from pathlib import Path
from typing import Iterator, TypeAlias

import pygit2

from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection

_Edit: TypeAlias = tuple[tuple[str, Path], tuple[str, Path]]


def edits_from_detection(detection: Detection, challenge_source: ChallengeSource):
    repository = pygit2.Repository(str(challenge_source.source_directory))

    diff = _diff_from_commit_id(detection.bug_introduce_commit, repository)

    return _edits_from_diff(diff)


def _edits_from_diff(diff: pygit2.Diff) -> Iterator[_Edit]:
    for patch in diff:
        yield from _edits_from_patch(patch)


def _edits_from_patch(patch: pygit2.Patch) -> Iterator[_Edit]:
    old_file_path = Path(patch.delta.old_file.path)
    new_file_path = Path(patch.delta.new_file.path)

    for hunk in patch.hunks:
        before, after = _before_and_after_from_hunk(hunk)
        yield ((before, old_file_path), (after, new_file_path))


def _before_and_after_from_hunk(hunk: pygit2.DiffHunk):
    mutable_before: list[str] = []
    mutable_after: list[str] = []

    for line in hunk.lines:
        match line.origin:
            case " ":
                mutable_before.append(line.content)
                mutable_after.append(line.content)
            case "+":
                mutable_after.append(line.content)
            case "-":
                mutable_before.append(line.content)
            case _:
                raise ValueError(f"Unexpected line origin: {line.origin}")

    return "".join(mutable_before), "".join(mutable_after)


def _diff_from_commit_id(commit_id: str, repository: pygit2.Repository):
    commit = repository.revparse_single(commit_id).peel(1)
    parent = commit.parent_ids[0]

    diff = repository.diff(parent, commit.tree)

    return diff
