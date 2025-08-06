import logging
from collections import Counter
from itertools import groupby
from pathlib import Path
from typing import Callable, Iterator, Mapping, cast

from grep_ast import filename_to_lang  # pyright: ignore[reportUnknownVariableType]
from grep_ast import TreeContext
from networkx import pagerank  # pyright: ignore[reportUnknownVariableType]
from networkx import MultiDiGraph
from pygments.lexer import Lexer
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from tree_sitter_languages import get_language, get_parser

from redia.repository_map.models import Tag


def repository_map_as_prompt(
    tags: list[Tag],
    root_directory: Path,
    token_counts: int,
    number_of_tokens: Callable[[str], int],
):
    lower_bound, upper_bound = 0, len(tags)

    mutable_output = ""

    while lower_bound <= upper_bound:
        middle = (lower_bound + upper_bound) // 2
        rendered = _rendered_from_tags(tags[:middle], root_directory)

        if number_of_tokens(rendered) <= token_counts:
            mutable_output = rendered
            lower_bound = middle + 1
        else:
            upper_bound = middle - 1

    return mutable_output


def _rendered_from_tags(
    tags: list[Tag],
    root_directory: Path,
):
    tags = sorted(tags, key=lambda x: x.absolute_path)

    mutable_output: str = ""

    for path, tags_in_path in groupby(tags, key=lambda x: x.absolute_path):
        tags_in_path = list(tags_in_path)

        mutable_context = TreeContext(
            filename=path,
            code=path.read_text(),
            color=False,
            line_number=False,
            child_context=False,
            last_line=False,
            margin=0,
            mark_lois=False,
            loi_pad=0,
            show_top_of_file_parent_scope=False,
        )

        for tag in tags_in_path:
            mutable_context.add_lines_of_interest(  # pyright: ignore[reportUnknownMemberType]
                [tag.start_line_index]
            )
            mutable_context.add_context()

        match len(tags_in_path):
            case 0:
                mutable_output = (
                    f"{mutable_output}\n{path.relative_to(root_directory)}\n"
                )
            case _:
                mutable_output = f"{mutable_output}\n{path.relative_to(root_directory)}:\n{mutable_context.format()}"

    return mutable_output


def sorted_tags_by_rank(absolute_paths: list[Path], others: list[Path]):
    definitions, references = _definitions_and_references_from_files(
        absolute_paths + others
    )

    definition_by_name = {tag.name: tag for tag in definitions}
    definition_by_name_and_path = {
        (tag.name, tag.absolute_path): tag for tag in definitions
    }
    references_by_name = (
        {
            tag.name: [
                reference for reference in references if reference.name == tag.name
            ]
            for tag in references
        }
        if references
        else {tag.name: [tag] for tag in definitions}
    )

    page_graph = MultiDiGraph()

    intersecting_names = set(definition_by_name.keys()) & set(references_by_name.keys())

    for name in intersecting_names:
        defined_on = definition_by_name[name].absolute_path

        for referenced_on, count in Counter(
            reference.absolute_path for reference in references_by_name[name]
        ).items():
            page_graph.add_edge(  # pyright: ignore[reportUnknownMemberType]
                referenced_on, defined_on, weight=count, identifier=name
            )

    ranked: Mapping[Path, float] = pagerank(
        page_graph,
        weight="weight",
        personalization={path: 1.0 for path in absolute_paths},
        dangling={path: 1.0 for path in absolute_paths},
    )

    ranked_definitions: list[tuple[str, Path, float]] = [
        (
            data["identifier"],
            destination,
            (
                ranked[source]
                * cast(float, data["weight"])
                / _total_outgoing_weight(node, page_graph)
            ),
        )
        for node in cast(Iterator[Path], page_graph.nodes)
        for source, destination, data in page_graph.out_edges(  # type: ignore
            node, data=True
        )
    ]

    return [
        definition_by_name_and_path[(identifier, destination)]
        for identifier, destination, _ in sorted(
            ranked_definitions, key=lambda x: x[2], reverse=True
        )
    ]


def _definitions_and_references_from_files(absolute_paths: list[Path]):
    definitions_and_references_by_file: list[tuple[list[Tag], list[Tag]]] = []

    for path in absolute_paths:
        try:
            definitions_and_references = _definitions_and_references_from_file(path)
        except AssertionError as e:
            logging.error(e)
            continue

        definitions_and_references_by_file.append(definitions_and_references)

    definitions = [
        tag
        for definitions, _ in definitions_and_references_by_file
        for tag in definitions
    ]

    references = [
        tag
        for _, references in definitions_and_references_by_file
        for tag in references
    ]

    return definitions, references


def _definitions_and_references_from_file(absolute_path: Path):
    assert (
        absolute_path.exists() and absolute_path.is_file()
    ), f"Invalid path of file: {absolute_path}"

    language_identifier = filename_to_lang(absolute_path.name)
    assert (
        language_identifier is not None
    ), f"Unsupported language: {absolute_path.suffix}"

    parser = get_parser(language_identifier)
    tree = parser.parse(absolute_path.read_bytes())

    scm_path = (
        Path(__file__).parent
        / "queries"
        / f"tree-sitter-{language_identifier}-tags.scm"
    )
    assert (
        scm_path.exists() and scm_path.is_file()
    ), f"Invalid path of query: {scm_path}"
    language = get_language(language_identifier)
    captured = language.query(scm_path.read_text()).captures(tree.root_node)

    definitions = [
        Tag(
            absolute_path=absolute_path,
            kind="def",
            name=node.text.decode(),
            start_line_index=node.start_point[0],
        )
        for node, tag in captured
        if tag.startswith("name.definition.")
    ]

    references = [
        Tag(
            absolute_path=absolute_path,
            kind="ref",
            name=node.text.decode(),
            start_line_index=node.start_point[0],
        )
        for node, tag in captured
        if tag.startswith("name.reference.")
    ]

    only_definitions_exist = len(definitions) != 0 and len(references) == 0

    if not only_definitions_exist:
        return definitions, references
    else:
        lexer = cast(
            Lexer,
            guess_lexer_for_filename(absolute_path, absolute_path.read_text()),
        )

        return definitions, [
            Tag(
                absolute_path=absolute_path,
                kind="ref",
                name=name,
                start_line_index=None,
            )
            for token_type, name in lexer.get_tokens(absolute_path.read_text())
            if token_type in Token.Name
        ]


def _total_outgoing_weight(node: Path, graph: MultiDiGraph) -> float:
    return sum(data["weight"] for _, _, data in graph.out_edges(node, data=True))  # type: ignore


if __name__ == "__main__":
    tags = sorted_tags_by_rank(
        [Path(__file__)],
        [Path(__file__).parent / "models.py"],
    )

    print(repository_map_as_prompt(tags, Path(__file__).parent.parent.parent, 512, len))
