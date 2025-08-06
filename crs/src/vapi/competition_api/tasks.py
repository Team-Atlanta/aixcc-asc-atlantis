import asyncio
from base64 import b64encode
import contextlib
import datetime
import os
from pathlib import Path
import subprocess
import traceback
from typing import Callable
from uuid import UUID

import git
import whatthepatch
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from structlog.stdlib import get_logger
from vyper import v

from competition_api.audit import Auditor
from competition_api.audit.types import (
    Disposition,
    EventType,
    GPSubmissionFailReason,
    VDSubmissionFailReason,
)
from competition_api.bisector import Bisector
from competition_api.cp_workspace import BadReturnCode, AbstractCPWorkspace
from competition_api.capi_client import CapiClient, CapiSubmissionResult
from competition_api.cp_registry import CPRegistry
from competition_api.db import PrecompilationCommitHint, GeneratedPatch, VulnerabilityDiscovery, db_session
from competition_api.file_folder_copy import copy_file
from competition_api.flatfile import Flatfile
from competition_api.lib import peek
from competition_api.models.gp import GPSubmission
from competition_api.models.types import FeedbackStatus, CheckingStatus, VDDBSubmissionFailReason
from competition_api.models.vds import VDSubmission, POV
from competition_api.sadlock import test_and_set
from competition_api.wrapped_cp_workspace import BuildStatus, WrappedCPWorkspace

LOGGER = get_logger(__name__)


# The number of initial commits to attempt to test at when picking
# sources to bisect over, before giving up and including them in that
# set by default
NUM_INITIAL_COMMIT_TESTS = 4
# If whether a VD is a duplicate or not depends on the outcome of one or
# more previously-submitted VDs which are still pending, request a
# status update from CAPI this frequently
CAPI_PENDING_RETRY_INTERVAL = 5  # seconds
# When submitting a VD or GP to CAPI, if there's some error that seems
# to indicate that it's temporarily unavailable (e.g., connection
# timeout, connection refused, internal server error), wait this long
# before retrying
CAPI_TRY_AGAIN_INTERVAL = 20  # seconds
# If the precompilation thread notices that one or more VD or GP tests
# have started, it stops its work and re-checks every X seconds until it
# sees that all of them have finished, before resuming
PRECOMPILATION_ACTIVITY_CHECK_INTERVAL = 5  # seconds


class WorkspaceBuildError(Exception):
    pass


async def task_ignore_excs(task):
    """
    Wrapper for an async task that logs any exceptions instead of
    propagating them. Useful for TaskGroups where you want failures to
    be ignored instead of cancelling all the other tasks.
    """
    try:
        await task
    except Exception:
        await LOGGER.awarning(f'Ignoring exception during status update:\n{traceback.format_exc()}')


class NullAsyncContextManager(contextlib.AbstractAsyncContextManager):
    async def __aenter__(self): pass
    async def __aexit__(self, _exc_type, _exc, _tb): pass


def UUID_or_none(s: str | None) -> UUID | None:
    if s is None:
        return None
    else:
        return UUID(s)


def nth_general_bisection_fraction(n: int) -> tuple[int, int]:
    """
    Return the numerator and denominator for the n'th element
    (0-indexed) of the following sequence:

        1/2, 1/4, 3/4, 1/8, 3/8, 5/8, 7/8, 1/16, 3/16, ...

    This is the order of fractions that would be hypothetically used in
    bisection, if you didn't actually have a specific target.
    """
    # Skip nonsensical first element ("0/1")
    n += 1
    # Numerator: OEIS A006257 (formula: left-rotate n by 1)
    numerator = ((n << 1) & ((1 << n.bit_length()) - 1)) | 1
    # Denominator: OEIS A062383 (formula: see below)
    denominator = 1 << n.bit_length()
    return numerator, denominator

assert [nth_general_bisection_fraction(i) for i in range(9)] \
    == [(1,2), (1,4), (3,4), (1,8), (3,8), (5,8), (7,8), (1,16), (3,16)]


async def build_at(
    workspace: AbstractCPWorkspace,
    commit: str,
) -> bool:
    source = workspace.cp.source_from_ref(commit)
    if source is None:
        # this should never happen
        # we pick our own commits during bisection
        raise RuntimeError(f"source was none but we picked the commit ({commit}) ourselves")
    workspace.set_src_repo_by_name(source)

    try:
        await workspace.checkout(commit)
    except git.exc.GitCommandError:
        return False

    return await workspace.build(None)


async def check_sanitizers_at(
    workspace: AbstractCPWorkspace,
    vds: VulnerabilityDiscovery,
    commit: str,
    auditor: Auditor,
) -> set[str] | None:
    source = workspace.cp.source_from_ref(commit)
    if source is None:
        # this should never happen
        # we pick our own commits during bisection
        raise RuntimeError(f"source was none but we picked the commit ({commit}) ourselves")

    if not await build_at(workspace, commit):
        return None

    try:
        sanitizers = await workspace.check_sanitizers(
            vds.pov_data_sha256, vds.pov_harness
        )
    except BadReturnCode:
        await LOGGER.awarning("Bad return code when checking sanitizers at %s", commit)
        return None

    await auditor.emit(
        EventType.VD_SANITIZER_RESULT,
        source=source,
        commit_sha=commit,
        disposition=Disposition.GOOD,
        sanitizers_triggered=[
            workspace.sanitizer(san) for san in sanitizers
        ],
    )

    return sanitizers


class WorkspaceBisector(Bisector):
    """
    Subclass of Bisector that implements the methods for interacting
    with the workspace
    """
    def __init__(self,
        workspace: AbstractCPWorkspace,
        vds: VulnerabilityDiscovery,
        auditor: Auditor,
        sources_to_bisect: set[str],
    ):
        self.workspace = workspace
        self.vds = vds
        self.auditor = auditor
        self.sources_to_bisect = sources_to_bisect

    async def get_sources(self) -> set[str]:
        return self.sources_to_bisect

    async def get_all_commits_for_source(self, source: str) -> list[str]:
        return self.workspace.commit_list(source)

    async def test_at(self, commit: str) -> set[str] | None:
        return await check_sanitizers_at(self.workspace, self.vds, commit, self.auditor)


async def workspace_build_or_raise(workspace: AbstractCPWorkspace, *args, **kwargs) -> bool:
    """
    Wrapper for workspace.build() which raises WorkspaceBuildError
    instead of returning False upon failure
    """
    if not await workspace.build(*args, **kwargs):
        raise WorkspaceBuildError
    return True


