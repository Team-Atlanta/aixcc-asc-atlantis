import logging

from llm_seed_gen.tools.code_analyzer import CodeAnalyzer
from llm_seed_gen.tools.git_commit_handler import GitCommitHandler
from llm_seed_gen.llm.llm_request_processor import LLMRequestProcessor
from llm_seed_gen.prompt_generator import PromptGenerator
from llm_seed_gen.tools.src_handler import SourceHandler
from llm_seed_gen.utils.logger_manager import LoggerManager


class TestHarnessCommitMatcher:
    def __init__(self, model, src_path, prompt_dir, log_dir, loglevel=logging.INFO):
        # setup logger
        self.logger = LoggerManager(log_dir).get_logger(self.__class__.__name__, loglevel)

        self.model = model
        self.llm_request_processor = LLMRequestProcessor(model)
        self.git_commit_handler = GitCommitHandler(src_path)
        self.prompt_generator = PromptGenerator(src_path, prompt_dir)
        self.src_handler = SourceHandler(src_path)
        self.code_analyzer = CodeAnalyzer(src_path)

    def _send_message_to_llm(self, role, message):
        self.logger.debug(f'Sending {role} message to LLM {message}')
        response = self.llm_request_processor.process_request(role, message, self.logger)
        self.logger.debug(response)
        return response

    def match(self, test_harness, git_commit_hash_list, max_retries=10):
        print(f'match {test_harness} {git_commit_hash_list}')
        self.logger.info(f'match {test_harness} {git_commit_hash_list}')

        # initialize session to clear existing messages
        self.llm_request_processor.new_session()
        self.llm_request_processor.clear_tools()

        # send system prompt
        system_prompt = self.prompt_generator.get_test_harness_git_commit_match_system_prompt()
        self._send_message_to_llm('system', system_prompt)

        # add tools
        get_tool_functions = [self.src_handler.get_list_directory_tool, self.src_handler.get_read_file_tool, self.git_commit_handler.get_fetch_diff_tool, self.git_commit_handler.get_get_oneline_log_tool, self.code_analyzer.get_get_function_usage_tool]
        for get_tool_function in get_tool_functions:
            func, tool = get_tool_function()
            self.llm_request_processor.add_tool(func, tool)

        prompt = self.prompt_generator.get_test_harness_git_commit_match_prompt(test_harness, git_commit_hash_list)
        response = self._send_message_to_llm('user', prompt)

        retry_count = 0
        while True:
            if retry_count >= max_retries:
                return None

            start_tag = '<commit_hash>'
            end_tag = '</commit_hash>'

            start_index = response.find(start_tag)
            end_index = response.find(end_tag, start_index)
            suggested_commit = response[start_index + len(start_tag):end_index].strip()

            if start_index != -1 and end_index != -1 and suggested_commit in git_commit_hash_list:
                return suggested_commit

            error_fix_prompt = self.prompt_generator.get_test_harness_git_commit_match_fix_error_prompt(suggested_commit, git_commit_hash_list)
            response = self._send_message_to_llm('user', error_fix_prompt)
            retry_count += 1
