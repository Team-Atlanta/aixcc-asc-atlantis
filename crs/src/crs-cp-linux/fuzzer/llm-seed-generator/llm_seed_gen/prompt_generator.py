import os
import glob


class PromptGenerator:
    def __init__(self, src_path, prompt_dir):
        self.src_path = src_path

        self.prompts = {}
        self.prompt_wildcard_pattern = '*.prompt'
        self.prompt_dir = prompt_dir

        self._init_prompts()

    def _init_prompts(self):
        for file in glob.glob(os.path.join(self.prompt_dir, self.prompt_wildcard_pattern)):
            with open(file, 'r') as f:
                content = f.read()
                prompt_filename = os.path.basename(file)
                self.prompts[prompt_filename] = content

    def get_system_prompt(self):
        return self.prompts['system.prompt']

    def get_testlang_explanation_prompt(self):
        return self.prompts['testlang_explanation.prompt']

    def get_testlang_prompt(self, testlang_file):
        with open(testlang_file, 'r') as f:
            testlang = f.read()

            prompt = self.prompts['testlang.prompt']
            prompt = prompt.replace('BLOBNAME', os.path.basename(testlang_file))
            prompt = prompt.replace('[INSERT TESTLANG HERE]', testlang)

            return prompt

    def get_debug_request_prompt(self, error):
        prompt = self.prompts['debug_request.prompt']
        prompt = prompt.replace('[INSERT ERROR MESSAGE HERE]', error)
        return prompt

    def get_test_harness_prompt(self, test_harness_file):
        with open(test_harness_file, 'r') as f:
            test_harness = f.read()

            prompt = self.prompts['test_harness.prompt']
            prompt = prompt.replace('[INSERT TEST HARNESS HERE]', test_harness)

            return prompt

    def get_git_diff_prompt(self, git_diff):
        prompt = self.prompts['git_diff.prompt']
        prompt = prompt.replace('[INSERT GIT DIFF HERE]', git_diff)
        return prompt

    def get_test_harness_git_commit_match_system_prompt(self):
        return self.prompts['test_harness_git_commit_match_system.prompt']

    def get_test_harness_git_commit_match_prompt(self, test_harness_file, git_commit_hash_list):
        with open(test_harness_file, 'r') as f:
            test_harness = f.read()

            prompt = self.prompts['test_harness_git_commit_match.prompt']
            prompt = prompt.replace('[INSERT TEST HARNESS HERE]', test_harness)
            prompt = prompt.replace('[INSERT GIT COMMIT HASH LIST HERE]', ', '.join(git_commit_hash_list))

            return prompt

    def get_test_harness_git_commit_match_fix_error_prompt(self, suggested_commit, git_commit_hash_list):
        prompt = self.prompts['test_harness_git_commit_match_fix_error.prompt']
        prompt = prompt.replace('[INSERT SUGGESTED GIT COMMIT HASH HERE]', suggested_commit)
        prompt = prompt.replace('[INSERT GIT COMMIT HASH LIST HERE]', ', '.join(git_commit_hash_list))

        return prompt
