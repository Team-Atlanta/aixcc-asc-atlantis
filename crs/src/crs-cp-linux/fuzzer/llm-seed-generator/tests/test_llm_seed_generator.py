import logging
import unittest

from llm_seed_gen.llm_seed_script_generator import LLMSeedScriptGenerator

import os

from llm_seed_gen.llm.model import OaiGpt4o


class TestLLMSeedGenerator(unittest.TestCase):
    def setUp(self):
        linux_src_dir = os.getenv("LINUX_SRC")
        self.generator = LLMSeedScriptGenerator(OaiGpt4o(), linux_src_dir, '../prompts', '../logs', logging.DEBUG)
        self.test_harness_dir = os.getenv("TEST_HARNESS_DIR")

    def test_llm_seed_generator(self):
        input_args = []

        #Sample
        input_args.append(['linux_test_harness.txt', 'linux_test_harness.c', '426d4a4'])

        #CVEs
        #input_args.append(['CVE-2022-32250.txt', 'CVE-2022-32250.c', 'd762a4b84'])
        #input_args.append(['CVE-2022-32250-2.txt', 'CVE-2022-32250-2.c', 'd762a4b84'])
        #input_args.append(['CVE-2022-0995.txt', 'CVE-2022-0995.c', '05072bf'])
        #input_args.append(['CVE-2022-0995-2.txt', 'CVE-2022-0995-2.c', '05072bf'])
        #input_args.append(['CVE-2022-0185.txt', 'CVE-2022-0185.c', '6818359'])
        #input_args.append(['CVE-2021-38208.txt', 'CVE-2021-38208.c', '607143f'])
        #input_args.append(['CVE-2023-2513.txt', 'CVE-2023-2513.c', '8761564'])

        #CGCs
        #input_args.append(['CADET-00001.txt', 'CADET-00001.c', 'f5ef208'])
        #input_args.append(['CADET-00001-2.txt', 'CADET-00001-2.c', 'f5ef208'])
        #input_args.append(['CROMU-00001.txt', 'CROMU-00001.c', 'd2631c9'])
        #input_args.append(['CROMU-00003.txt', 'CROMU-00003.c', 'c93cdf1'])
        #input_args.append(['CROMU-00004.txt', 'CROMU-00004.c', 'c0a71e4'])
        #input_args.append(['CROMU-00005.txt', 'CROMU-00005.c', '4ed13ea'])
        #input_args.append(['KPRCA-00001.txt', 'KPRCA-00001.c', 'f734c8f'])
        #input_args.append(['NRFIN-00001.txt', 'NRFIN-00001.c', 'a14c6a0'])
        #input_args.append(['NRFIN-00003.txt', 'NRFIN-00003.c', '63cdbdd'])

        #CTFs
        #input_args.append(['BRAD-OBERBERG.txt', 'BRAD-OBERBERG.c', 'c899a96'])

        for input_arg in input_args:
            self.generator.create_seed_generator_scripts(f'{self.test_harness_dir}/{input_arg[1]}', f'../../reverser/answers/{input_arg[0]}', input_arg[2], '../workdir')

if __name__ == '__main__':
    unittest.main()