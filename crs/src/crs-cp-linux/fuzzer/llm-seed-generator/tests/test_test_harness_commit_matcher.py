import logging
import unittest
import os

from llm_seed_gen.tools.git_commit_handler import GitCommitHandler

from llm_seed_gen.test_harness_commit_matcher import TestHarnessCommitMatcher

from llm_seed_gen.llm.model import OaiGpt4o


class TestTestHarnessCommitMatcher(unittest.TestCase):
    def setUp(self):
        linux_src_dir = os.getenv("LINUX_SRC")
        self.test_harness_dir = os.getenv("TEST_HARNESS_DIR")
        self.matcher = TestHarnessCommitMatcher(OaiGpt4o(), linux_src_dir, '../prompts', '../logs', logging.DEBUG)
        #self.commits = ['d762a4b84', '05072bf', '6818359', '607143f', '8761564', 'f5ef208', 'd2631c9', 'c93cdf1', 'c0a71e4', '4ed13ea', 'f734c8f', 'a14c6a0', '63cdbdd', 'c899a96']
        self.commits = GitCommitHandler(linux_src_dir).get_all_commit_hashes()

    def test_CVE_2022_32250(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CVE-2022-32250.c', self.commits)
        self.assertEqual(commit, 'd762a4b84')

    def test_CVE_2022_32250_2(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CVE-2022-32250-2.c', self.commits)
        self.assertEqual(commit, 'd762a4b84')

    def test_CVE_2022_0995(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CVE-2022-0995.c', self.commits)
        self.assertEqual(commit, '05072bf')

    def test_CVE_2022_0995_2(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CVE-2022-0995-2.c', self.commits)
        self.assertEqual(commit, '05072bf')

    def test_CVE_2022_0185(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CVE-2022-0185.c', self.commits)
        self.assertEqual(commit, '6818359')

    def test_CVE_2021_38208(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CVE-2021-38208.c', self.commits)
        self.assertEqual(commit, '607143f')

    def test_CVE_2023_2513(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CVE-2023-2513.c', self.commits)
        self.assertEqual(commit, '8761564')

    def test_CADET_00001(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CADET-00001.c', self.commits)
        self.assertEqual(commit, 'f5ef208')

    def test_CADET_00001_2(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CADET-00001-2.c', self.commits)
        self.assertEqual(commit, 'f5ef208')

    def test_CROMU_00001(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CROMU-00001.c', self.commits)
        self.assertEqual(commit, 'd2631c9')

    def test_CROMU_00003(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CROMU-00003.c', self.commits)
        self.assertEqual(commit, 'c93cdf1')

    def test_CROMU_00004(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CROMU-00004.c', self.commits)
        self.assertEqual(commit, 'c0a71e4')

    def test_CROMU_00005(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/CROMU-00005.c', self.commits)
        self.assertEqual(commit, '4ed13ea')

    def test_KPRCA_00001(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/KPRCA-00001.c', self.commits)
        self.assertEqual(commit, 'f734c8f')

    def test_NRFIN_00001(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/NRFIN-00001.c', self.commits)
        self.assertEqual(commit, 'a14c6a0')

    def test_NRFIN_00003(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/NRFIN-00003.c', self.commits)
        self.assertEqual(commit, '63cdbdd')

    def test_BRAD_OBERBERG(self):
        commit = self.matcher.match(f'{self.test_harness_dir}/BRAD-OBERBERG.c', self.commits)
        self.assertEqual(commit, 'c899a96')


if __name__ == '__main__':
    unittest.main()
