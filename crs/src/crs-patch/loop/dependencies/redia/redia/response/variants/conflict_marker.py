import difflib
import re
from itertools import groupby
from pathlib import Path
from typing import Iterator, TypeAlias

from rusty_results.prelude import Empty, Option, Some

_Before: TypeAlias = str
_After: TypeAlias = str


def git_diff_from_conflict_marker_response(
    response: str, source_directory: Path
) -> str:
    edits = list(_edits_from_response(response))

    assert len(edits) > 0, f"No edits found in response:\n {response}"

    return _git_diff_from_edits(edits, source_directory)


def _git_diff_from_edits(
    edits: list[tuple[_Before, _After, Path]], source_directory: Path
):
    sorted_edits = sorted(edits, key=lambda edit: edit[2])
    edits_by_file = groupby(sorted_edits, key=lambda edit: edit[2])

    mutable_result = ""

    for relative_path, file_edits in edits_by_file:
        file_edits = [(before, after) for before, after, _ in file_edits]

        before = (source_directory / relative_path).read_text()
        after = _replace_most_similar_chunk_by_edits(before, file_edits)

        mutable_result += f"{_git_diff(before, after, relative_path)}\n"

    return _make_string_ends_with_newline(mutable_result)


def _git_diff(before: str, after: str, relative_path: Path):
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{relative_path}",
        tofile=f"b/{relative_path}",
    )

    header = f"diff --git a/{relative_path} b/{relative_path}\n"

    return header + "".join(diff)


def _edits_from_response(
    response: str,
) -> Iterator[tuple[_Before, _After, Path]]:
    for filename, before, after in re.findall(
        r"(?:file: (.+?)\n```\w+\n*<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE)",
        response,
        flags=re.MULTILINE | re.DOTALL,
    ):
        yield before, after, Path(filename)


def _replace_most_similar_chunk_by_edits(
    target_content: str, edits: list[tuple[_Before, _After]]
):
    mutable_result = target_content

    for edit in edits:
        match _replace_most_similar_chunk_by_edit(mutable_result, edit):
            case Some(result):
                mutable_result = result
            case Empty():
                assert False, f"Failed to replace:\n{edit[0]}\n{edit[1]}"

    return mutable_result


def _replace_most_similar_chunk_by_edit(
    content: str, edit: tuple[_Before, _After]
) -> Option[str]:
    return (
        _replace_perfectly_matching_chunk(content, edit)
        # .or_else(lambda: _replace_part_with_missing_leading_whitespace(content, edit))
        .or_else(lambda: _replace_parts_with_ellipsis(content, edit))
    )


def _replace_perfectly_matching_chunk(
    content: str, edit: tuple[_Before, _After]
) -> Option[str]:
    before, after = edit
    if before in content:
        return Some(content.replace(before, after, 1))
    else:
        return Empty()


def _replace_part_with_missing_leading_whitespace(
    content: str, edit: tuple[_Before, _After]
) -> Option[str]:
    before, after = edit
    content_lines = _lines(content)
    before_lines = _lines(before)
    after_lines = _lines(after)

    min_leading_whitespace = _min_leading_whitespace_length(before_lines + after_lines)

    outdented_before_lines = _outdented_lines(before_lines, min_leading_whitespace)
    outdented_after_lines = _outdented_lines(after_lines, min_leading_whitespace)

    matched_target = _matched_target_without_leading_whitespace(
        content, "".join(outdented_before_lines)
    )

    match matched_target:
        case Some((before, index)):
            before_lines = _lines(before)

            leading_length = _min_leading_whitespace_length(
                content_lines[index : index + len(before_lines)]
            )

            indented_after_lines = _indent_lines(outdented_after_lines, leading_length)

            return Some(
                "".join(
                    content_lines[:index]
                    + indented_after_lines
                    + content_lines[index + len(before_lines) :]
                )
            )
        case Empty():
            return Empty()


def _min_leading_whitespace_length(lines: list[str]) -> int:
    return min(
        (len(line) - len(line.lstrip()) for line in lines if line.strip()),
        default=0,
    )


def _matched_target_without_leading_whitespace(
    content: str, before: _Before
) -> Option[tuple[str, int]]:
    content_lines = _lines(content)
    before_lines = _lines(before)

    assert len(content_lines) >= len(before_lines)

    chunks = [
        content_lines[i : i + len(before_lines)]
        for i in range(len(content_lines) - len(before_lines) + 1)
    ]

    for index, chunk in enumerate(chunks):
        if _match_without_leading_whitespace(chunk, before_lines):
            return Some(("".join(chunk), index))

    return Empty()


def _match_without_leading_whitespace(a: list[str], b: list[str]) -> bool:
    assert len(a) == len(b)

    if not all(a.lstrip() == b.lstrip() for a, b in zip(a, b)):
        return False
    else:
        indents = {a[: len(a) - len(b)] for a, b in zip(a, b) if a.strip()}

        return len(indents) == 1


def _indent_lines(lines: list[str], indent: int) -> list[str]:
    return [line[:indent] + line if line.strip() else line for line in lines]


def _outdented_lines(lines: list[str], outdent_length: int) -> list[str]:
    return [line[outdent_length:] if line.strip() else line for line in lines]


def _replace_parts_with_ellipsis(
    content: str, edit: tuple[_Before, _After]
) -> Option[str]:
    before, after = edit
    before_pieces = re.split(
        r"(^\s*\.\.\.\n)",
        before,
        flags=re.MULTILINE | re.DOTALL,
    )

    after_pieces = re.split(
        r"(^\s*\.\.\.\n)",
        after,
        flags=re.MULTILINE | re.DOTALL,
    )

    assert len(before_pieces) == len(
        after_pieces
    ), f"Unequal number of pieces: {before_pieces} vs {after_pieces}"

    if len(before_pieces) == 1:
        return Empty()

    assert all(
        before_piece == after_piece
        for before_piece, after_piece in zip(before_pieces[1::2], after_pieces[1::2])
    ), f"Unequal ellipsis pieces: {before_pieces} vs {after_pieces}"

    before_pieces = before_pieces[::2]
    after_pieces = after_pieces[::2]

    mutable_result = content

    for before, after in zip(before_pieces, after_pieces):
        if not before and not after:
            continue
        elif not before and after:
            mutable_result = _make_string_ends_with_newline(mutable_result) + after
        elif before not in mutable_result:
            return Empty()
        elif mutable_result.count(before) > 1:
            return Empty()
        else:
            mutable_result = mutable_result.replace(before, after, 1)

    return Some(mutable_result)


def _lines(content: str) -> list[str]:
    return _make_string_ends_with_newline(content).splitlines(keepends=True)


def _make_string_ends_with_newline(content: str) -> str:
    if not content.endswith("\n"):
        return content + "\n"
    else:
        return content
