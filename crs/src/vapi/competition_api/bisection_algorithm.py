"""
This file implements the core bisection algorithm. It doesn't depend on
any other VAPI source files, and can be run standalone for testing.

The algorithm operates on a single linear sequence of commits, and
refers to them by integer indices (0, 1, 2, ...) rather than SHA1
hashes. Each commit can be "tested", and the result of a test can either
be success (with a set of sanitizers that were triggered -- may be
empty) or failure (build or execution error). Some commits may be
"hinted", meaning they're considered especially likely to be
bug-inducing commits.

The goal is to find a commit that meets the definition of a bug-inducing
commit (BIC) without running very many tests, because they're
assumed to be very expensive. A BIC is defined a commit such that there
exists at least one sanitizer that was triggered at both HEAD and that
commit, and not at the previous commit.

In "normal" situations, the algorithm essentially reduces to bisection,
but it's designed to also handle weird situations sensibly.

An important design decision is that because the set of test results can
become arbitrarily messy (random failures, or weird/unexpected sets of
sanitizers triggered at certain commits), the algorithm doesn't keep L
and R variables as state, like in a traditional binary search algorithm.
Instead, at each step, it re-evaluates the "landscape" (so to speak) of
test results that have been collected so far, and selects a promising
L-R range based purely on that, without any memory of the reasons why it
chose to test each commit in the past. This design helps to ensure that
the algorithm makes smart decisions at all times.

algorithm() is the main entrypoint into the algorithm. Its docstring
explains how to use it.
"""

from __future__ import annotations

import dataclasses
import random
import string
from typing import Awaitable, Callable, Iterator

try:
    from structlog.stdlib import get_logger
    LOGGER = get_logger(__name__)
except ModuleNotFoundError:
    LOGGER = None


# Exponent used for exponential backoff when testing commits "around"
# the midpoint.
# y = round(x ** 1.5) -> 0, 1, 3, 5, 8, 11, 15, 19, 23, 27, 32, 36, ...
EXPONENTIAL_BACKOFF_EXPONENT = 1.5

VERBOSE = True


def vprint(*args, **kwargs) -> None:
    if VERBOSE:
        if LOGGER is None:
            print(*args, **kwargs)
        else:
            LOGGER.debug(*args, **kwargs)


def sign(x: int) -> int:
    """Return the sign of an integer (-1, 0, or 1)"""
    if x < 0:
        return -1
    elif x > 0:
        return 1
    else:
        return 0


def delta_sequence(limit: int) -> Iterator[int]:
    """0, -1, 1, -2, 2, -3, 3, ... (OEIS A130472)"""
    if limit <= 0: return

    i = 0
    yield i
    limit -= 1
    if limit == 0: return

    while True:
        i += 1

        yield -i
        limit -= 1
        if limit == 0: return

        yield i
        limit -= 1
        if limit == 0: return

assert [a for a in delta_sequence(5)] == [0, -1, 1, -2, 2]


def tag() -> str:
    """short random alphanumeric string"""
    s = ''
    for _ in range(8):
        s += random.choice(string.ascii_letters + string.digits)
    return s


# Below: algebraic enums using design pattern from https://stackoverflow.com/a/71519690
# (this makes me wish I had written this in Rust)

@dataclasses.dataclass
class IndividualSuccessResult:
    """
    Result of testing at one commit: PoV ran successfully, and triggered
    zero or more sanitizers
    """
    sanitizers: set[str]  # keep in mind that this may be empty!
    def __str__(self) -> str:
        return f'Success<{",".join(sorted(self.sanitizers))}>'
@dataclasses.dataclass
class IndividualFailureResult:
    """
    Result of testing at one commit: CP couldn't be built, or some other
    error prevented us from getting a meaningful result.
    We assume that CAPI would also fail to build here, and therefore,
    neither this commit nor the one following it can be chosen as a BIC.
    """
    def __str__(self) -> str:
        return 'Failure'
type IndividualResult = IndividualSuccessResult | IndividualFailureResult
# "IndividualResult | None" means a test may not have been attempted yet

@dataclasses.dataclass
class BicStatusYes:
    """The commit definitely meets the definition of a BIC"""
    sanitizer: str  # a sanitizer that would be fine to pick for the PoU