class TaskRunner:
    def __init__(self, cp_name: str, auditor: Auditor):
        self.auditor = auditor
        self.cp_name = cp_name

    async def precompile(self) -> None:
        """
        A "precompilation" thread for building some commits while the
        server is otherwise idle.
        """
        await LOGGER.ainfo("Precompilation thread launching")

        # We want at most one precompilation thread to run at any point,
        # so if there's already an existing one, exit immediately
        if await test_and_set(f'precompilation_thread_running_for_{self.cp_name}'):
            await LOGGER.ainfo("Another precompilation thread already exists -- exiting")
            return

        if v.get_bool("wait_docker_ready"):
            await WrappedCPWorkspace.await_docker_ready(self.cp_name)

        async with WrappedCPWorkspace(self.cp_name, self.auditor) as workspace:
            while True:
                try:
                    if commit := await self._precompile_pick_next_commit(workspace):
                        await LOGGER.ainfo("Precompiling %s", commit)
                        if commit == 'HEAD':
                            # pick the head ref from any source
                            source = next(iter(workspace.cp.sources.keys()))
                            commit = workspace.cp.head_ref_from_source(source)
                        await build_at(workspace, commit)
                    else:
                        await LOGGER.ainfo("Precompilation: done")
                        break
                except Exception:
                    await LOGGER.adebug(f"Exception during precompilation:\n{traceback.format_exc()}")
                    # Try again, but not immediately (don't want to spam build attempts)
                    await asyncio.sleep(5)

                # If any VD or GP tests are ongoing, we should sleep and
                # let them take priority. We can resume if/when they all
                # finish.
                printed_msg = False
                while await self._precompile_check_if_any_vds_or_gps_active():
                    if not printed_msg:
                        await LOGGER.adebug("Precompilation: pausing to wait for VD/GP tests to finish")
                        printed_msg = True
                    await asyncio.sleep(PRECOMPILATION_ACTIVITY_CHECK_INTERVAL)
                if printed_msg:
                    await LOGGER.adebug("Precompilation: resuming")

        # Note: we *don't* need to unset the "precompilation thread
        # running" flag here, because if we reach here,
        # _precompile_pick_next_commit() must've returned None, meaning
        # there are literally no commits left to compile -- and at that
        # point, we still don't want any additional precompile threads
        # to launch for this CP, even though this one's technically not
        # running anymore

    async def _precompile_pick_next_commit(self, workspace: AbstractCPWorkspace) -> str | None:
        """
        Pick the next commit SHA1 (or "HEAD") to precompile.
        Returns None if (and only if) there are literally no uncompiled
        commits left.
        """

        # In general, it's difficult to predict the exact order in which
        # the bisection algorithm will decide to test hints and other
        # commits, since it depends on many factors (e.g., commits that
        # are more likely to be a BIC for the specific VD under test
        # will be slightly favored; hinted commits closer to the center
        # of the range currently under test will be slightly favored;
        # etc.). What we're doing here is just a best-effort
        # approximation, which'll hopefully have enough overlap to be
        # useful. It'll certainly at least be better than just building
        # all hints in chronological order, or similar.

        # The overall order we aim for is:
        # - HEAD commit
        # - Hint-related things
        #   - Initial commits from hinted sources
        #   - Hinted commits
        #     - Midpoint hint for sources A, B, C, ...
        #     - 1/4 hint for sources A, B, C, ...
        #     - 3/4 hint for sources A, B, C, ...
        #     - 1/8 hint for sources A, B, C, ...
        #     - 3/8 hint for sources A, B, C, ...
        #     - 5/8 hint for sources A, B, C, ...
        #     - 7/8 hint for sources A, B, C, ...
        #     - 1/16 hint for sources A, B, C, ...
        #     - ...
        #   - Commits preceding hinted commits
        #     - Commit before the midpoint hint for sources A, B, C, ...
        #     - Commit before the 1/4 hint for sources A, B, C, ...
        #     - Commit before the 3/4 hint for sources A, B, C, ...
        #     - Commit before the 1/8 hint for sources A, B, C, ...
        #     - Commit before the 3/8 hint for sources A, B, C, ...
        #     - Commit before the 5/8 hint for sources A, B, C, ...
        #     - Commit before the 7/8 hint for sources A, B, C, ...
        #     - Commit before the 1/16 hint for sources A, B, C, ...
        #     - ...
        # - All commits
        #   - Initial commits from non-hinted sources
        #   - Midpoint commit for sources A, B, C, ...
        #   - 1/4 commit for sources A, B, C, ...
        #   - 3/4 commit for sources A, B, C, ...
        #   - 1/8 commit for sources A, B, C, ...
        #   - 3/8 commit for sources A, B, C, ...
        #   - 5/8 commit for sources A, B, C, ...
        #   - 7/8 commit for sources A, B, C, ...
        #   - 1/16 commit for sources A, B, C, ...

        # Structurally, the goal of this function is to pick the first
        # commit in this sequence that hasn't been built yet.

        commit_lists = {source: workspace.commit_list(source) for source in workspace.cp.sources.keys()}

        _check_cache = {}
        def check_with_cache(ref: str) -> BuildStatus:
            if ref not in _check_cache:
                _check_cache[ref] = workspace.commit_build_status(ref)
            return _check_cache[ref]

        hints = await self._precompile_get_current_hints()

        # HEAD is a bit tricky, because the act of entering a workspace
        # context will always automatically switch to it, making it
        # appear as CURRENTLY_BUILDING even if it hasn't actually
        # started building yet. Therefore, we choose HEAD unless we can
        # see that it's clearly already built. Even if it *is* actually
        # already building, this is a mistake we'll make at most once
        # thanks to the build lock in WrappedCPWorkspace -- and thanks
        # to the artifact cache, it won't really harm anything.
        if check_with_cache('HEAD') in {BuildStatus.NOT_BUILT, BuildStatus.CURRENTLY_BUILDING}:
            return 'HEAD'

        if hints:
            # Initial commits (hinted sources only)
            if commit := self._precompile_try_pick_initial_commit(
                workspace, commit_lists, hints, check_with_cache, only_hinted_sources=True
            ):
                return commit

            # Hints (bisection order)
            if commit := self._precompile_try_pick_bisection_commit(
                workspace, commit_lists, hints, check_with_cache, 'hints'
            ):
                return commit

            # Commits immediately preceding hints (bisection order)
            if commit := self._precompile_try_pick_bisection_commit(
                workspace, commit_lists, hints, check_with_cache, 'preceding_hints'
            ):
                return commit

        # Initial commits (all sources)
        if commit := self._precompile_try_pick_initial_commit(
            workspace, commit_lists, hints, check_with_cache, only_hinted_sources=False
        ):
            return commit

        # All commits (bisection order)
        if commit := self._precompile_try_pick_bisection_commit(
            workspace, commit_lists, hints, check_with_cache, 'all'
        ):
            return commit

        return None

    def _precompile_try_pick_initial_commit(
        self,
        workspace: AbstractCPWorkspace,
        commit_lists: dict[str, list[str]],
        hints: set[str],
        check_fn: Callable[[str], BuildStatus],
        *,
        only_hinted_sources: bool,
    ) -> str | None:
        """
        Try to pick a next commit for precompilation, targeting commits
        expected to be used by self._test_vds_at_initial_commits().
        If only_hinted_sources == True, only sources that have hints
        associated with them will be used.
        """
        for source in workspace.cp.sources.keys():
            if only_hinted_sources and not any(h in commit_lists[source] for h in hints):
                continue

            commit_list = commit_lists[source]
            for i, commit in enumerate(commit_list):
                if i >= NUM_INITIAL_COMMIT_TESTS:
                    break
                status = check_fn(commit)
                if status == BuildStatus.NOT_BUILT:
                    return commit
                elif status == BuildStatus.BUILT_SUCCESS:
                    break
                elif status == BuildStatus.BUILT_FAILURE:
                    continue
                else:  # BuildStatus.CURRENTLY_BUILDING
                    # Whether we should check the next commit or move on
                    # to the next source depends on whether this build
                    # is a success or failure. But we can just
                    # optimistically assume that it'll probably be a
                    # success (and if not, we'll quickly notice in a
                    # future precompilation round)
                    break

        return None

    def _precompile_try_pick_bisection_commit(
        self,
        workspace: AbstractCPWorkspace,
        commit_lists: dict[str, list[str]],
        hints: set[str],
        check_fn: Callable[[str], BuildStatus],
        phase: str,
    ) -> str | None:
        """
        Try to pick a next commit for precompilation, targeting commits
        expected to be used during the bisection process.
        "phase" can be one of the following:
        - "hints": pick from hinted commits, roughly in the order that
          one would bisect over them
        - "preceding_hints": like "hints", but picks from commits
          immediately preceding hints instead of the hints themselves
        - "all": ignore hints and return all commits, roughly in the
          order that one would bisect over them
        """

        def nth_commit_in_sequence(source: str, n: int) -> str:
            """
            Get the n'th commit from the sequence indicated by `phase`.
            Always returns *some* commit -- you'll need a separate
            stopping condition if you want to iterate over the sequence.
            """
            commit_list = commit_lists[source]
            hinted_commit_list = [c for c in commit_list if c in hints]

            frac_num, frac_denom = nth_general_bisection_fraction(n)
            frac = frac_num / frac_denom

            if phase == 'all':
                return commit_list[int(len(commit_list) * frac)]
            elif phase == 'hints':
                if hinted_commit_list:
                    return hinted_commit_list[int(len(hinted_commit_list) * frac)]
                else:
                    return commit_list[-1]
            elif phase == 'preceding_hints':
                if hinted_commit_list:
                    hint = hinted_commit_list[int(len(hinted_commit_list) * frac)]
                    idx = commit_list.index(hint) - 1
                    if idx < 0:
                        idx = 0
                    return commit_list[idx]
                else:
                    return commit_list[-1]

        def all_commits_in_sequence(source: str) -> set[str]:
            """
            Return the full set of commits that will eventually be
            returned by nth_commit()
            """
            commit_list = commit_lists[source]
            hinted_commit_list = [c for c in commit_list if c in hints]

            if phase == 'all':
                return set(commit_list)
            elif phase == 'hints':
                return set(hinted_commit_list)
            elif phase == 'preceding_hints':
                ret = set()
                for hint in hinted_commit_list:
                    idx = commit_list.index(hint) - 1
                    if idx < 0:
                        idx = 0
                    ret.add(commit_list[idx])
                return ret

        i = -1
        while True:
            i += 1
            anything_remaining = False
            for source in workspace.cp.sources.keys():
                commit = nth_commit_in_sequence(source, i)
                if check_fn(commit) == BuildStatus.NOT_BUILT:
                    return commit

                for c in all_commits_in_sequence(source):
                    if check_fn(c) == BuildStatus.NOT_BUILT:
                        anything_remaining = True

            if not anything_remaining:
                break

        return None

    async def _precompile_get_current_hints(self) -> set[str]:
        """
        Return the current (!) set of commit hints for precompilation.
        (May change over time, if the /precompile/ endpoint is invoked
        multiple times to add additional hints.)
        """
        async with db_session() as db:
            hint_rows = (
                await db.execute(
                    select(PrecompilationCommitHint)
                    .where(PrecompilationCommitHint.cp_name == self.cp_name)
                )
            ).fetchall()

            return {row.commit_sha1.lower() for (row,) in hint_rows}

    async def _precompile_check_if_any_vds_or_gps_active(self) -> bool:
        """
        For the precompilation thread: check if there are any VDS or GP
        checks currently running
        """
        async with db_session() as db:
            active_vds_count, = (
                await db.execute(
                    select(
                        func.count(VulnerabilityDiscovery.id)  # pylint: disable=not-callable
                    ).where(
                        VulnerabilityDiscovery.checking_status == CheckingStatus.BEGINNING
                    )
                )
            ).fetchone()
            if active_vds_count > 0:
                return True

            active_gp_count, = (
                await db.execute(
                    select(
                        func.count(GeneratedPatch.id)  # pylint: disable=not-callable
                    ).where(
                        GeneratedPatch.checking_status == CheckingStatus.BEGINNING
                    )
                )
            ).fetchone()
            return active_gp_count > 0

    async def test_vds(self, vds: VulnerabilityDiscovery):
        try:
            if vd_uuid := await self._test_vds(vds):
                await self.auditor.emit(EventType.VD_SUBMISSION_SUCCESS)
                async with db_session() as db:
                    await db.execute(
                        update(VulnerabilityDiscovery)
                        .where(VulnerabilityDiscovery.id == vds.id)
                        .values(
                            remote_uuid=UUID(vd_uuid),
                            checking_status=CheckingStatus.DONE,
                        )
                    )
            else:
                async with db_session() as db:
                    await db.execute(
                        update(VulnerabilityDiscovery)
                        .where(VulnerabilityDiscovery.id == vds.id)
                        .values(
                            status=FeedbackStatus.NOT_ACCEPTED,
                            checking_status=CheckingStatus.DONE,
                        )
                    )
        except Exception:
            await LOGGER.adebug(f"Exception during VDS testing:\n{traceback.format_exc()}")
            await self.auditor.emit(
                EventType.VD_SUBMISSION_FAIL,
                reason=VDSubmissionFailReason.GENERAL_EXCEPTION,
            )
            async with db_session() as db:
                await db.execute(
                    update(VulnerabilityDiscovery)
                    .where(VulnerabilityDiscovery.id == vds.id)
                    .values(
                        status=FeedbackStatus.NOT_ACCEPTED,
                        checking_status=CheckingStatus.DONE,
                        fail_reason=VDDBSubmissionFailReason.GENERAL_EXCEPTION,
                    )
                )

    async def _set_vds_fail_reason(self, vds: VulnerabilityDiscovery, reason: VDDBSubmissionFailReason) -> None:
        async with db_session() as db:
            await db.execute(
                update(VulnerabilityDiscovery)
                .where(VulnerabilityDiscovery.id == vds.id)
                .values(fail_reason=reason)
            )

    async def _test_vds(
        self,
        vds: VulnerabilityDiscovery,
    ) -> str | None:
        """
        The high-level logic for testing and submitting a VD.
        Returns the VD_UUID if submission is successful.
        """
        await LOGGER.ainfo("Testing VDS %s", vds)

        if v.get_bool("wait_docker_ready"):
            await WrappedCPWorkspace.await_docker_ready(self.cp_name)

        async with WrappedCPWorkspace(self.cp_name, self.auditor) as workspace:
            # Validate sanitizer fires at HEAD
            sanitizers_triggered_at_head = await self._test_vds_at_head(
                vds, workspace
            )
            if sanitizers_triggered_at_head is None:
                return None
            elif not sanitizers_triggered_at_head:
                await self.auditor.emit(
                    EventType.VD_SUBMISSION_FAIL,
                    reason=VDSubmissionFailReason.SANITIZER_DID_NOT_FIRE_AT_HEAD,
                )
                await self._set_vds_fail_reason(vds, VDDBSubmissionFailReason.SANITIZER_DID_NOT_FIRE_AT_HEAD)
                return None

            hinted_commits = set(c.lower() for c in vds.pou_commit_hints.split(','))
            hinted_commits.discard('')

            # Check which sources have hints pointing to them, and which
            # don't
            hinted_sources = set()
            non_hinted_sources = set()
            for source in workspace.cp.sources.keys():
                all_commits_for_source = workspace.commit_list(source)
                if hinted_commits & set(all_commits_for_source):
                    hinted_sources.add(source)
                else:
                    non_hinted_sources.add(source)

            # Prioritize for speed: check hinted sources first, and only
            # check the rest if all of those fail
            tested_any_sources = False
            other_tests_already_performed = {}
            for sources_subset in [hinted_sources, non_hinted_sources]:

                # We start by testing at the initial commit(s) (or the
                # earliest one(s) we're able to build), to make sure
                # that the vulnerability was introduced by *some* later
                # commit. This also gives us a list of which sources we
                # should bisect over (hopefully just one).
                sources_to_bisect, more_tests = await self._test_vds_at_initial_commits(
                    vds, workspace, sanitizers_triggered_at_head, sources_subset
                )
                other_tests_already_performed.update(more_tests)

                if sources_to_bisect:
                    tested_any_sources = True

                    # Then bisect
                    pou = await WorkspaceBisector(
                        workspace, vds, self.auditor, sources_to_bisect
                    ).bisect(
                        sanitizers_triggered_at_head, other_tests_already_performed, hinted_commits
                    )
                    if pou is not None:
                        break

            if not tested_any_sources:
                await self.auditor.emit(
                    EventType.VD_SUBMISSION_FAIL,
                    reason=VDSubmissionFailReason.ALL_SANITIZERS_ALSO_FIRED_AT_INITIAL,
                )
                await self._set_vds_fail_reason(vds, VDDBSubmissionFailReason.ALL_SANITIZERS_ALSO_FIRED_AT_INITIAL)
                return None

        if pou is None:
            await self.auditor.emit(
                EventType.VD_SUBMISSION_FAIL,
                reason=VDSubmissionFailReason.BISECTION_FAILED,
            )
            await self._set_vds_fail_reason(vds, VDDBSubmissionFailReason.BISECTION_FAILED)
            return None

        # Either way, we now have something to submit
        await LOGGER.adebug(
            "Achieved PoU: commit=%s, sanitizer=%s",
            pou.commit_sha1.lower(), pou.sanitizer,
        )
        async with db_session() as db:
            await db.execute(
                update(VulnerabilityDiscovery)
                .where(VulnerabilityDiscovery.id == vds.id)
                .values(
                    pou_commit_sha1=pou.commit_sha1.lower(),
                    pou_sanitizer=pou.sanitizer,
                )
            )

        new_vd_submission = VDSubmission(
            cp_name=vds.cp_name,
            pou=pou,
            pov=POV(
                harness=vds.pov_harness,
                data=b64encode(Flatfile(contents_hash=vds.pov_data_sha256).filename.read_bytes()),
            ),
        )

        if v.get_bool("scoring.reject_duplicate_vds"):
            # Check if we've already submitted a working VDS for this commit
            if await self._test_vds_check_for_duplicate(vds, new_vd_submission):
                await self.auditor.emit(
                    EventType.VD_SUBMISSION_FAIL,
                    reason=VDSubmissionFailReason.DUPLICATE_COMMIT,
                )
                await self._set_vds_fail_reason(vds, VDDBSubmissionFailReason.DUPLICATE_COMMIT)
                return None

        # If not, submit it
        return await self._test_vds_submit_to_capi(vds, new_vd_submission)

    async def _test_vds_at_head(
        self,
        vds: VulnerabilityDiscovery,
        workspace: AbstractCPWorkspace,
    ) -> set[str] | None:
        """
        Test the VDS at the HEAD commit.
        Returns the set of sanitizers that were triggered, or None if
        there was an error.
        """
        await LOGGER.adebug("Building at HEAD")

        try:
            await workspace_build_or_raise(workspace, None)
            sanitizers = await workspace.check_sanitizers(
                vds.pov_data_sha256, vds.pov_harness
            )
        except git.exc.GitCommandError:
            await self.auditor.emit(
                EventType.VD_SUBMISSION_FAIL,
                reason=VDSubmissionFailReason.COMMIT_CHECKOUT_FAILED,
            )
            await self._set_vds_fail_reason(vds, VDDBSubmissionFailReason.COMMIT_CHECKOUT_FAILED)
            return None
        except WorkspaceBuildError:
            # um, that's not good
            await LOGGER.acritical("EMERGENCY: the HEAD commit for %s can't be built", vds.cp_name)
            await self.auditor.emit(
                EventType.VD_SUBMISSION_FAIL,
                reason=VDSubmissionFailReason.HEAD_BUILD_FAILED,
            )
            await self._set_vds_fail_reason(vds, VDDBSubmissionFailReason.HEAD_BUILD_FAILED)
            return None
        except BadReturnCode:
            # um, that's not good
            await LOGGER.acritical("EMERGENCY: the HEAD commit for %s can't be run", vds.cp_name)
            await self.auditor.emit(
                EventType.VD_SUBMISSION_FAIL,
                reason=VDSubmissionFailReason.RUN_POV_FAILED,
            )
            return None

        await LOGGER.adebug("Sanitizers triggered at HEAD: %s", str(sanitizers))

        await self.auditor.emit(
            EventType.VD_SANITIZER_RESULT,
            source='HEAD',
            commit_sha='HEAD',
            disposition=Disposition.GOOD if sanitizers else Disposition.BAD,
            sanitizers_triggered=[
                workspace.sanitizer(san) for san in sanitizers
            ],
        )

        return sanitizers


    async def _test_vds_at_initial_commits(
        self,
        vds: VulnerabilityDiscovery,
        workspace: AbstractCPWorkspace,
        sanitizers_triggered_at_head: set[str],
        only_sources: set[str] | None = None,
    ) -> tuple[set[str], dict[str, set[str] | None]]:
        """
        Test the VDS at the earliest commit of each source.
        If only_sources is None, try all sources; otherwise, it should
        be a subset of sources to check.
        Returns a set of sources for which at least one sanitizer that
        was triggered at HEAD was not triggered at its earliest commit,
        indicating a source where bisection is likely to be fruitful,
        as well as a dict containing the results of each test that was
        performed as part of this process (useful information for the
        bisection algorithm).
        """
        if only_sources is None:
            sources_to_check = workspace.cp.sources.keys()
        else:
            sources_to_check = only_sources

        # We try a few early commits in case the earliest one(s) fail to
        # build, but we limit this to NUM_INITIAL_COMMIT_TESTS attempts,
        # since we don't want to get stuck testing dozens or hundreds of
        # commits one by one if there's a long stretch of non-building
        # commits at the start of the git history. If we fail that many
        # times, we give up and pass it to the bisector and let it
        # figure out what to do with it, since bisection is O(log(n)).

        sources_to_bisect = set()
        all_test_results = {}
        for source in sources_to_check:
            for i, commit in enumerate(workspace.commit_list(source)):
                if i >= NUM_INITIAL_COMMIT_TESTS:
                    sources_to_bisect.add(source)
                    break

                await LOGGER.adebug(
                    "Initial-commit testing: building at %s (commit #%d of source %s)",
                    commit, i, source
                )

                try:
                    workspace.set_src_repo_by_name(source)
                    await workspace.checkout(commit)
                    await workspace_build_or_raise(workspace, None)
                    sanitizers = await workspace.check_sanitizers(
                        vds.pov_data_sha256, vds.pov_harness
                    )
                    all_test_results[commit] = sanitizers
                except git.exc.GitCommandError:
                    # skip it and try the next one, I guess
                    all_test_results[commit] = None
                    continue
                except (WorkspaceBuildError, BadReturnCode):
                    # try the next one
                    all_test_results[commit] = None
                    continue

                break

            if source in sources_to_bisect:
                # We must've hit NUM_INITIAL_COMMIT_TESTS -- skip
                # further processing
                continue

            # The source is worth bisecting if at least one
            # sanitizer that was triggered at HEAD was not triggered
            # at this initial commit
            if sanitizers_triggered_at_head - sanitizers:
                sources_to_bisect.add(source)

            await self.auditor.emit(
                EventType.VD_SANITIZER_RESULT,
                source=source,
                commit_sha=workspace.current_commit(),
                disposition=Disposition.GOOD,
                sanitizers_triggered=[
                    workspace.sanitizer(san) for san in sanitizers
                ],
            )

        return sources_to_bisect, all_test_results

    async def _test_vds_check_for_duplicate(
        self,
        vds: VulnerabilityDiscovery,
        vd_submission: VDSubmission,
    ) -> bool:
        """
        Check if this VD submission should be rejected as a duplicate.
        True = is duplicate, reject. False = seems unique.
        Will block waiting for pending potential-duplicate submissions
        to be resolved, if necessary.
        """
        while True:
            wait_and_retry = False

            async with db_session() as db:
                submissions_for_commit = (
                    await db.execute(
                        select(VulnerabilityDiscovery).where(
                            VulnerabilityDiscovery.id != vds.id,
                            VulnerabilityDiscovery.pou_commit_sha1 == vd_submission.pou.commit_sha1.lower(),
                        )
                    )
                ).fetchall()
                async with CapiClient() as client:
                    for (other,) in submissions_for_commit:
                        current_status = other.status
                        if other.remote_uuid is not None and current_status == FeedbackStatus.PENDING:
                            current_status, _, _ = await CapiCommTaskRunner(client) \
                                .update_vds_status_from_capi(str(other.id), db)

                        if current_status == FeedbackStatus.PENDING:
                            # CAPI's still checking -- we need to wait and see what it
                            # decides, so let's sleep for a bit before checking again
                            await LOGGER.adebug(
                                "Duplicate checking: waiting on pending submission %s / %s",
                                other.id, other.remote_uuid,
                            )
                            wait_and_retry = True
                        elif current_status == FeedbackStatus.ACCEPTED:
                            # Definitely a duplicate in this case -- CAPI would reject it
                            await LOGGER.adebug("Duplicate: %s / %s", other.id, other.remote_uuid)
                            return True
                        elif current_status == FeedbackStatus.NOT_ACCEPTED:
                            # CAPI doesn't consider rejected VDSes as duplicates
                            pass

            if wait_and_retry:
                await asyncio.sleep(CAPI_PENDING_RETRY_INTERVAL)
            else:
                break

        return False

    async def _test_vds_submit_to_capi(
        self,
        vds: VulnerabilityDiscovery,
        vd_submission: VDSubmission,
    ) -> str | None:
        """
        The final step of VDS testing: submitting a VDSubmission to CAPI.
        Returns the VD_UUID if submission is successful.
        """
        while True:
            async with db_session() as db:
                await db.execute(
                    update(VulnerabilityDiscovery)
                    .where(VulnerabilityDiscovery.id == vds.id)
                    .values(checking_status=CheckingStatus.READY_TO_SUBMIT_TO_CAPI)
                )

            async with CapiClient() as client:
                submission_result, vd_uuid = await client.submit_vds(vd_submission)

            if submission_result == CapiSubmissionResult.ACCEPTED_PENDING:
                return vd_uuid
            elif submission_result == CapiSubmissionResult.REJECTED:
                await self.auditor.emit(
                    EventType.VD_SUBMISSION_FAIL,
                    reason=VDSubmissionFailReason.CAPI_REJECTED,
                )
                await self._set_vds_fail_reason(vds, VDDBSubmissionFailReason.CAPI_REJECTED)
                return None
            else:  # CapiSubmissionResult.ERROR_TRY_AGAIN
                await LOGGER.adebug("VD submission: waiting %d seconds and trying again...", CAPI_TRY_AGAIN_INTERVAL)

            await asyncio.sleep(CAPI_TRY_AGAIN_INTERVAL)

    async def test_gp(self, gp: GeneratedPatch, vds: VulnerabilityDiscovery):
        try:
            if gp_uuid := await self._test_gp(gp, vds):
                await self.auditor.emit(EventType.GP_SUBMISSION_SUCCESS)
                async with db_session() as db:
                    await db.execute(
                        update(GeneratedPatch)
                        .where(GeneratedPatch.id == gp.id)
                        .values(
                            remote_uuid=UUID(gp_uuid),
                            checking_status=CheckingStatus.DONE,
                        )
                    )
            else:
                async with db_session() as db:
                    await db.execute(
                        update(GeneratedPatch)
                        .where(GeneratedPatch.id == gp.id)
                        .values(
                            status=FeedbackStatus.NOT_ACCEPTED,
                            checking_status=CheckingStatus.DONE,
                        )
                    )
        except Exception:
            await LOGGER.adebug(f"Exception during GP testing:\n{traceback.format_exc()}")
            await self.auditor.emit(
                EventType.GP_SUBMISSION_FAIL,
                reason=GPSubmissionFailReason.GENERAL_EXCEPTION,
            )
            async with db_session() as db:
                await db.execute(
                    update(GeneratedPatch)
                    .where(GeneratedPatch.id == gp.id)
                    .values(
                        status=FeedbackStatus.NOT_ACCEPTED,
                        checking_status=CheckingStatus.DONE,
                    )
                )

    async def _test_gp(self, gp: GeneratedPatch, vds: VulnerabilityDiscovery) -> str | None:
        """
        The high-level logic for testing and submitting a GP.
        Returns the GP_UUID if submission is successful.
        """
        await LOGGER.ainfo("Testing GP %s", gp)

        should_test_pov = v.get_bool('test_gps_with_pov')
        should_test_functional = v.get_bool('test_gps_functional')

        if should_test_pov or should_test_functional:
            # Building is required for running PoV or functional tests
            should_test_build = True
        else:
            should_test_build = v.get_bool('test_gps_build')

        if should_test_build:
            # note: no need to await
            # WrappedCPWorkspace.await_docker_ready(), because GPs can
            # only be submitted if a VD was previously accepted, meaning
            # Docker is clearly already running properly
            workspace_obj = WrappedCPWorkspace(self.cp_name, self.auditor)
        else:
            # don't incur the overhead of setting up a whole workspace
            # if we're not going to use it
            workspace_obj = NullAsyncContextManager()

        async with workspace_obj as workspace:
            # Check for duplicate
            if await self._test_gp_check_for_duplicate(gp):
                # CAPI doesn't immediately reject duplicate GPs anymore,
                # as of 073bcde. This is consistent with the ASC
                # Procedures and Scoring Guide (v4), which state that "a
                # CRS may re-submit a GP for the same CPV_UUID to
                # receive a higher [Program Repair Score], but this will
                # be at the cost of reducing the [Accuracy Multiplier]."
                # So GP submissions for the same CPV_UUID are not
                # outright forbidden like duplicate VDs are. We
                # therefore follow CAPI's behavior here and just log an
                # event without rejecting the GP.
                await self.auditor.emit(
                    EventType.DUPLICATE_GP_SUBMISSION_FOR_CPV_UUID,
                )
                # (tl;dr do NOT "return None" here)

            # Verify patch only modifies allowed extensions
            if not await self._test_gp_check_patch_extensions_allowed(gp):
                # (that method posts the fail reason to the auditor itself)
                return None

            if should_test_build:
                # Build with patch
                if not await self._test_gp_build_with_patch(gp, vds, workspace):
                    await self.auditor.emit(
                        EventType.GP_SUBMISSION_FAIL,
                        reason=GPSubmissionFailReason.PATCH_FAILED_APPLY_OR_BUILD,
                    )
                    return None

                await self.auditor.emit(EventType.GP_PATCH_BUILT)

            # In CAPI, the DB row is updated to "accepted" at this point, so
            # that any failures from here on will be invisible to the
            # client. However, hiding information like that would be
            # counterproductive for VAPI, so we do still observably fail if
            # anything fails after this point.

            if should_test_functional:
                # Run functional tests
                if not await workspace.run_functional_tests():
                    await self.auditor.emit(
                        EventType.GP_SUBMISSION_FAIL,
                        reason=GPSubmissionFailReason.FUNCTIONAL_TESTS_FAILED,
                    )
                    return None

                await self.auditor.emit(EventType.GP_FUNCTIONAL_TESTS_PASS)

            if should_test_pov:
                # Check if sanitizers fire
                try:
                    triggered = vds.pou_sanitizer in await workspace.check_sanitizers(
                        vds.pov_data_sha256, vds.pov_harness
                    )
                except BadReturnCode:
                    # The POV ran successfully already, so this should never happen
                    await self.auditor.emit(
                        EventType.GP_SUBMISSION_FAIL,
                        reason=GPSubmissionFailReason.RUN_POV_FAILED,
                    )
                    return None

                if triggered:
                    await self.auditor.emit(
                        EventType.GP_SUBMISSION_FAIL,
                        reason=GPSubmissionFailReason.SANITIZER_FIRED_AFTER_PATCH,
                    )
                    return None

                await self.auditor.emit(EventType.GP_SANITIZER_DID_NOT_FIRE)

            if should_test_build:
                workspace.clean_up()

            # TODO: "Intentional Vuln?" box is not fill-out-able
            # TODO: Private PoV suite?
            # TODO: mark for manual review

            gp_submission = GPSubmission(
                cpv_uuid=str(gp.cpv_uuid),
                data=b64encode(Flatfile(contents_hash=gp.data_sha256).filename.read_bytes()),
            )

            # Submit to CAPI
            return await self._test_gp_submit_to_capi(
                gp, gp_submission
            )

    async def _test_gp_check_for_duplicate(
        self,
        gp: GeneratedPatch,
    ) -> bool:
        """
        Check if this GP submission is a duplicate.
        True = is duplicate. False = seems unique
        """
        async with db_session() as db:
            submissions_for_cpv_uuid = (
                await db.execute(
                    select(
                        func.count(GeneratedPatch.id)  # pylint: disable=not-callable
                    ).where(
                        GeneratedPatch.cpv_uuid
                        == gp.cpv_uuid,  # CPV UUIDs are globally unique
                        GeneratedPatch.remote_uuid.is_not(None),
                    )
                )
            ).fetchone()

            return submissions_for_cpv_uuid[0] > 0

    async def _test_gp_check_patch_extensions_allowed(
        self,
        gp: GeneratedPatch,
    ) -> bool:
        """
        Check if this GP submission only modifies files with allowed
        extensions.
        True = no problems. False = problems were found (reject)
        """
        patchfile = Flatfile(contents_hash=gp.data_sha256)
        try:
            content = await patchfile.read()
            if content is None:
                raise ValueError("Patch file was empty")

            wtp_diffs = whatthepatch.parse_patch(content.decode("utf8"))
            if not (diffs := peek(wtp_diffs)):
                raise ValueError("No diffs in patch file")

        except Exception:  # pylint: disable=broad-exception-caught
            # Catch any exceptions utf-8 decoding or parsing
            await self.auditor.emit(
                EventType.GP_SUBMISSION_FAIL,
                reason=GPSubmissionFailReason.MALFORMED_PATCH_FILE,
            )
            return False

        for diff in diffs:
            if not diff.header:
                extension = "unparseable-header"
            else:
                _, extension = os.path.splitext(diff.header.old_path)
            if extension.lower() not in [".c", ".h", ".in", ".java"]:
                await self.auditor.emit(
                    EventType.GP_SUBMISSION_FAIL,
                    reason=GPSubmissionFailReason.PATCHED_DISALLOWED_FILE_EXTENSION,
                )
                return False

        return True

    async def _test_gp_build_with_patch(
        self,
        gp: GeneratedPatch,
        vds: VulnerabilityDiscovery,
        workspace: AbstractCPWorkspace,
    ) -> bool:
        """
        Attempt to build the CP with the GP applied.
        True = built successfully. False = unable to build (reject)
        """
        # TODO: Can't differentiate apply failure & build failure from outside ./runsh
        await LOGGER.adebug("Building GP with patch")

        source = workspace.cp.source_from_ref(vds.pou_commit_sha1)
        if source is None:
            # Should never happen; we've already validated this commit is part of the CP
            raise ValueError(
                "VDS passed tests, but by the time we tested the GP the VDS's commit "
                "was not part of the CP"
            )

        workspace.set_src_repo_by_name(source)
        ref = workspace.cp.head_ref_from_source(source)
        await workspace.checkout(ref)
        return await workspace.build(source, patch_sha256=gp.data_sha256)

    async def _test_gp_submit_to_capi(
        self,
        gp: GeneratedPatch,
        gp_submission: GPSubmission,
    ) -> str | None:
        """
        The final step of GP testing: submitting a GPSubmission to CAPI.
        Returns the VD_UUID if submission is successful.
        """
        while True:
            async with db_session() as db:
                await db.execute(
                    update(GeneratedPatch)
                    .where(GeneratedPatch.id == gp.id)
                    .values(checking_status=CheckingStatus.READY_TO_SUBMIT_TO_CAPI)
                )

            async with CapiClient() as client:
                submission_result, gp_uuid = await client.submit_gp(gp_submission)

            if submission_result == CapiSubmissionResult.ACCEPTED_PENDING:
                return gp_uuid
            elif submission_result == CapiSubmissionResult.REJECTED:
                await self.auditor.emit(
                    EventType.GP_SUBMISSION_FAIL,
                    reason=GPSubmissionFailReason.CAPI_REJECTED,
                )
                return None
            else:  # CapiSubmissionResult.ERROR_TRY_AGAIN
                pass

            await asyncio.sleep(CAPI_TRY_AGAIN_INTERVAL)


