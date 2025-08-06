import unittest

import os

from llm_seed_gen.tools.code_analyzer import CodeAnalyzer


class TestCodeAnalyzer(unittest.TestCase):
    def setUp(self):
        self.code_analyzer = CodeAnalyzer(os.getenv("LINUX_SRC"))

    def test_CADET_00001_transmit_all(self):
        self.code_analyzer.analyze_driver_code()
        usages = self.code_analyzer.get_function_usage('cadet00001_transmit_all', 'b')
        print(usages)
        usages = self.code_analyzer.get_function_usage('cadet00001_transmit_all', 'drivers/CADET-00001/libc.c')
        print(usages)

    def test_CADET_00001_handle_main(self):
        self.code_analyzer.analyze_driver_code()
        usages = self.code_analyzer.get_function_usage('handle_main', 'b')
        print(usages)
        usages = self.code_analyzer.get_function_usage('handle_main', 'drivers/CADET-00001/service.c')
        print(usages)
        usages = self.code_analyzer.get_function_usage('handle_main', 'drivers/CROMU-00004/service.c')
        print(usages)


if __name__ == '__main__':
    unittest.main()
