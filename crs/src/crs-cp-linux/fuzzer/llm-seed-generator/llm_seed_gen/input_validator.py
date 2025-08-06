from git import Repo

import os

from llm_seed_gen.tools.git_commit_handler import GitCommitHandler

from llm_seed_gen.utils import error


class InputValidator:
    def __init__(self):
        self.repo = None

    def validate_linux_src_repo_path(self, linux_src_repo_path):
        try:
            self.repo = Repo(linux_src_repo_path)
            return linux_src_repo_path
        except Exception as e:
            error.fatal(f'The linux src repo path {linux_src_repo_path} is not a valid git repository. Exception: {type(e).__name__}({e})')

    def _validate_readable_file(self, file):
        try:
            if not os.path.isfile(file):
                error.print_error(f'The file {file} is not a file.')
                return None
            if not os.access(file, os.R_OK):
                error.print_error(f'The file {file} is not readable.')
                return None
            return file
        except Exception as e:
            error.print_error(f'An error occured: {type(e).__name__}({e})')
            return None

    def _validate_testlang_content(self, testlang):
        # Todo : How to check whether testlang content is valid?
        return testlang

    def validate_testlang(self, testlang, fallback_testlang_file):
        validated_testlang = self._validate_testlang_content(testlang)
        if self._validate_readable_file(testlang) is None or validated_testlang is None:
            error.print_error(f'testlang {testlang} is not a valid testlang. Using fallback testlang.')

            if self._validate_readable_file(fallback_testlang_file) is None:
                error.fatal(f'Backup testlang file {fallback_testlang_file} is invalid')
            return fallback_testlang_file
        return validated_testlang

    def validate_test_harness(self, test_harness):
        if self._validate_readable_file(test_harness) is None:
            error.fatal(f'test harness {test_harness} is not a valid test harness.')
        return test_harness

    def _commit_exists(self, hash):
        try:
            self.repo.commit(hash)
            return True
        except Exception as e:
            return False

    def _validate_commit_hash(self, commit_hash_list):
        valid_commit_hash_list = []

        for hash in commit_hash_list:
            if self._commit_exists(hash.strip()):
                valid_commit_hash_list.append(hash.strip())

        return valid_commit_hash_list if valid_commit_hash_list else []

    def _backup_commit_hash_list(self, src_repo_path):
        error.print_error('Commit hash list is empty. Using all commit hashes from the repository.')
        commit_hash_list = GitCommitHandler(src_repo_path).get_all_commit_hashes()

        if not commit_hash_list:
            error.fatal(f'No commits to work with: {commit_hash_list}')

        return commit_hash_list

    def validate_commit_analyzer_output_file(self, output_file, src_repo_path):
        try:
            commit_hash_list = []

            with open(output_file, 'r') as f:
                lines = f.readlines()

                for line in lines:
                    tokens = line.split(',')
                    commit_hash_list.append(tokens[1].strip())

            commit_hash_list = self._validate_commit_hash(commit_hash_list)

            if commit_hash_list:
                return commit_hash_list
            # Use entire commit hash when commit analyzer result is invalid
            return self._backup_commit_hash_list(src_repo_path)

        except Exception as e:
            # Use entire commit hash when commit analyzer result is invalid
            return self._backup_commit_hash_list(src_repo_path)

    def _create_directory_if_does_not_exists(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except:
            return

    def _validate_dir(self, directory):
        try:
            self._create_directory_if_does_not_exists(directory)
            if os.path.isdir(directory):
                return directory
            return None
        except:
            return None

    def validate_workdir(self, workdir):
        # Validate workdir
        workdir = self._validate_dir(workdir)
        if workdir is None:
            error.fatal(f'workdir {workdir} is not valid')
        return workdir

    def validate_output_dir(self, output_dir):
        # Validate workdir
        output_dir = self._validate_dir(output_dir)
        if output_dir is None:
            error.fatal(f'output_dir {output_dir} is not valid')
        return output_dir

    def validate_nblobs(self, nblobs):
        try:
            n = int(nblobs)
            return n
        except:
            default_val = 5
            error.print_error(f'nblobs {nblobs} is not a number. Using default value of {default_val}')
            return default_val