class CapiCommTaskRunner:
    # The minimum time between consecutive CAPI update requests for a
    # single VD or GP, when throttling is enabled
    THROTTLING_MIN_UPDATE_TIME = 4.0  # seconds

    def __init__(self, client: CapiClient):
        self.client = client

    async def update_vds_status_from_capi(
        self,
        vd_uuid: str,
        db: AsyncConnection | AsyncSession | None,
    ) -> tuple[FeedbackStatus, VDDBSubmissionFailReason, str | None]:
        """returns current status, and CPV_UUID if assigned"""
        if db is None:
            async with db_session() as db:
                return await self.update_vds_status_from_capi(vd_uuid, db)

        vds = (
            await db.execute(
                select(VulnerabilityDiscovery).where(
                    VulnerabilityDiscovery.id == UUID(vd_uuid)
                )
            )
        ).fetchone()

        if vds is None:
            raise ValueError(f'Unknown VD_UUID: {vd_uuid}')

        vds = vds[0]

        if vds.status != FeedbackStatus.PENDING:
            return vds.status, VDDBSubmissionFailReason.NOT_REJECTED, vds.cpv_uuid

        new_info = await self.client.check_vds(vds.remote_uuid)

        if new_info is not None:
            new_status, new_cpv_uuid = new_info

            if new_status == FeedbackStatus.NOT_ACCEPTED:
                new_fail_reason = VDDBSubmissionFailReason.CAPI_REJECTED
            else:
                new_fail_reason = VDDBSubmissionFailReason.NOT_REJECTED

            await db.execute(
                update(VulnerabilityDiscovery)
                .where(VulnerabilityDiscovery.id == vds.id)
                .values(
                    status=new_status,
                    fail_reason=new_fail_reason,
                    cpv_uuid=UUID_or_none(new_cpv_uuid),
                    last_remote_status_update_time=datetime.datetime.now(),
                )
            )
            return new_status, new_fail_reason, new_cpv_uuid

        else:
            await db.execute(
                update(VulnerabilityDiscovery)
                .where(VulnerabilityDiscovery.id == vds.id)
                .values(last_remote_status_update_time=datetime.datetime.now())
            )

            return vds.status, VDDBSubmissionFailReason.NOT_REJECTED, vds.cpv_uuid

    async def update_gp_status_from_capi(
        self,
        gp_uuid: str,
        db: AsyncConnection | AsyncSession | None,
    ) -> FeedbackStatus:
        """returns current status"""
        if db is None:
            async with db_session() as db:
                return await self.update_gp_status_from_capi(gp_uuid, db)

        gp = (
            await db.execute(
                select(GeneratedPatch).where(
                    GeneratedPatch.id == UUID(gp_uuid)
                )
            )
        ).fetchone()

        if gp is None:
            raise ValueError(f'Unknown GP_UUID: {gp_uuid}')

        gp = gp[0]

        if gp.status != FeedbackStatus.PENDING:
            return gp.status

        new_status = await self.client.check_gp(str(gp.remote_uuid))

        if new_status is not None:
            await db.execute(
                update(GeneratedPatch)
                .where(GeneratedPatch.id == gp.id)
                .values(
                    status=new_status,
                    last_remote_status_update_time=datetime.datetime.now(),
                )
            )
            return new_status

        else:
            await db.execute(
                update(GeneratedPatch)
                .where(GeneratedPatch.id == gp.id)
                .values(last_remote_status_update_time=datetime.datetime.now())
            )

            return gp.status

    async def update_all_statuses(
        self,
        db: AsyncConnection | AsyncSession | None,
        *,
        update_vds: bool,
        update_gps: bool,
        throttling: bool = True,
    ) -> None:
        """
        Query CAPI for the latest status for all pending VDs and/or GPs.
        Statuses in the database are updated.
        """
        if not update_vds and not update_gps:
            return

        if db is None:
            async with db_session() as db:
                return await self.update_all_statuses(
                    db,
                    update_vds=update_vds,
                    update_gps=update_gps,
                    throttling=throttling,
                )

        async with asyncio.TaskGroup() as tg:
            if update_vds:
                vds_rows = (
                    await db.execute(
                        select(VulnerabilityDiscovery)
                        .where(
                            VulnerabilityDiscovery.status == FeedbackStatus.PENDING,
                            VulnerabilityDiscovery.remote_uuid.is_not(None),
                        )
                    )
                ).fetchall()

                for (vds_row,) in vds_rows:
                    if throttling:
                        last_update = vds_row.last_remote_status_update_time
                        if last_update is not None:
                            seconds_since_last_update = (datetime.datetime.now() - last_update).total_seconds()
                            if seconds_since_last_update < self.THROTTLING_MIN_UPDATE_TIME:
                                # This VD's status was already updated recently -- skip
                                continue

                    # update_vds_status_from_capi() doesn't use the auditor,
                    # so we can just set it to None. We also don't share our
                    # db connection because AsyncConnection is not
                    # thread-safe
                    tg.create_task(
                        task_ignore_excs(
                            self.update_vds_status_from_capi(str(vds_row.id), None)
                        )
                    )

            if update_gps:
                gp_rows = (
                    await db.execute(
                        select(GeneratedPatch, VulnerabilityDiscovery)
                        .join(VulnerabilityDiscovery)
                        .where(
                            GeneratedPatch.status == FeedbackStatus.PENDING,
                            GeneratedPatch.remote_uuid.is_not(None),
                        )
                    )
                ).fetchall()

                for gp_row, vds_row in gp_rows:
                    if throttling:
                        last_update = gp_row.last_remote_status_update_time
                        if last_update is not None:
                            seconds_since_last_update = (datetime.datetime.now() - last_update).total_seconds()
                            if seconds_since_last_update < self.THROTTLING_MIN_UPDATE_TIME:
                                # This GP's status was already updated recently -- skip
                                continue

                    # update_gp_status_from_capi() doesn't use the auditor,
                    # so we can just set it to None. We also don't share our
                    # db connection because AsyncConnection is not
                    # thread-safe
                    tg.create_task(
                        task_ignore_excs(
                            self.update_gp_status_from_capi(str(gp_row.id), None)
                        )
                    )


