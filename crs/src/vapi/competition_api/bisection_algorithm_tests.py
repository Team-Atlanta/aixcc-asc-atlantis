"""
Unit tests for bisection_algorithm.py
"""

from bisection_algorithm import \
    IndividualSuccessResult, IndividualFailureResult, IndividualResult, \
    ResultsObserver, iter_L_R_ranges, pick_next_test_location


SN = IndividualSuccessResult(set())  # noqa: F841
S1 = IndividualSuccessResult({'id_1'})  # noqa: F841
S2 = IndividualSuccessResult({'id_2'})  # noqa: F841
S3 = IndividualSuccessResult({'id_3'})  # noqa: F841
S12 = IndividualSuccessResult({'id_1', 'id_2'})  # noqa: F841
S13 = IndividualSuccessResult({'id_1', 'id_3'})  # noqa: F841
S23 = IndividualSuccessResult({'id_2', 'id_3'})  # noqa: F841
S123 = IndividualSuccessResult({'id_1', 'id_2', 'id_3'})  # noqa: F841
F = IndividualFailureResult()
N = None


def run_L_R_tests():
    """
    Unit tests for the L/R range selection portion of the algorithm,
    which is the most difficult part to reason about
    """
    def try_L_R(
        commits: list[IndividualResult | None],
    ) -> list[tuple[int, int]]:
        """
        Helper function to run iter_L_R_ranges() on test data and return
        the top pick
        """
        assert isinstance(commits[-1], IndividualSuccessResult)
        observer = ResultsObserver(len(commits))
        for i, commit in enumerate(commits):
            if commit is not None:
                observer.report_result(i, commit)
        print('Testing', observer)
        results = []
        for L, R in iter_L_R_ranges(observer):
            results.append((L, R))
        return results

    def check_L_R(
        title: str,
        commits: list[IndividualResult | None],
        expected: list[tuple[int, int]],
    ) -> None:
        print('-' * 30)
        print(title)
        actual = try_L_R(commits)
        if actual != expected:
            raise ValueError(f'expected: {expected} / actual: {actual}')
        print(f'Test success ({expected} == {actual})')

    check_L_R(
        'Common initial state 1',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, N, N, S23],
        #   ---------------------
        [(1, 7)],
    )
    check_L_R(
        'Common initial state 2',
        # 0 1  2  3  4  5  6  7
        [F, N, N, N, N, N, N, S23],
        #      ------------------
        [(2, 7)],
    )
    check_L_R(
        'Common initial state 3',
        # 0 1  2  3    4  5  6  7
        [N, N, N, S23, N, N, N, S23],
        #   ---------
        [(1, 3)],
    )
    check_L_R(
        'Common initial state 4',
        # 0 1  2  3    4  5  6  7
        [N, N, N, S13, N, N, N, S23],
        #              ------------
        #   ---------
        [(4, 7), (1, 3)],
    )
    check_L_R(
        'Common initial state 5',
        # 0 1  2  3  4  5  6  7
        [N, N, N, F, N, N, N, S23],
        #   ---------------------
        [(1, 7)],
    )

    check_L_R(
        'A pretty normal case',
        # 0   1  2  3    4  5    6  7  8  9    10 11 12
        [S13, N, N, S13, F, S13, N, N, N, S23, N, N, S23],
        #                        ------------
        [(6, 9)],
    )

    check_L_R(
        'None of the commits preceding HEAD have any fewer sanitizers than it',
        # 0   1  2    3  4  5  6
        [S12, N, S23, N, F, F, S2],
        [],
    )

    check_L_R(
        'Failure preceding what would otherwise be R',
        # 0   1  2  3    4  5    6  7  8  9    10 11 12
        [S13, N, N, S13, F, S13, N, N, F, S23, N, N, S23],
        #                        ----
        [(6, 7)],
    )

    check_L_R(
        "Failure at what would otherwise be L (note: 7 can't be the BIC because 6 failed)",
        # 0   1  2  3    4  5    6  7  8  9    10 11 12
        [S13, N, N, S13, F, S13, F, N, N, S23, N, N, S23],
        #                              ------
        [(8, 9)],
    )

    check_L_R(
        'Subset preceding the newest commit matching HEAD',
        # 0   1  2  3    4  5    6  7  8    9    10 11 12
        [S13, N, N, S13, F, S13, N, N, S13, S23, N, N, S23],
        #                                   ---
        [(9, 9)],
    )

    check_L_R(
        'String of failures between newest commit matching HEAD and the previous subset commit',
        # 0   1  2  3    4  5    6  7  8  9    10 11 12
        [S13, N, N, S13, F, S13, F, F, F, S23, N, N, S23],
        [],
    )

    check_L_R(
        "The same, but there's an earlier range that can be used instead",
        # 0   1  2  3   4  5    6  7  8  9    10 11 12
        [S13, N, N, S1, N, S13, F, F, F, S23, N, N, S23],
        #               ------
        [(4, 5)],
    )

    check_L_R(
        'A commit before HEAD *adds* a sanitizer, and then we go back to just the HEAD sanitizers again (it should ignore that)',
        # 0   1  2  3  4    5  6  7     8  9
        [S13, N, N, N, S23, F, N, S123, N, S23],
        #     ------------
        [(1, 4)],
    )

    check_L_R(
        'No commit before HEAD that exactly matches it',
        # 0   1  2  3  4    5  6  7  8  9
        [S13, N, N, N, S13, N, N, F, N, S23],
        #                   ---------------
        [(5, 9)],
    )

    check_L_R(
        'String of failures flooding what would otherwise be the range',
        # 0   1  2  3    4  5  6
        [S13, F, F, S23, N, N, S23],
        [],
    )

    check_L_R(
        'The same, but with a None prepended',
        # 0 1    2  3  4    5  6  7
        [N, S13, F, F, S23, N, N, S23],
        #   ---
        [(1, 1)],
    )

    check_L_R(
        'Multiple L candidates in a row',
        # 0  1   2   3    4  5
        [SN, S1, S2, S13, F, S123],
        #            ---
        #        --
        #    --
        [(3, 3), (2, 2), (1, 1)],
    )

    check_L_R(
        'Oops! All Failures',
        # 0 1  2  3  4
        [F, F, F, F, S23],
        [],
    )

    check_L_R(
        'Oops! All Failures, except for the initial commit',
        # 0 1  2  3  4
        [N, F, F, F, S23],
        [],
    )

    check_L_R(
        'Oops! All Failures, except for the initial two commits',
        # 0 1  2  3  4
        [N, N, F, F, S23],
        #   -
        [(1, 1)],
    )

    check_L_R(
        'Oops! All Failures, but with two Nones in the middle',
        # 0 1  2  3  4  5  6
        [F, F, N, N, F, F, S23],
        #         -
        [(3, 3)],
    )

    check_L_R(
        'Oops! All Empty',
        # 0  1   2   3   4
        [SN, SN, SN, SN, S23],
        #                ---
        [(4, 4)],
    )

    check_L_R(
        'Oops! All HEAD',
        # 0   1    2    3    4
        [S23, S23, S23, S23, S23],
        [],
    )

    check_L_R(
        'Alternating failures and Nones (1)',
        # 0 1  2  3  4  5
        [F, N, F, N, F, S23],
        [],
    )
    check_L_R(
        'Alternating failures and Nones (2)',
        # 0 1  2  3  4  5
        [N, F, N, F, N, S23],
        #               ---
        [(5, 5)],
    )

    check_L_R('Two-commit case 1', [SN, S23], [(1, 1)])
    check_L_R('Two-commit case 2', [S13, S23], [(1, 1)])
    check_L_R('Two-commit case 3', [S23, S23], [])
    check_L_R('Two-commit case 4', [S123, S23], [])
    check_L_R('Two-commit case 5', [N, S23], [(1, 1)])
    check_L_R('Two-commit case 6', [F, S23], [])

    print('All test cases ran successfully')


