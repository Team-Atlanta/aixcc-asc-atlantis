from __future__ import annotations

from structlog.stdlib import get_logger

from competition_api.models.vds import POU
from competition_api.bisection_algorithm import algorithm as bisection_algorithm

LOGGER = get_logger(__name__)


def list_find(L, x) -> int:
    """like str.find() but for lists"""
    try:
        return L.index(x)
    except ValueError:
        return -1


class Bisector:
    """
    Class that helps to bridge the gap between the bisection algorithm
    and the messy world of CP workspaces.
    Requires a subclass to implement the methods for interacting with
    the workspace.
    """
    async def get_sources(self) -> set[str]:
        """Return a set of all sources to bisect over"""
        raise NotImplementedError("abstract method, must be implemented by subclass")

    async def get_all_commits_for_source(self, source: str) -> list[str]:
        """
        Get a chronologically ordered list of all commit hashes for the
        specified source
        """
        raise NotImplementedError("abstract method, must be implemented by subclass")

    async def test_at(self, commit: str) -> set[str] | None:
        """
        Test the CP at the specified commit, and return the set of
        sanitizer IDs that were triggered.
        If this returns None, the test failed (e.g. build error). If it
        returns a set -- even if empty -- the test succeeded.
        """
        raise NotImplementedError("abstract method, must be implemented by subclass")

    async def bisect(
        self,
        sanitizers_triggered_at_head: set[str],
        other_tests_already_performed: dict[str, set[str] | None],
        hinted_commits: set[str],
    ) -> POU | None:
        """Perform bisection on all relevant sources to identify the BIC"""
        sources = await self.get_sources()
        await LOGGER.adebug("Beginning overall bisection (sources: %s)", ', '.join(sources))

        for source in sources:
            res = await self.bisect_one_source(
                source,
                sanitizers_triggered_at_head,
                other_tests_already_performed,
                hinted_commits,
            )
            if res is not None:
                return res

        return None

    async def bisect_one_source(
        self,
        source: str,
        sanitizers_triggered_at_head: set[str],
        other_tests_already_performed: dict[str, set[str] | None],
        hinted_commits: set[str],
    ) -> POU | None:
        """Perform bisection on a single source to identify the BIC"""
        await LOGGER.adebug('Beginning bisection for source "%s"', source)

        commit_list = await self.get_all_commits_for_source(source)

        hinted_commit_indices = {list_find(commit_list, c) for c in hinted_commits}
        hinted_commit_indices.discard(-1)
        hinted_commit_indices = hinted_commit_indices

        await LOGGER.adebug(
            '(Source "%s" has %d commits (%d hinted))',
            source, len(commit_list), len(hinted_commit_indices)
        )

        if len(commit_list) < 2:
            # need at least 2, because the initial commit can't be the
            # BIC
            await LOGGER.adebug("Bisection: source has fewer than 2 commits? Exiting")
            return None

        async def test_function(index: int) -> set[str] | None:
            commit = commit_list[index]
            await LOGGER.adebug(
                "Bisection: testing at %s (commit #%d in source %s)",
                commit, index, source,
            )
            return await self.test_at(commit)

        all_tests_already_performed_by_idx = {len(commit_list) - 1: sanitizers_triggered_at_head}
        for hash, result in other_tests_already_performed.items():
            if hash in commit_list:
                all_tests_already_performed_by_idx[commit_list.index(hash)] = result

        result = await bisection_algorithm(
            len(commit_list),
            all_tests_already_performed_by_idx,
            hinted_commit_indices,
            test_function,
        )

        if result is None:
            return None
        else:
            bic_index, pou_sanitizer = result
            return POU(
                commit_sha1=commit_list[bic_index],
                sanitizer=pou_sanitizer,
            )
