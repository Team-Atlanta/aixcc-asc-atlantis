import os
import re
import argparse

from bench_init import *

from harness.utils.builder import CPBuilder
from harness.common.project import Project
from harness.parser.repository import JavaRepository
from harness.llm import ChatBot

import gen
from llm_parser import LLMJavaStaticParser

from data import *


argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=5)
args = argparse.parse_args()

num_of_exec = args.num

class LLMParserTest(TestBench):
    def __init__(self, file_path) -> None:
        super().__init__()
        self.file_path = file_path
        
        self.invocation_code = {}
        self.dependencies = {}
        
    def is_visited(self, file_path: str, class_name: str, method_name: str):
        if file_path in self.invocation_code:
            if class_name in self.invocation_code[file_path]:
                if method_name in self.invocation_code[file_path][class_name]:
                    return True
        return False
    
    def set_visited(self, file_path: str, class_name: str, method_name: str):
        if file_path not in self.invocation_code:
            self.invocation_code[file_path] = {}
            self.dependencies[file_path] = {}
        
        if class_name not in self.invocation_code[file_path]:
            self.invocation_code[file_path][class_name] = {}
            self.dependencies[file_path][class_name] = {}
        
        self.invocation_code[file_path][class_name][method_name] = None
        self.dependencies[file_path][class_name][method_name] = []
    
    def _has_primitive_argument(self, arguments: str, allowed_types: list[str]):
        arg_list = arguments.split(",")
        for arg in arg_list:
            arg_list = arg.strip().split(" ")
            if len(arg_list) != 2:
                continue
            
            if arg_list[0] in allowed_types:
                return True
            
        return False
    
    def _extract_argument(self, arguments: str, target_types: list[str]):
        args = []
        splited_args = arguments.split(",")
        for raw_args in splited_args:
            raw_args = raw_args.strip()
            re_arg = re.findall(r'(?:(.*)\s+)?([^\s]+)\s+(\w+)', raw_args)
            if len(re_arg) == 0:
                continue
            if re_arg[0][-2] in target_types:
                args.append(f'{re_arg[0][-2]} {re_arg[0][-1]}')
            
        return args
    
    def _get_dependencies(self, code: str, class_name: str, method_name: str):
        dependencies = []
        
        invocations = self.parser.get_invocations(code, class_name, method_name)
        for invocation in invocations:
            parsed_invocation = re.findall(r'(\w+)\.(\w+)\((.*?)\)', invocation)
            if len(parsed_invocation) == 1:
                classname, methodname, arguments = parsed_invocation[0]
                
                for target_file in self.repository.find_file_by_name(f'{classname}.java'):
                    dependencies.append((target_file, classname, methodname, arguments))
            else: 
                print("Not typical java method : ", invocation)
        
        return dependencies

    
    def _remove_comments(self, code: str):
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def visit(self, file_path: str, class_name: str, method_name: str, intersting_args: list, depth: int = 0, max_depth: int = 3):
        if depth > max_depth:
            return
        
        if self.is_visited(file_path, class_name, method_name):
            return
        
        print("Visiting: ", file_path, class_name, method_name, intersting_args)
        self.set_visited(file_path, class_name, method_name)
        
        with open(file_path, "r") as f:
            code = f.read()
        
        code = self._remove_comments(code)
        
        dependencies = self._get_dependencies(code, class_name, method_name)
        self.dependencies[file_path][class_name][method_name] = dependencies
        
        for child_file, child_class_name, child_method_name, arguments in dependencies:
            child_args = self._extract_argument(arguments, ["String", "int", "byte[]", "boolean"])
            print(f"<<Dependency: {child_file}, {child_class_name}.{child_method_name}({child_args})>>")
            if len(child_args) != 0:
                self.visit(child_file, child_class_name, child_method_name, child_args, depth+1, max_depth)
        
        dependencies_code = []
        for child_file, child_class_name, child_method_name, arguments in dependencies:
            if not self.is_visited(child_file, child_class_name, child_method_name):
                continue 
            
            sample_code = self.invocation_code[child_file][child_class_name][child_method_name]
            if sample_code is not None:
                dependencies_code.append((child_class_name, child_method_name, sample_code))
        
        chatbot = ChatBot(temperature=0.0)
        invocation_code = gen.generate_example_body(chatbot, code, class_name, method_name, intersting_args, dependencies_code)
        self.invocation_code[file_path][class_name][method_name] = invocation_code
        
        # print("---------Visited: ", file_path, class_name, method_name)
        # print(invocation_code)
        return
        

        
    def batch(self):
        self.cp_dir = CP_DIR
        self.project = Project(self.cp_dir)
        self.repository = JavaRepository(self.cp_dir)
        # exclude external source directories
        for source_dir in self._project.cp_sources:
            self._repository.add_exclude(os.path.join('src', source_dir))
            
        self.parser = LLMJavaStaticParser()
        class_name = os.path.basename(self.file_path).replace(".java", "")
        self.visit(self.file_path, class_name, "fuzzerTestOneInput", ["byte[] data"])
        
        harness_code = self.invocation_code[self.file_path][class_name]["fuzzerTestOneInput"]
        basename = os.path.basename(self.file_path)
        print("Visit results: ")
        with open("./.tmp/" + basename, "w") as f:
            f.write(harness_code)
        print("./.tmp/" + basename)
        
        
        return 1


def bench_all_harness(n=5): 
    if os.path.exists(TMP_DIR):
        os.system(f"rm -rf {TMP_DIR}")
    os.mkdir(TMP_DIR)
    
    res = {}
    for id in byte_harnesses:
        benchtest = LLMParserTest(byte_harnesses[id])
        res[id] = benchtest.bench(n)

    os.system(f"rm -rf {TMP_DIR}")
    
    for id in res:
        print(f"{id}: {res[id]} / {n} success rate")


def main():
    # bench_all_harness(num_of_exec)
    
    for id in byte_harnesses:
        benchtest = LLMParserTest(byte_harnesses[id])
        benchtest.bench(1)


if __name__ == "__main__":
    main()