@dataclasses.dataclass
class BicStatusNo:
    """The commit definitely does not meet the definition of a BIC"""
    pass
type BicStatus = BicStatusYes | BicStatusNo
# "BicStatus | None" means more testing may be necessary before a
# definitive determination can be made


class ResultsObserver:
    """
    This class just watches the results of each test (from calls to
    report_result()), and draws logical conclusions about
    (possible or actual) BICs.
    It doesn't have any insight into -- or subjective suggestions for --
    the binary-search logic. It just tells you the facts.
    """
    num_commits: int
    _results: dict[int, IndividualResult]  # {commit index: test result}

    def __init__(self, num_commits: int):
        self.num_commits = num_commits
        self._results = {}

    def report_result(self, index: int, result: IndividualResult) -> None:
        self._results[index] = result

    def get_result(self, index: int) -> IndividualResult | None:
        return self._results.get(index)

    @property
    def sanitizers_triggered_at_head(self) -> set[str]:
        res = self.get_result(self.num_commits - 1)
        if not isinstance(res, IndividualSuccessResult):
            raise ValueError('no sanitizers were triggered at HEAD')
        return res.sanitizers

    def is_tested(self, index: int) -> bool:
        return index in self._results

    def bic_info(self, index: int) -> BicStatus | None:
        """
        Check whether the indicated commit is a valid BIC, and if so,
        find its PoU sanitizer
        """
        if index <= 0:
            # The initial commit is never allowed to be the BIC
            return BicStatusNo()

        commit = self.get_result(index)
        commit_prev = self.get_result(index - 1)

        if isinstance(commit, IndividualFailureResult) or isinstance(commit_prev, IndividualFailureResult):
            # At least one of them couldn't be built/tested
            # successfully, which means we can't use this as a BIC
            return BicStatusNo()

        if isinstance(commit, IndividualSuccessResult) and self.sanitizers_triggered_at_head.isdisjoint(commit.sanitizers):
            # There needs to be at least one sanitizer in common between
            # HEAD and the commit. If there's not, this can't be a BIC
            return BicStatusNo()

        if isinstance(commit_prev, IndividualSuccessResult) and self.sanitizers_triggered_at_head.issubset(commit_prev.sanitizers):
            # There needs to be at least one sanitizer in HEAD that
            # didn't also fire at the previous commit. Therefore, if
            # every sanitizer in HEAD also fired at the previous commit,
            # this can't be a BIC
            return BicStatusNo()

        if commit is None or commit_prev is None:
            # At least one of them hasn't been tested yet
            return None

        assert isinstance(commit, IndividualSuccessResult)
        assert isinstance(commit_prev, IndividualSuccessResult)

        # The condition for a BIC: at least one sanitizer that triggered
        # in both HEAD and commit did not trigger at commit_prev
        pou_sanitizers = (self.sanitizers_triggered_at_head & commit.sanitizers) - commit_prev.sanitizers
        if pou_sanitizers:
            # Pick one arbitrarily, but deterministically
            one_sanitizer = sorted(pou_sanitizers)[0]
            return BicStatusYes(one_sanitizer)
        else:
            return BicStatusNo()

    def is_bic(self, index: int) -> bool | None:
        """
        Check whether the indicated commit is a valid BIC.
        True = yes, False = no, None = needs further testing before
        there can be a definitive answer
        """
        match self.bic_info(index):
            case BicStatusYes(_):
                return True
            case BicStatusNo():
                return False
            case _:
                return None

    def is_untested_possible_bic(self, index: int) -> bool:
        """
        Return True if the indicated commit is untested and hasn't been
        ruled out as a possible BIC (if so, this commit could be worth
        testing)
        """
        return (not self.is_tested(index)) and (self.is_bic(index) in {True, None})

    def could_be_bic_if_prev_commit_was_tested(self, index: int) -> bool:
        """
        Return True if the indicated commit has already been tested, and
        *might* be a BIC, depending on the result of the commit before
        it, which hasn't been tested yet (if so, the previous commit
        could be worth testing)
        """
        return self.is_tested(index) and (not self.is_tested(index - 1)) and (self.is_bic(index) in {True, None})

    def find_bic(self) -> int | None:
        """
        Based on all information collected thus far, check if any
        commits can be blamed as the BIC. If so, return the index of one
        of them.
        """
        # If there are multiple BICs, we pick the oldest one because,
        # intuitively, it's probably the one that a human would be the
        # most likely to pick. It doesn't really matter, though.
        for idx in sorted(self._results.keys()):
            if self.is_bic(idx):
                return idx

        return None

    def __str__(self) -> str:
        return f'BisectionObserver<{",".join(str(self.get_result(i)) for i in range(self.num_commits))}>'


