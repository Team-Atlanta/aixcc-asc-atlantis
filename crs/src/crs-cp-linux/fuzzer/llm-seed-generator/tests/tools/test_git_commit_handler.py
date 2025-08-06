import unittest
import os

from llm_seed_gen.tools.git_commit_handler import GitCommitHandler


class TestGitCommitHandler(unittest.TestCase):
    def setUp(self):
        linux_src_dir = os.getenv("LINUX_SRC")
        self.git_commit_handler = GitCommitHandler(linux_src_dir)

    def test_fetch_diff(self):
        # Invalid case
        self.assertEqual('[Error] Commit abcd not found', self.git_commit_handler.fetch_diff("abcd"))
        # Valid case
        self.assertIsNotNone(self.git_commit_handler.fetch_diff("d762a4b84"))

    def test_get_fetch_diff_tool(self):
        func, tool = self.git_commit_handler.get_fetch_diff_tool()
        # Invalid case
        self.assertEqual(self.git_commit_handler.fetch_diff("abcd"), func("abcd"))
        # Valid case
        self.assertIsNotNone(self.git_commit_handler.fetch_diff("d762a4b84"), func("d762a4b84"))

    def test_get_oneline_log(self):
        log = self.git_commit_handler.get_oneline_log()
        self.assertIsNotNone(log)
        print(log)

    def test_get_get_oneline_log_tool(self):
        func, tool = self.git_commit_handler.get_get_oneline_log_tool()
        self.assertEqual(self.git_commit_handler.get_oneline_log(), func())

    def test_get_all_commit_hashes(self):
        commit_hashes = self.git_commit_handler.get_all_commit_hashes()
        print(commit_hashes)
        self.assertNotEqual(0, commit_hashes)


if __name__ == '__main__':
    unittest.main()
