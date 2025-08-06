import logging
import traceback

from llm_seed_gen.llm.model import OaiGpt4o
from llm_seed_gen.llm.llm_request_processor import LLMRequestProcessor

from llm_seed_gen.utils.logger_manager import LoggerManager
from llm_seed_gen.utils import error

from llm_seed_gen.input_validator import InputValidator
from llm_seed_gen.test_harness_commit_matcher import TestHarnessCommitMatcher
from llm_seed_gen.llm_seed_script_generator import LLMSeedScriptGenerator
from llm_seed_gen.seed_generator_runner import SeedGeneratorRunner


class LLMSeedGenerator:
    def __init__(self, src_repo_path, testlang, fallback_testlang_file, test_harness, commit_analyzer_output, nblobs, prompt_dir, log_dir, workdir, output_dir, loglevel=logging.INFO):
        # Model
        self.model = OaiGpt4o()
        # Variables determined within the program. Does not need to be validated
        self.prompt_dir = prompt_dir
        self.log_dir = log_dir
        self.loglevel = loglevel
        # Create Log Manager(Later unused. Just initialize the singleton instance)
        self.logger_manager = LoggerManager(self.log_dir)
        # Create Input Validator
        self.input_validator = InputValidator()
        # Validate user provided inputs
        self.src_repo_path = self.input_validator.validate_linux_src_repo_path(src_repo_path)
        self.testlang = self.input_validator.validate_testlang(testlang, fallback_testlang_file)
        self.test_harness = self.input_validator.validate_test_harness(test_harness)
        self.commit_hash_list = self.input_validator.validate_commit_analyzer_output_file(commit_analyzer_output, self.src_repo_path)
        self.nblobs = self.input_validator.validate_nblobs(nblobs)
        self.workdir = self.input_validator.validate_workdir(workdir)
        self.output_dir = self.input_validator.validate_output_dir(output_dir)
        # Create
        self.matcher = TestHarnessCommitMatcher(self.model, self.src_repo_path, self.prompt_dir, self.log_dir, self.loglevel)
        self.script_generator = LLMSeedScriptGenerator(self.model, self.src_repo_path, self.prompt_dir, self.log_dir, self.loglevel)

    def run_one(self):
        target_commit_hash = self.matcher.match(self.test_harness, self.commit_hash_list)
        seed_generator_scripts = self.script_generator.create_seed_generator_scripts(self.test_harness, self.testlang, target_commit_hash, self.workdir)
        print(f'[Info] Script generator: {seed_generator_scripts}')
        SeedGeneratorRunner(seed_generator_scripts, self.workdir).run(self.output_dir, self.nblobs)

    def run(self, max_attempts=3):
        attempt = 0
        while attempt < max_attempts:
            try:
                self.run_one()
                print(f'[Info] Total Cost: {LLMRequestProcessor.total_cost}')
                print(f'[Info] Total Delay: {LLMRequestProcessor.total_delay}')
                return
            except Exception as e:
                attempt += 1
                error.print_exception(e, traceback.print_exc())
                error.print_error('Failed... Retry!')
        # Fatal
        error.fatal(f'Attempted {max_attempts}.')
