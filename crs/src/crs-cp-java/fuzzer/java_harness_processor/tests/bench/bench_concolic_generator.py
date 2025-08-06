import os
import re
import argparse

from bench_init import *

from harness.llm import ChatBot
from harness.common.project import Project
from harness.utils.logger import Log
from harness.utils.builder import CPBuilder
from harness.java_static.code_editor import LLMJavaCodeEditor
from harness.generator import LLMConcolicHarnessGenerator
from harness.common.harness import Harness
from data import *


argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=5)
args = argparse.parse_args()

num_of_exec = args.num

class ConcolicGenerateTest(TestBench):
    def __init__(self, file_path, tmp_dir = TMP_DIR) -> None:
        super().__init__()
        self.file_path = file_path
        self.tmp_dir = tmp_dir
        
        self.project = Project(CP_DIR)
        self.builder = CPBuilder(CP_DIR)
        base = os.path.dirname(file_path)
        number = os.path.basename(base)
        self.builder.add_classpath(f'{CP_DIR}/out/harnesses/{number}/*')
        self.builder.add_classpath(f"swat/BinaryArgumentLoader.jar")
        with open(self.file_path, 'r') as f:
            self.code = f.read()
    
    def setUp(self):
        if os.path.exists(self.tmp_dir):
            os.system(f"rm -rf {self.tmp_dir}")
        os.mkdir(self.tmp_dir)
    
    def batch(self):
        tmp_dir = self.tmp_dir
        tmp_dir = os.path.join(self.tmp_dir, self.name)
        os.mkdir(tmp_dir)

        class_name = os.path.basename(self.file_path).replace(".java", "")
        fuzz_class_name = f'{class_name}_Concolic'
        generator = LLMConcolicHarnessGenerator()
        generator.class_name = fuzz_class_name
        generator.code = self.code
        code = generator.generate()
        with open(f'{tmp_dir}/{fuzz_class_name}.java', 'w') as f:
            f.write(code)
        print(f'Generated Concolic Harness: {tmp_dir}/{fuzz_class_name}.java')
        
        # generator = LLMJazzerHarnessGenerator(temperature=0.2)
        # generator.class_name = class_name
        # generator.code = self.code
        # fuzz_harness_code = generator.generate()
        
        # # Create Blob Generator File
        # converter = LocalBlobConverter()
        # converter.file_path = '/work/tmp_blob'
        # converter.target_class = class_name
        # converter.from_class_name = class_name
        # converter.to_class_name = f'{class_name}_BlobGenerator'
        # converter.code = fuzz_harness_code
        # blob_code = converter.generate()
        # with open(f'{tmp_dir}/{class_name}_BlobGenerator.java', 'w') as f:
        #     f.write(blob_code)
        # print(f'Generated Blob Harness: {tmp_dir}/{class_name}_BlobGenerator.java')
        
        try:
            self.builder.javac(f'{tmp_dir}/{fuzz_class_name}.java', dest_dir=tmp_dir)
            return True
        except Exception as e:
            Log.e(f'Failed to compile: {e}')
            return False


    def tearDown(self):
        pass
        

def main():
    print("Base API URL:", BASE_URL)
    print("CP_DIR:", CP_DIR)
    print("TMP_DIR:", TMP_DIR)
    
    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)
    
    res = {}
    for id in test_harnesses:
        bench = ConcolicGenerateTest(test_harnesses[id]["source"], os.path.join(TMP_DIR, id))
        res[id] = bench.bench(num_of_exec)
        
    for id in res:
        print(f"{id}: {res[id].count(True)} / {num_of_exec} success rate")
        
        
if __name__ == "__main__":
    main()
