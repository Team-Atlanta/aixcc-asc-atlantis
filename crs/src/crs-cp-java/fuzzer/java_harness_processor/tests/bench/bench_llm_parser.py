import argparse

from bench_init import *
from harness.common.project import Project
from harness.parser import LLMHarnessParser


argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=5)
args = argparse.parse_args()

num_of_exec = args.num

data = {
    "id_1": ("PipelineCommandUtilPovRunner", "fuzzerTestOneInput"),
    "id_2": ("UserRemoteCountPovRunner", "fuzzerTestOneInput"),
    "id_3": ("ProxyConfigurationPovRunner", "fuzzerTestOneInput"),
    "id_4": ("CoverageProcessorPovRunner", "fuzzerTestOneInput"),
    "id_5": ("UserNameActionPovRunner", "fuzzerTestOneInput"),
    "id_6": ("StateMonitorPovRunner", "fuzzerTestOneInput"),
    "id_7": ("UserRemoteConfigPovRunner", "fuzzerTestOneInput"),
    "id_8": ("AuthActionPovRunner", "fuzzerTestOneInput"),
    "id_9": ("ApiPovRunner", "fuzzerTestOneInput"),
    "id_10": ("SecretMessagePovRunner", "fuzzerTestOneInput"),
    "id_11": ("AccessFilterPovRunner", "fuzzerTestOneInput"),
    "id_12": ("ScriptPovRunner", "fuzzerTestOneInput"),
    "id_13": ("UserRemoteCountPovRunner2", "fuzzerTestOneInput"),
    "id_14": ("PluginUploadSyntheticPovRunner", "fuzzerTestOneInput")       
}

class LLMParserTest(TestBench):
    def __init__(self, id) -> None:
        super().__init__()
        self.id = id

    def setUp(self):
        project = Project(CP_DIR)
        self.parser = LLMHarnessParser(project)
        
    def batch(self):
        harness = self.parser.get_harness(self.id)
        
        if harness is not None and \
            harness.target_class == data[self.id][0] and \
            harness.target_method == data[self.id][1]:
            return True
        
        return False


def bench_all_harness(n=5): 
    res = {}
    
    for id in data:
        benchtest = LLMParserTest(id)
        res[id] = benchtest.bench(n)
        
    for id in res:
        print(f"{id}: {res[id].count(True)} / {n} success rate")

def main():
    bench_all_harness(num_of_exec)

if __name__ == "__main__":
    main()