def iter_L_options(observer: ResultsObserver, *, prefix: str | None = None) -> Iterator[int]:
    """Yield possible L values"""
    if prefix is None:
        prefix = f'[{tag()}] '
    else:
        prefix += '- '
    vprint(f'{prefix}iter_L_options(observer)')
    prefix2 = prefix + 'iter_L_options(): '

    # A limit for walking the L value upward. The initial value should
    # let it use the entire range, so point it to the most recent commit
    # (aka num_commits - 1) plus one
    last_yielded = observer.num_commits

    # Starting at the end and working backwards, look for any test
    # results where at least one sanitizer that was triggered at HEAD
    # was not triggered. These form starting points for potential lower
    # bounds
    for L in range(observer.num_commits - 1, -1, -1):  # from last commit to first commit, inclusive
        result_L = observer.get_result(L)

        # We forgive the commit at L==0 if it's failure or untested, but
        # not if it's successful and looks obviously bad
        if isinstance(result_L, IndividualSuccessResult):
            if not (observer.sanitizers_triggered_at_head - result_L.sanitizers):
                continue
        elif L != 0:
            continue

        vprint(f'{prefix2}beginning walk-up from {L} ({result_L!s})')

        # Now we "walk" it upward until we find a commit that could
        # conceivably be a BIC.
        # We stop at last_yielded (non-inclusive), because we only want
        # to yield a value smaller than the last one we yielded. (This
        # limit also makes this part of the algorithm O(n) worst-case
        # instead of O(n^2).)
        # Note that we begin at L+1 because we chose L as a possible
        # "previous commit". If it could also itself be a BIC, that's a
        # separate fact that can be explored by the algorithm later.
        for L2 in range(L + 1, last_yielded):  # from L+1 to last_yielded-1, inclusive
            if observer.is_bic(L2) in {True, None}:
                vprint(f'{prefix2}yielding L={L2}')
                yield L2
                last_yielded = L2
                break

            # Also stop early if we hit a commit that indicates we've
            # gone too far
            result_L2 = observer.get_result(L2)
            if isinstance(result_L2, IndividualSuccessResult):
                if not (observer.sanitizers_triggered_at_head - result_L2.sanitizers):
                    vprint(f'{prefix2}ending walk-up because we hit {L2} ({result_L2})')
                    break

        else:
            vprint(f'{prefix2}ending walk-up because the loop ended after {last_yielded-1}')

    vprint(f'{prefix2}giving up')


