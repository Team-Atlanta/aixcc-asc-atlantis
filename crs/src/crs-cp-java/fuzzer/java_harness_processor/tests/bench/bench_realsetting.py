import argparse
from pathlib import Path

from bench_init import *
from harness.processor import llm_processing
from harness.utils.builder import CPBuilder
from data import test_harnesses


argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=5)
args = argparse.parse_args()

num_of_exec = args.num

class LLMProcessingBench(TestBench):
    def __init__(self, args, tmp_dir = TMP_DIR) -> None:
        super().__init__()
        self.tmp_dir = tmp_dir
        self.args = args
        
        self.class_name = os.path.basename(test_harnesses[self.args.harnessid]["source"]).split(".")[0]
        self.JARS = []
        
    def setUp(self):
        if os.path.exists(self.tmp_dir):
            os.system(f'rm -rf {self.tmp_dir}')
        os.mkdir(self.tmp_dir)
        print("Setting up the test bench")
        file_path = test_harnesses[self.args.harnessid]["source"]
        harness_jars = Path( f'{CP_DIR}/out/harnesses/{os.path.basename(os.path.dirname(file_path))}' )
        self.JARS = [str(jar) for jar in harness_jars.rglob("*.jar")]
            
        
    def batch(self):
        output_dir = os.path.join(self.tmp_dir, self.name)
        
        self.args.output_dir = output_dir
        llm_processing(self.args)
        
        try:
            builder = CPBuilder(CP_DIR)
            for jar in self.JARS:
                builder.add_classpath(jar)
                
            if self.args.format == 'protobuf':
                os.system(f'cp {output_dir}/{self.class_name}_Fuzz.proto {output_dir}/HarnessInput.proto')
                os.system(f'protobuf/protoc -I {output_dir} --java_out={output_dir} {output_dir}/HarnessInput.proto')
        
                builder.add_classpath(f"protobuf/protobuf-java-3.25.3.jar")
                builder.javac(os.path.join(output_dir, f'{self.class_name}_Fuzz.java'))
                builder.javac(os.path.join(output_dir, f'{self.class_name}_BlobGenerator.java'))
            elif self.args.format == 'jazzer':
                builder.javac(os.path.join(output_dir, f'{self.class_name}_JazzerFuzz.java'))
                builder.javac(os.path.join(output_dir, f'{self.class_name}_JazzerBlobGenerator.java'))
            else:
                raise Exception("Invalid format")
        except:
            return False
        
        return True


def main():
    
    jazzer_res = {}
    protobuf_res = {}
    print("-------------------------------")
    print("Jazzer harness generate")
    print("-------------------------------")
    for id in test_harnesses:
        print(f"jazzer - {id}")
        args.project = CP_DIR
        args.harnessid = id
        args.format = 'jazzer'
        args.include_origin = True
        bench = LLMProcessingBench(args, f'{TMP_DIR}/{id}')
        jazzer_res[id] = bench.bench(num_of_exec)

    print("-------------------------------")
    print("Protobuf harness generate")
    print("-------------------------------")
    for id in test_harnesses:
        print(f"protobuf - {id}")
        args.project = CP_DIR
        args.harnessid = id
        args.format = 'protobuf'
        args.include_origin = True
        bench = LLMProcessingBench(args, f'{TMP_DIR}/{id}')
        protobuf_res[id] = bench.bench(num_of_exec)
    
    print('----------- Jazzer --------------')
    for id in jazzer_res:
        print(f"{id}: {jazzer_res[id].count(True)} / {num_of_exec} success rate")
    print('----------- Protobuf --------------')
    for id in protobuf_res:
        print(f"{id}: {protobuf_res[id].count(True)} / {num_of_exec} success rate")

if __name__ == "__main__":
    main()
