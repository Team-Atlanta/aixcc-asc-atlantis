import difflib
import re
from pathlib import Path


def git_diff_from_unified_diff_response(response: str, source_directory: Path) -> str:
    edits = _edits_from_response(response)

    return _git_diff_from_edits(edits, source_directory).strip()


def _git_diff_from_edits(
    edits: list[tuple[str, str, list[str]]], source_directory: Path
) -> str:
    return "\n".join(_unified_diff_from_edit(edit, source_directory) for edit in edits)


def _unified_diff_from_edit(
    edit: tuple[str, str, list[str]], source_directory: Path
) -> str:
    before_path, after_path, hunk_lines = edit

    before = (source_directory / before_path).read_text()
    after = _apply_hunk_lines(hunk_lines, before)

    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{before_path}",
        tofile=f"b/{after_path}",
        n=max(*[len(x) for x in _before_and_after_of_hunk_lines(hunk_lines)]),
    )

    header = f"diff --git a/{before_path} b/{after_path}\n"

    return header + "".join(diff)


def _apply_hunk_lines(hunk_lines: list[str], contents: str) -> str:
    before_lines, after_lines = _before_and_after_of_hunk_lines(hunk_lines)

    before, after = "".join(before_lines), "".join(after_lines)

    assert (
        before in contents
    ), f"Mismatch in original code and suggested code. There is no:\n{before}"

    return contents.replace(before, after)


def _before_and_after_of_hunk_lines(
    hunk_lines: list[str],
) -> tuple[list[str], list[str]]:
    mutable_before: list[str] = []
    mutable_after: list[str] = []

    for line in hunk_lines:
        if line.startswith("-"):
            mutable_before.append(line[1:])
        elif line.startswith("+"):
            mutable_after.append(line[1:])
        else:
            mutable_before.append(line[1:])
            mutable_after.append(line[1:])

    return mutable_before, mutable_after


def _edits_from_response(response: str) -> list[tuple[str, str, list[str]]]:
    return [
        edit
        for block in _fenced_blocks_from_response(response)
        for edit in _edits_from_fenced_block(block)
    ]


def _fenced_blocks_from_response(response: str) -> list[str]:
    assert "```diff" in response, "No diff fences found"

    return re.findall(r"```diff\n(.*?)\n```", response, re.DOTALL)


def _edits_from_fenced_block(block: str) -> list[tuple[str, str, list[str]]]:
    return [
        _edits_from_unified_diff(diff)
        for diff in _unified_diffs_from_fenced_block(block)
    ]


def _edits_from_unified_diff(diff: str) -> tuple[str, str, list[str]]:
    filenames = _filename_from_unified_diff(diff)

    assert filenames is not None, f"Expected a filename in diff, got {filenames}"

    edits = [
        edit for hunk in _hunks_of_unified_diff(diff) for edit in _lines_of_hunk(hunk)
    ]

    return *filenames, edits


def _unified_diffs_from_fenced_block(block: str) -> list[str]:
    return [f"--- {partial}" for partial in f"\n{block}".split("\n--- ")[1:]]


def _hunks_of_unified_diff(diff: str) -> list[str]:
    return [f"@@{partial}" for partial in diff.split("\n@@")[1:]]


def _filename_from_unified_diff(hunk: str) -> tuple[str, str] | None:
    lines = hunk.splitlines()

    assert len(lines) >= 2, f"Expected at least 2 lines in hunk, got {len(lines)}"

    if lines[0].startswith("--- ") and lines[1].startswith("+++ "):
        return lines[0][4:].strip(), lines[1][4:].strip()
    else:
        return None


def _lines_of_hunk(hunk: str) -> list[str]:
    lines = (hunk.strip() + "\n").splitlines(keepends=True)[1:]

    return lines
