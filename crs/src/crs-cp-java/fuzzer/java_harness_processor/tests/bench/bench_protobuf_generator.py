import os
import shutil
import argparse

from bench_init import *
from testbench import TestBench
from harness.utils.builder import CPBuilder
from harness.generator import LLMProtobufHarnessGenerator, ProtoBufMultiTypeGenerator

from data import *

argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=5)
args = argparse.parse_args()

num_of_exec = args.num


def build_test(builder, java_file):
    try:
        builder.javac(java_file)
        print(f'Success to compile: {java_file}')
        return True
    except:
        print(f'Failed to compile: {java_file}')
        return False



class LLMProtobufHarnessGeneratorBench(TestBench):
    def __init__(self, file_path, tmp_dir=TMP_DIR):
        self.tmp_dir = tmp_dir
        self.file_path = file_path
        with open(self.file_path, "r") as f:
            self.code = f.read()
            
    def setUp(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        os.mkdir(self.tmp_dir)

        builder = CPBuilder(CP_DIR)
        try:
            builder.javac(self.file_path, dest_dir=f'{self.tmp_dir}/target_classes')
        except:
            print(f'Prebuilt failed: {self.file_path}')
        
        
    def tearDown(self):
        pass
    
    def batch(self):
        output_dir = os.path.join(self.tmp_dir, self.name)
        shutil.copytree(f'{self.tmp_dir}/target_classes', f'{output_dir}')
        
        target_class_name = os.path.basename(self.file_path).split(".")[0]
        class_name = f'{target_class_name}_Fuzz'
        output_file = f'{output_dir}/{class_name}.java'
        output_proto_file = f'{output_dir}/HarnessInput.proto'
        
        generator = LLMProtobufHarnessGenerator()
        generator.jazzer_code = self.code
        generator.target_class_name = target_class_name
        generator.main_class_name = class_name
        harness_code = generator.generate()
        
        proto_generator = ProtoBufMultiTypeGenerator()
        proto_generator.argument_types = generator.arguments
        protobuf_code = proto_generator.generate()
        
        with open(output_file, "w") as f:
            f.write(harness_code)
        
        with open(output_proto_file, "w") as f:
            f.write(protobuf_code)
            
        os.system(f'protobuf/protoc -I {output_dir} --java_out={output_dir} {output_proto_file}')
        
        builder = CPBuilder(CP_DIR)
        builder.add_classpath(f"protobuf/protobuf-java-3.25.3.jar")
        
        try:
            builder.javac(output_file, dest_dir=output_dir)
            return True
        except:
            return False

def bench_probobuf_harness(n):
    res = {}
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.mkdir(TMP_DIR)
    for id in test_harnesses:
        tmp_dir = os.path.join(TMP_DIR, id)
        res[id] = LLMProtobufHarnessGeneratorBench(test_harnesses[id]["source"], tmp_dir).bench(n)
    
    return res


def main():
    probobuf_results = bench_probobuf_harness(num_of_exec)
    print("----------------------------------------------------------------------")
    print("LLM-based Protobuf harness results")
    print("----------------------------------------------------------------------")
    for id in probobuf_results:
        print(f"{id}: {probobuf_results[id].count(True) } / {num_of_exec} build success rate")
    
    
if __name__ == "__main__":
    main()
    