def pick_R(observer: ResultsObserver, L: int, *, prefix: str | None = None) -> int | None:
    """Given a left bound, try to find a reasonable right bound"""
    if prefix is None:
        prefix = f'[{tag()}] '
    else:
        prefix += '- '
    vprint(f'{prefix}pick_R(observer, {L})')
    prefix2 = prefix + 'pick_R(): '

    # First, check what sanitizers were triggered immediately prior to
    # L, or the closest commit before it for which we have that
    # information
    sanitizers_expected_at_Lm1 = set()  # default: optimistically assume none
    where_checked = '(beginning)'
    for other in range(L - 1, -1, -1):  # from L-1 to first commit, inclusive
        result = observer.get_result(other)
        if isinstance(result, IndividualSuccessResult):
            sanitizers_expected_at_Lm1 = result.sanitizers
            where_checked = other
            break

    vprint(
        f'{prefix2}sanitizers at {where_checked} are {sanitizers_expected_at_Lm1}'
        f' -- using that as a proxy for L-1 ({L-1})'
    )

    # There needs to be at least one sanitizer triggered at HEAD and not
    # at the lower end of the L-R range. If that's not the case, give up
    if observer.sanitizers_triggered_at_head.issubset(sanitizers_expected_at_Lm1):
        vprint(f"{prefix2}that doesn't seem to work, so, giving up here")
        return None

    # Starting at L and working forwards, look for a commit such that
    # there exists a sanitizer triggered in HEAD and that commit, and
    # not at L (or its proxy)
    for R in range(L, observer.num_commits):  # from L to last commit, inclusive
        result_R = observer.get_result(R)

        # Note: no need to "forgive" failure or untested results at
        # R==end like we do at L==0, because the HEAD commit is
        # guaranteed to already be tested successfully
        if not isinstance(result_R, IndividualSuccessResult):
            continue
        # If we reach a commit at which there are no new sanitizers
        # triggered compared to those expected at L-1, we should give up
        if result_R.sanitizers.issubset(sanitizers_expected_at_Lm1):
            return None
        # Otherwise, this is worth trying as a starting point for R

        vprint(f'{prefix2}beginning walk-down from {R}')

        # Just like we did with L, we now walk this backwards until we find
        # a possible BIC.
        # This time, we consider both R and L as possible BICs (i.e.,
        # start at R, not R-1).
        most_recently_seen_R2_sanitizers = result_R.sanitizers
        for R2 in range(R, L - 1, -1):  # from R to L, inclusive
            result_R2 = observer.get_result(R2)
            if isinstance(result_R2, IndividualSuccessResult):
                most_recently_seen_R2_sanitizers = result_R2.sanitizers

            # R must be both a BIC candidate *and* look like a
            # legitimate pairing for the "L" we've found.
            # For example, consider a range of commit test results
            # [{id_1}, None, None, {id_1}]. Even though R==3 could
            # technically be a BIC (since commit 2 might trigger zero
            # sanitizers), we don't want to pick it, because there's no
            # good reason to bisect over [0, 3], since R==3 wouldn't
            # form a BIC with L==0 if they were hypothetically adjacent.
            if observer.is_bic(R2) in {True, None} \
                    and ((observer.sanitizers_triggered_at_head & most_recently_seen_R2_sanitizers) - sanitizers_expected_at_Lm1):
                vprint(f'{prefix2}returning R={R2}')
                return R2

        vprint(f'{prefix2}ending walk-up because the loop ended')

    # No apparent R value to pair up with this L...
    vprint(f'{prefix2}giving up')
    return None


def iter_L_R_ranges(observer: ResultsObserver, *, prefix: str | None = None) -> Iterator[tuple[int, int]]:
    """
    Iterate over possible L-to-R ranges that could be used for the next
    bisection step.
    Somewhat more specifically, this is defined as a range of commit
    indices that we believe is likely to contain a BIC.
    The L and R values are both inclusive (aka in [0, num_commits - 1]).
    """
    if prefix is None:
        prefix = f'[{tag()}] '
    else:
        prefix += '- '
    vprint(f'{prefix}iter_L_R_ranges(observer)')
    prefix2 = prefix + 'iter_L_R_ranges(): '

    for L in iter_L_options(observer, prefix=prefix):
        if (R := pick_R(observer, L, prefix=prefix)) is not None:
            # (just in case)
            if L > R:
                vprint(f'{prefix2}skipping {L}-{R} because L > R')
                continue

            vprint(f'{prefix2}yielding {L}-{R} as a L-R range')
            yield L, R
        else:
            vprint(f'{prefix2}got L={L}, but no corresponding R')

    vprint(f'{prefix2}done')