def run_pick_next_test_location_tests():
    """Unit tests for pick_next_test_location()"""
    def try_pick(
        commits: list[IndividualResult | None],
        hints: set[int],
    ) -> tuple[int, int] | None:
        """
        Helper function to run pick_next_test_location() on test data
        """
        assert isinstance(commits[-1], IndividualSuccessResult)
        observer = ResultsObserver(len(commits))
        for i, commit in enumerate(commits):
            if commit is not None:
                observer.report_result(i, commit)
        print('Testing', observer)
        return pick_next_test_location(observer, hints)

    def check_pick(
        title: str,
        commits: list[IndividualResult | None],
        hints: set[int],
        expected: int | None,
    ) -> None:
        print('-' * 30)
        print(title)
        actual = try_pick(commits, hints)
        if actual != expected:
            raise ValueError(f'expected: {expected} / actual: {actual}')
        print(f'Test success ({expected} == {actual})')

    check_pick(
        'BIC exists',
        # 0 1  2  3   4   5  6  7
        [N, N, N, S2, S3, N, N, S23], set(),
        None,
    )

    check_pick(
        'No hints',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, N, N, S23], set(),
        4,
    )

    check_pick(
        'One hint',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, N, N, S23], {2},
        2,
    )

    check_pick(
        'Two hints: left one closer to center',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, N, N, S23], {3, 6},
        3,
    )

    check_pick(
        'Two hints: right one closer to center',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, N, N, S23], {1, 5},
        5,
    )

    check_pick(
        'Three hints',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, N, N, S23], {4, 5, 6},
        5,
    )

    check_pick(
        'One hint, already tested',
        # 0 1  2  3  4  5  6  7
        [N, N, F, N, N, N, N, S23], {2},
        4,
    )

    check_pick(
        'Two hints, one already tested, one not',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, F, N, S23], {2, 5},
        2,
    )

    check_pick(
        'One hint, needs its previous commit checked ASAP',
        # 0 1  2  3  4  5  6  7
        [N, N, N, N, N, N, N, S23], {7},
        6,
    )

    check_pick(
        'No hints: testing exponential-backoff spiral (1)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, N, N, N, N, N, N, N, N, N, N, N, N, N, N, N, N, N, S23], set(),
        #                              ^
        10,
    )
    check_pick(
        'No hints: testing exponential-backoff spiral (2)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, N, N, N, N, N, N, N, N, F, N, N, N, N, N, N, N, N, S23], set(),
        #                           ^  X
        9,
    )
    check_pick(
        'No hints: testing exponential-backoff spiral (3)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, N, N, N, N, N, N, N, F, F, N, N, N, N, N, N, N, N, S23], set(),
        #                     ^     X  X  *
        7,  # *11 gets skipped because it can't be a BIC (prev. commit is failure)
    )
    check_pick(
        'No hints: testing exponential-backoff spiral (4)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, N, N, N, N, N, F, N, F, F, N, N, N, N, N, N, N, N, S23], set(),
        #                     X     X  X  *     ^
        13,
    )
    check_pick(
        'No hints: testing exponential-backoff spiral (5)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, N, N, N, N, N, F, N, F, F, N, N, F, N, N, N, N, N, S23], set(),
        #               ^     X     X  X  *     X
        5,
    )
    check_pick(
        'No hints: testing exponential-backoff spiral (6)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, N, N, N, F, N, F, N, F, F, N, N, F, N, N, N, N, N, S23], set(),
        #               X     X     X  X  *     X     ^
        15,
    )
    check_pick(
        'No hints: testing exponential-backoff spiral (6)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, N, N, N, F, N, F, N, F, F, N, N, F, N, F, N, N, N, S23], set(),
        #      ^        X     X     X  X  *     X     X
        2,
    )
    check_pick(
        'No hints: testing exponential-backoff spiral (6)',
        # 0 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19
        [N, N, F, N, N, F, N, F, N, F, F, N, N, F, N, F, N, N, N, S23], set(),
        #      X        X     X     X  X  *     X     X        ^
        18,
    )
    # (after 18 gets set to F, the L-R range changes, and it starts
    # checking some different commits)

    check_pick(
        'Oops! All Failures',
        # 0 1  2  3  4
        [F, F, F, F, S23], set(),
        None,
    )

    check_pick(
        'Oops! All Failures, except for the initial commit',
        # 0 1  2  3  4
        [N, F, F, F, S23], set(),
        None,
    )

    check_pick(
        'Oops! All Failures, except for the initial two commits',
        # 0 1  2  3  4
        [N, N, F, F, S23], set(),
        #   -
        1,
    )

    check_pick(
        'Oops! All Failures, but with two Nones in the middle',
        # 0 1  2  3  4  5  6
        [F, F, N, N, F, F, S23], set(),
        #         -
        3,
    )

    check_pick(
        'Oops! All Empty',
        # 0  1   2   3   4
        [SN, SN, SN, SN, S23], set(),
        #                ---
        None,
    )

    check_pick(
        'Oops! All HEAD',
        # 0   1    2    3    4
        [S23, S23, S23, S23, S23], set(),
        None,
    )

    check_pick(
        'Alternating failures and Nones (1)',
        # 0 1  2  3  4  5
        [F, N, F, N, F, S23], set(),
        None,
    )
    check_pick(
        'Alternating failures and Nones (2)',
        # 0 1  2  3  4  5
        [N, F, N, F, N, S23], set(),
        #               ---
        4,
    )

    check_pick('Two-commit case 1', [SN, S23], set(), None)
    check_pick('Two-commit case 2', [S13, S23], set(), None)
    check_pick('Two-commit case 3', [S23, S23], set(), None)
    check_pick('Two-commit case 4', [S123, S23], set(), None)
    check_pick('Two-commit case 5.1', [N, S23], set(), 0)
    check_pick('Two-commit case 5.2', [N, S23], {1}, 0)
    check_pick('Two-commit case 6', [F, S23], set(), None)


if __name__ == '__main__':
    run_L_R_tests()
    run_pick_next_test_location_tests()
