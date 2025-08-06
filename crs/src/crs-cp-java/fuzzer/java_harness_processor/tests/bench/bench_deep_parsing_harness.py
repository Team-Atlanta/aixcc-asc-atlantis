import os
import re
import argparse

from bench_init import *

from harness.parser import LLMDeepJavaProjectParser
from harness.common.project import Project
from harness.java_static import LLMJavaCodeEditor
from harness.utils.logger import Log
from harness.utils.builder import CPBuilder
from data import *

argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=5)
args = argparse.parse_args()

num_of_exec = args.num



class LLMDeepParseHarnessTest(TestBench):
    def __init__(self, file_path, tmp_dir = TMP_DIR) -> None:
        super().__init__()
        self.file_path = file_path
        self.tmp_dir = tmp_dir
        
        self.project = Project(CP_DIR)
        self.builder = CPBuilder(CP_DIR)
        with open(self.file_path, 'r') as f:
            self.code = f.read()
    
    def setUp(self):
        if os.path.exists(self.tmp_dir):
            os.system(f"rm -rf {self.tmp_dir}")
        os.mkdir(self.tmp_dir)
    
    def batch(self):
        tmp_dir = os.path.join(self.tmp_dir, self.name)
        os.mkdir(tmp_dir)

        package_name = re.findall(r'package\s+(.*?);', self.code)
        class_name = os.path.basename(self.file_path).replace(".java", "")
        fuzz_class_name = f'{class_name}_Fuzz'
        
        
        parser = LLMDeepJavaProjectParser(self.project)
        harness = parser.get_harness(self.file_path)
        code = harness.source_code
        
        editor = LLMJavaCodeEditor(code)
        editor.change_class_name(class_name, fuzz_class_name)
        editor.change_package(package_name)
        editor.save(f'{tmp_dir}/{fuzz_class_name}.java')
        
        try:
            self.builder.javac(self.file_path, dest_dir=tmp_dir)
            self.builder.javac(f'{tmp_dir}/{fuzz_class_name}.java', dest_dir=tmp_dir)
        except Exception as e:
            Log.e(f'Failed to compile: {e}')
            return False
        
        return True
        
        
def bench_all_harness(n=5):
    res = {}
    for id in test_harnesses:
        benchtest = LLMDeepParseHarnessTest(test_harnesses[id]["source"], os.path.join(TMP_DIR, id))
        res[id] = benchtest.bench(n)
    
    for id in res:
        print(f"{id}: {res[id].count(True)} / {n} success rate")


def main():
    bench_all_harness(num_of_exec)
    


if __name__ == "__main__":
    main()