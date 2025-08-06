import os
import logging
from collections import namedtuple

from llm_seed_gen.tools.git_commit_handler import GitCommitHandler
from llm_seed_gen.llm.llm_request_processor import LLMRequestProcessor

from llm_seed_gen.prompt_generator import PromptGenerator
from llm_seed_gen.utils.python_code_validator import PythonCodeValidator
from llm_seed_gen.tools.src_handler import SourceHandler
from llm_seed_gen.utils.logger_manager import LoggerManager

SeedGeneratorScripts = namedtuple('SeedGeneratorScripts', 'test_harness_upgraded, git_commit_upgraded')


class LLMSeedScriptGenerator:
    def __init__(self, model, src_git_repo_path, prompt_dir, log_dir, loglevel=logging.INFO):
        # Setup logger
        self.logger = LoggerManager(log_dir).get_logger(self.__class__.__name__, loglevel)

        #Ensure Absolute Path
        src_git_repo_path = os.path.abspath(src_git_repo_path)
        prompt_dir = os.path.abspath(prompt_dir)
        log_dir = os.path.abspath(log_dir)

        self.model = model
        self.llm_request_processor = LLMRequestProcessor(model)
        self.git_commit_handler = GitCommitHandler(src_git_repo_path)
        self.prompt_generator = PromptGenerator(src_git_repo_path, prompt_dir)
        self.python_validator = PythonCodeValidator()
        self.src_handler = SourceHandler(src_git_repo_path)

        self.src_git_repo_path = src_git_repo_path

    def _fetch_diff(self, commit_hash):
        diff = self.git_commit_handler.fetch_diff(commit_hash)
        self.logger.debug(f'Diff of {commit_hash}')
        self.logger.debug(diff)
        return diff

    def _send_message_to_llm(self, role, message):
        self.logger.debug(f'Sending {role} message to LLM {message}')
        response = self.llm_request_processor.process_request(role, message, self.logger)
        self.logger.debug(response)
        return response

    def _create_directory_if_does_not_exists(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except:
            return

    def _send_system_prompt(self):
        system_prompt = self.prompt_generator.get_system_prompt()
        self._send_message_to_llm('system', system_prompt)

    def _request_seed_generator(self, prompt, filename, max_retries=10):
        response = self._send_message_to_llm('user', prompt)

        retry_count = 0
        while True:
            if retry_count >= max_retries:
                return False

            start_index = response.find('#START_CODE')
            error = ''
            if start_index != -1:
                end_index = response.find('#END_CODE', start_index) + len('#END_CODE')

                python_code = response[start_index:end_index]
                error = self.python_validator.run_code(filename, python_code)

                if error is None:
                    return True
            else:
                error = 'No Python code was found enclosed between #START_CODE and #END_CODE. Please provide Python code.'

            self.logger.debug(f'The python code had an error')
            self.logger.debug(error)
            debug_prompt = self.prompt_generator.get_debug_request_prompt(error)
            response = self._send_message_to_llm('user', debug_prompt)
            retry_count += 1

    def _create_generator_using_test_harness(self, workdir, test_harness, src_repo_path, commit_hash):
        filename = f'{workdir}/{commit_hash}_test_harness_generated.py'
        test_harness_prompt = self.prompt_generator.get_test_harness_prompt(test_harness, src_repo_path)
        success = self._request_seed_generator(test_harness_prompt, filename)
        return filename if success else None

    def _upgrade_generator_using_git_commit_diff(self, workdir, commit_hash):
        filename = f'{workdir}/{commit_hash}_git_diff_upgraded.py'
        git_diff = self._fetch_diff(commit_hash)
        git_diff_prompt = self.prompt_generator.get_git_diff_prompt(git_diff)
        success = self._request_seed_generator(git_diff_prompt, filename)
        return filename if success else None

    def create_seed_generator_scripts(self, test_harness, commit_hash, workdir):
        print(f'create_seed_generator_scripts {test_harness} {commit_hash}')
        self.logger.info(f'create_seed_generator_scripts {test_harness} {commit_hash}')

        # initialize session to clear existing messages
        self.llm_request_processor.new_session()
        self.llm_request_processor.clear_tools()

        # send system prompt containing guideline
        self._send_system_prompt()

        # add tools
        get_tool_functions = [self.src_handler.get_list_directory_tool, self.src_handler.get_read_file_tool]
        for get_tool_function in get_tool_functions:
            func, tool = get_tool_function()
            self.llm_request_processor.add_tool(func, tool)

        # upgrade seed generator using test harness
        test_harness_upgraded = self._create_generator_using_test_harness(workdir, test_harness, self.src_git_repo_path, commit_hash)
        # upgrade seed generator using git diff
        if commit_hash is not None:
            git_commit_upgraded = self._upgrade_generator_using_git_commit_diff(workdir, commit_hash)
            return SeedGeneratorScripts(test_harness_upgraded, git_commit_upgraded)
        else:
            return SeedGeneratorScripts(test_harness_upgraded, None)