def pick_next_test_location(
    observer: ResultsObserver,
    hinted_commit_indices: set[int],
    *,
    prefix: str | None = None,
) -> int | None:
    """Select the next index at which we should perform a test"""
    if prefix is None:
        prefix = f'[{tag()}] '
    else:
        prefix += '- '
    vprint(f'{prefix}pick_next_test_location(observer, {hinted_commit_indices})')
    prefix2 = prefix + 'pick_next_test_location(): '

    # Before anything else: if a BIC can be positively identified right
    # now, there's obviously no need to run another test, and we should
    # terminate
    if observer.find_bic() is not None:
        vprint(f'{prefix2}BIC is found -- stopping immediately')
        return None

    # Try various L-R ranges we might want to use for bisection
    for L, R in iter_L_R_ranges(observer, prefix=prefix):
        vprint(f'{prefix2}got L-R range: {L}-{R}')

        # Which hints are still in the range, and which of those aren't
        # yet tested?
        hints_in_range = {c for c in hinted_commit_indices if L <= c <= R}
        vprint(f'{prefix2}hints in range: {hints_in_range}')
        untested_hints_in_range = {c for c in hints_in_range if not observer.is_tested(c)}
        vprint(f'{prefix2}untested hints in range: {untested_hints_in_range}')

        if untested_hints_in_range:
            # Pick the one closest to the middle, and test there.
            # delta_sequence() isn't needed here, because hint tests
            # that fail will naturally drop out of the "untested hints"
            # set in the next algorithm iteration, leading to a
            # different hint-midpoint
            if len(untested_hints_in_range) % 2 == 0:
                # If there's an even number of untested hints in range,
                # as a tiebreaker, favor whichever one is closer to the
                # actual midpoint of the range
                true_midpoint = (L + R) // 2
                option_1 = sorted(untested_hints_in_range)[len(untested_hints_in_range) // 2 - 1]
                option_2 = sorted(untested_hints_in_range)[len(untested_hints_in_range) // 2]
                if abs(option_1 - true_midpoint) < abs(option_2 - true_midpoint):
                    ret = option_1
                else:
                    ret = option_2
            else:
                # Odd number of untested hints in range -- no ambiguity
                ret = sorted(untested_hints_in_range)[len(untested_hints_in_range) // 2]
            vprint(f'{prefix2}returning middle untested hint: {ret}')
            return ret

        # If we reach this point, all hints still in this range have
        # been tested. I *think* there can logically only be one hint
        # still in range at this point, but either way: ensure that all
        # of the ones that might be a BIC have had their previous commit
        # tested (in reverse chronological order)
        for commit_idx in sorted(hints_in_range, reverse=True):
            if observer.could_be_bic_if_prev_commit_was_tested(commit_idx):
                # No delta_sequence() necessary here
                vprint(f'{prefix2}returning {commit_idx - 1}, which precedes possible-BIC hint {commit_idx}')
                return commit_idx - 1

        # At this point, we've done all we can with hints.
        # Pick the untested commit closest to the middle and test there.
        # Ideally this will affect L/R on the next iteration; if not, we
        # pick "nearby" commits (spiraling outward with exponential
        # backoff) and test there instead

        # First, limit the search to only untested possible BICs, since
        # those should take priority...
        middle = (L + R) // 2
        vprint(f'{prefix2}ideal midpoint: {middle}')
        for delta in delta_sequence(observer.num_commits * 4):
            delta = round(abs(delta) ** EXPONENTIAL_BACKOFF_EXPONENT) * sign(delta)
            commit_idx = middle + delta
            if not (L <= commit_idx <= R):
                continue
            if observer.is_untested_possible_bic(commit_idx):
                vprint(f'{prefix2}returning {commit_idx} as an untested-possible-BIC midpoint')
                return commit_idx
            else:
                vprint(f"{prefix2}skipping midpoint {commit_idx} as it's either tested or can't be a BIC")
        # ...then just any untested commits
        for delta in delta_sequence(observer.num_commits * 4):
            delta = round(abs(delta) ** EXPONENTIAL_BACKOFF_EXPONENT) * sign(delta)
            commit_idx = middle + delta
            if not (L <= commit_idx <= R):
                continue
            if not observer.is_tested(commit_idx):
                vprint(f'{prefix2}returning {commit_idx} as an untested midpoint')
                return commit_idx
            else:
                vprint(f"{prefix2}skipping midpoint {commit_idx} as it's already tested")

        # If we reach here, we've tested enough commits in this L-R
        # range to be reasonably confident that none of them will work.
        # Still, if any of them (R especially) could be the BIC and is
        # just lacking a test at the previous commit to confirm it, be
        # sure to do that
        for other in range(R, L - 1, -1):  # from R to L, inclusive
            if observer.could_be_bic_if_prev_commit_was_tested(other):
                vprint(f'{prefix2}returning {other - 1} since {other} is in range and could be a BIC depending on this test')
                return other - 1

        # At this point, it seems this L-R range is most likely a dud
        # (though we don't want to waste time testing every single
        # commit to make sure). Loop again to move on to the next L-R
        # range.

    # We've checked all L-R ranges, and none have worked. Time to give
    # up.
    vprint(f'{prefix2}giving up')
    return None


async def algorithm(
    num_commits: int,
    tests_already_performed: dict[int, set[str] | None],
    hinted_commit_indices: set[int],
    test_function: Callable[[int], Awaitable[set[str] | None]],
) -> tuple[int, str] | None:
    """
    Run the bisection algorithm.

    - num_commits: the total number of commits in the linear git history
      we're bisecting over, including both the initial commit and HEAD
    - tests_already_performed: a mapping of commit indices to sets of
      triggered sanitizers (or None, to indicate failed tests), for any
      tests that have already been performed. This MUST include, at
      minimum, the HEAD commit, which MUST have had a successful test
      (at least one sanitizer triggered).
    - hinted_commit_indices: the indices of any commits that are hinted
      to be the BIC
    - test_function: an async function that takes a commit index, tests
      that commit, and returns the set of sanitizers that were
      triggered, or None if there was an error

    If a BIC is found, return its index and the name of the sanitizer to
    use in the PoU. Otherwise, return None.
    """
    prefix = f'[{tag()}] '
    vprint(f'{prefix}algorithm({num_commits}, {tests_already_performed}, {hinted_commit_indices}, test_function)')
    prefix2 = prefix + 'algorithm(): '

    if num_commits <= 1:
        vprint(f'{prefix2}too few commits ({num_commits}) -- giving up')
        return None

    hinted_commit_indices = set(hinted_commit_indices)
    hinted_commit_indices.discard(0)  # just in case (initial commit can't be BIC)

    # Create the ResultsObserver, and report the results of all tests
    # already performed
    observer = ResultsObserver(num_commits)
    for commit_idx, result in tests_already_performed.items():
        if result is not None:
            observer.report_result(commit_idx, IndividualSuccessResult(set(result)))
        else:
            observer.report_result(commit_idx, IndividualFailureResult())

    # Ensure that we can check which sanitizers were triggered at HEAD
    try:
        observer.sanitizers_triggered_at_head
    except ValueError:
        print('WARNING: no reported result for test at HEAD -- skipping bisection')
        return None
    if not observer.sanitizers_triggered_at_head:
        print('WARNING: no sanitizers were triggered at HEAD -- skipping bisection')
        return None

    vprint(f'{prefix2}sanitizers triggered at head: {observer.sanitizers_triggered_at_head}')

    # As long as pick_next_test_location() continues to suggest new
    # commits to test at, test at them
    # (note that it stops suggesting hints the moment a BIC can be
    # positively identified)
    while True:
        vprint(f'{prefix2}observer current state: {observer!s}')
        commit_idx = pick_next_test_location(observer, hinted_commit_indices, prefix=prefix)
        vprint(f'{prefix2}pick_next_test_location() -> {commit_idx}')

        if commit_idx is None:
            vprint(f'{prefix2}(breaking from loop)')
            break

        # This shouldn't happen, but as an extra safeguard against
        # infinite looping: if we've already tested this commit,
        # pick_next_test_location() has reached some sort of fixed
        # point, so we have to break
        if (res := observer.get_result(commit_idx)) is not None:
            vprint(
                f"{prefix2}breaking from loop because we've already tested at {commit_idx} ({res})"
            )
            break

        if (sanitizers := await test_function(commit_idx)) is not None:
            vprint(f'{prefix2}reporting success ({sanitizers}) at {commit_idx}')
            observer.report_result(commit_idx, IndividualSuccessResult(sanitizers))
        else:
            vprint(f'{prefix2}reporting failure at {commit_idx}')
            observer.report_result(commit_idx, IndividualFailureResult())

    vprint(f'{prefix2}loop finished')

    # Now that it's run out of suggestions, return the BIC if one can be
    # identified from the results
    if (bic_index := observer.find_bic()):
        bic_status = observer.bic_info(bic_index)
        vprint(f'{prefix2}status for BIC at {bic_index} is {bic_status}')
        assert isinstance(bic_status, BicStatusYes)
        return (bic_index, bic_status.sanitizer)
    else:
        vprint(f'{prefix2}no BIC found')
        return None