v.set_default("gp_requests_dir", f"{os.environ['AIXCC_CRS_SCRATCH_SPACE']}/requests")
v.set_default("gp_request_blobs_dir", f"{os.environ['AIXCC_CRS_SCRATCH_SPACE']}/request_povs")


class UpdateGpRequestsTaskRunner:
    """
    A TaskRunner to check CAPI for the latest statuses of pending VDs,
    and post GP requests to the appropriate directory.
    """
    def __init__(self):
        self.gp_requests_directory = Path(v.get('gp_requests_dir'))
        self.gp_request_blobs_directory = Path(v.get('gp_request_blobs_dir'))

        if not self.gp_requests_directory.is_dir():
            self.gp_requests_directory.mkdir()

        if not self.gp_request_blobs_directory.is_dir():
            self.gp_request_blobs_directory.mkdir()

    async def update_gp_requests(self, db: AsyncConnection | AsyncSession | None) -> None:
        """Update VD statuses and ensure that the GP requests folder is up to date"""
        if db is None:
            async with db_session() as db:
                return await self.update_gp_requests(db)

        # Check which VDs have already had a GP requested
        already_requested_vds = set()
        for fp in self.gp_requests_directory.glob('*.toml'):
            already_requested_vds.add(fp.stem)

        # Update all VD status info from CAPI
        async with CapiClient() as client:
            await CapiCommTaskRunner(client).update_all_statuses(db, update_vds=True, update_gps=False)

        # Check for accepted VDs
        vds_rows = (
            await db.execute(
                select(VulnerabilityDiscovery)
                .where(VulnerabilityDiscovery.status == FeedbackStatus.ACCEPTED)
            )
        ).fetchall()

        for (vds_row,) in vds_rows:
            if str(vds_row.id) not in already_requested_vds:
                await LOGGER.adebug(f'Creating new GP request for {vds_row.id}')
                await self.create_gp_request(vds_row)

    async def create_gp_request(self, vds: VulnerabilityDiscovery) -> None:
        """Create a GP-request TOML file for this VD"""

        # Get the source directory name
        cp = CPRegistry.instance().get(vds.cp_name)
        if cp is None:
            # should never happen
            await LOGGER.awarning(f'{vds.cp_name} does not exist')
            return

        source_name = cp.source_from_ref(vds.pou_commit_sha1)
        if source_name is None:
            # this should never happen
            # we already verified that this commit sha1 is a BIC
            raise RuntimeError(f"source was none but the commit ({vds.pou_commit_sha1}) is the BIC")

        # Copy the PoV blob file
        # NOTE: this must be done *before* the TOML file is written, to
        # avoid a race with the patch-generation subsystem
        shared_blob_file_path = self.gp_request_blobs_directory / f'{vds.id}.bin'
        blob_flatfile = Flatfile(contents_hash=vds.pov_data_sha256)
        copy_file(blob_flatfile.filename, shared_blob_file_path)

        # Create the TOML data
        file_data = f"""
cp_name = "{vds.cp_name}"
blob_file = "{shared_blob_file_path}"
harness_id = "{vds.pov_harness}"
sanitizer_id = "{vds.pou_sanitizer}"
bug_introduce_commit = "{vds.pou_commit_sha1}"
src_dir = "./src/{source_name}"
cpv_uuid = "{vds.cpv_uuid}"
""".strip('\n')

        # Write it out
        file_path = self.gp_requests_directory / f'{vds.id}.toml'
        file_path.write_text(file_data, encoding='utf-8')
