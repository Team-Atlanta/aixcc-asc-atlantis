import os
import argparse

from bench_init import *
from testbench import TestBench
from harness.utils.builder import CPBuilder
from harness.generator import LLMJazzerHarnessGenerator

from data import *


argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=5)
args = argparse.parse_args()

num_of_exec = args.num


class JazzerHarnessGenerateBench(TestBench):
    def __init__(self, harness_file: str, tmp_dir=TMP_DIR):
        self.file_path = harness_file
        self.tmp_dir = tmp_dir
        
        self.builder = CPBuilder(CP_DIR) 
        with open(self.file_path, "r") as f:
            self.code = f.read()
    
    def setUp(self):
        if os.path.exists(self.tmp_dir):
            os.system(f'rm -rf "{self.tmp_dir}"')
        os.mkdir(self.tmp_dir)
        
        self.builder.javac(self.file_path, dest_dir=self.tmp_dir)
    
    def tearDown(self):
        pass
    
    def batch(self):
        file_path = self.file_path
        print(f"-----------------------------------------------------")
        print(f"Test harness: {file_path}")
        print(f"-----------------------------------------------------")
        
        class_name = f'{os.path.basename(file_path).split(".")[0]}_Fuzz'
        
        batch_tmp = os.path.join(self.tmp_dir, str(self.name))
        os.mkdir(batch_tmp)
        output_file = os.path.join(batch_tmp, f'{class_name}.java')
        
        generator = LLMJazzerHarnessGenerator(temperature=0.3)
        generator.class_name = class_name
        generator.code = self.code 
        code = generator.generate()
        
        with open(output_file, "w") as f:
            f.write(code)
        
        res = build_test(self.builder, output_file)
            
        if res:
            return True
        return False


def bench_jazzer_harness(n):
    res = {}
    for id in test_harnesses:
        harness_file = test_harnesses[id]["source"]
        tmp_dir = os.path.join(TMP_DIR, id)
        
        res[id] = JazzerHarnessGenerateBench(harness_file, tmp_dir=tmp_dir).bench(n)

    return res


def main():
    jazzer_results = bench_jazzer_harness(num_of_exec)
    print("----------------------------------------------------------------------")
    print("LLM-based Jazzer harness results")
    print("----------------------------------------------------------------------")
    for id in jazzer_results:
        print(f"{id}: {jazzer_results[id].count(True) } / {num_of_exec} build success rate")
    

if __name__ == "__main__":
    main()