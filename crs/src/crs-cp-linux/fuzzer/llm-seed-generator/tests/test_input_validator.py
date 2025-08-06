import unittest
from unittest.mock import patch

from llm_seed_gen.input_validator import InputValidator


class TestInputValidator(unittest.TestCase):
    def setUp(self):
        self.validator = InputValidator()

    @patch('llm_seed_gen.utils.error.fatal')
    def test_validate_linux_src_repo_path(self, mock_fatal):
        self.assertIsNone(self.validator.validate_linux_src_repo_path(''))
        self.assertEqual(1, mock_fatal.call_count)
        self.assertIsNone(self.validator.validate_linux_src_repo_path('/home'))
        self.assertEqual(2, mock_fatal.call_count)
        self.assertIsNone(self.validator.validate_linux_src_repo_path('../'))
        self.assertEqual(3, mock_fatal.call_count)
        self.assertIsNotNone(self.validator.validate_linux_src_repo_path('../../../'))
        self.assertEqual(3, mock_fatal.call_count)

    def test_validate_readable_file(self):
        self.assertIsNone(self.validator._validate_readable_file('../'))
        self.assertIsNone(self.validator._validate_readable_file('../prompts'))
        self.assertEqual('../run.py', self.validator._validate_readable_file('../run.py'))

    def test_validate_testlang(self):
        fallback_testlang = '../fallback_files/testlang.txt'
        self.assertEqual(fallback_testlang, self.validator.validate_testlang('', fallback_testlang))
        self.assertEqual('../../reverser/answers/CADET-00001.txt', self.validator.validate_testlang('../../reverser/answers/CADET-00001.txt', fallback_testlang))

    def test_validate_commit_hash(self):
        self.assertIsNotNone(self.validator.validate_linux_src_repo_path('../../../'))
        hashes = self.validator._validate_commit_hash(['d4cdbcbef'])
        self.assertEqual(['d4cdbcbef'], hashes)
        hashes = self.validator._validate_commit_hash(['d4cdbcbef', 'inavlid'])
        self.assertEqual(['d4cdbcbef'], hashes)
        hashes = self.validator._validate_commit_hash(['inavlid', 'd4cdbcbef'])
        self.assertEqual(['d4cdbcbef'], hashes)
        hashes = self.validator._validate_commit_hash(['inavlid', 'invalid', 'invalid'])
        self.assertEqual([], hashes)


if __name__ == '__main__':
    unittest.main()
