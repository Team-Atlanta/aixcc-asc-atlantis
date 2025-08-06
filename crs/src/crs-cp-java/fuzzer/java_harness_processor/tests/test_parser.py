import unittest
from .test_init import *
from harness.parser import DumbJavaProjectParser
from harness.common.project import Project


harnesses = {"id_1": ("PipelineCommandUtilPovRunner", 3), 
                "id_2": ("UserRemoteCountPovRunner", 3),
                "id_3": ("ProxyConfigurationPovRunner", 5),
                "id_4": ("CoverageProcessorPovRunner", 2),
                "id_5": ("UserNameActionPovRunner", 4),
                "id_6": ("StateMonitorPovRunner", 4),
                "id_7": ("UserRemoteConfigPovRunner", 1),
                "id_8": ("AuthActionPovRunner", 4),
                "id_9": ("ApiPovRunner", 3),
                "id_10": ("SecretMessagePovRunner", 8),
                "id_11": ("AccessFilterPovRunner", 4),
                "id_12": ("ScriptPovRunner", 1),
                "id_13": ("UserRemoteCountPovRunner2", 1),
                "id_14": ("PluginUploadSyntheticPovRunner", 1),}

# non-null delimiter
non_delim_data = ["id_2"]

# container_scripts --> src/easy-test 
easy_test_data = ["id_1"]

# only one argument
single_arg_data = ["id_7", "id_12"]

# multiple arguments
core_data = ["id_3", "id_4", "id_5", "id_6", "id_8", "id_9", "id_10", "id_11"]

# complex arguments
complex_data = ["id_13", "id_14"]

class DumbParserTest(unittest.TestCase):
    def setUp(self):
        self.project = Project(CP_DIR)
        self.parser = DumbJavaProjectParser(self.project)
        
    # def test_non_delim_data(self):
    #     for id in non_delim_data:
    #         harness_info = self.parser.get_harness(id)
    #         self.assertTrue(harnesses[id][1] == len(harness_info.arguments), 
    #                         f"Expected {harnesses[id][1]} arguments, got {len(harness_info.arguments)}")
    
    def test_easy_test_data(self):
        for id in easy_test_data:
            harness_info = self.parser.get_harness(id)
            self.assertTrue(harnesses[id][1] == len(harness_info.arguments), 
                            f"Expected {harnesses[id][1]} arguments, got {len(harness_info.arguments)}")
    
    def test_single_arg_data(self):
        for id in single_arg_data:
            harness_info = self.parser.get_harness(id)
            self.assertTrue(harnesses[id][1] == len(harness_info.arguments), 
                            f"Expected {harnesses[id][1]} arguments, got {len(harness_info.arguments)}")

    def test_core_data(self):
        for id in core_data:
            harness_info = self.parser.get_harness(id)
            self.assertTrue(harnesses[id][1] == len(harness_info.arguments), 
                            f"Expected {harnesses[id][1]} arguments, got {len(harness_info.arguments)}")

