import os
import re
import javalang

from .javaobj import JavaCode
from .repository import JavaRepository
from ..common.harness import Harness
from ..common.project import Project
from ..utils.logger import Log

# Exception classes 
class ParserException(Exception):
    pass
class InvalidHarnessException(ParserException):
    pass
class ArgumentLengthNotDefinedException(ParserException):
    pass
    
TARGET_METHOD = 'fuzzerTestOneInput'

class DumbJavaProjectParser(object):
    def __init__(self, project: Project):
        self._project = project 
        self._repository = JavaRepository(self._project.project_path)
        
        # exclude external source directories
        for source_dir in self._project.cp_sources:
            self._repository.add_exclude(os.path.join('src', source_dir))
            
        self._java_code = {}
        self.harnesses = {}
        self._harness_source_paths = {}
        for id in self._project.harnesses:
            project_filepath = self._repository.path(project.harnesses[id]['source'])
            self._harness_source_paths[id] = project_filepath
    
    def get_harnesses(self) -> dict:
        self._parse_harnesses()
        return self.harnesses
        
    def get_harness(self, id) -> Harness:
        self._parse_harness(id)
        return self.harnesses[id]

    def _parse_harnesses(self):
        self.harnesses = {}
        for id in self._harness_source_paths:
            self._parse_harness(id)
            
    def _parse_harness(self, id):
        harness_path = self._harness_source_paths[id]
        harness_code = self._parse_java_file(harness_path)
        
        # find target file and argc
        try:
            _, argc = self._lookup_argument(harness_code)
        except InvalidHarnessException as e:
            Log.d(f'invalid harness: {id} - use default argc: 1')
            argc = 1

        harness = Harness()
        harness.file_path = harness_path
        harness.source_code = harness_code.source_code
        
        # find class have fuzzerTestOneInput in harness_code.classes
        for cls_name in harness_code.classes:
            if TARGET_METHOD in harness_code.classes[cls_name].methods:
                target_class = harness_code.classes[cls_name].name
                break

        harness.target_package = harness_code.package
        harness.target_class = target_class
        harness.target_method = TARGET_METHOD
        
        for i in range(argc):
            harness.add_argument({'name': f'arg{i + 1}'})
        
        self.harnesses[id] = harness
        
            
    def _parse_java_file(self, filepath) -> JavaCode:
        if filepath in self._java_code:
            return self._java_code[filepath]
        
        self._java_code[filepath] = JavaCode.from_file(filepath)
        
        syms = set()
        for cls_name in self._java_code[filepath].classes:
            methods = self._java_code[filepath].classes[cls_name].methods
            for method_name in methods:
                syms = syms.union(CodeSerializer().get_symbols(methods[method_name].obj))
        
        dependencies = []
        for sym in syms:
            dependencies += self._repository.find_file_by_name(f'{sym}.java')
        
        dependencies = list(set(dependencies))
        
        for dep_filepath in dependencies:
            if dep_filepath not in self._java_code:
                self._java_code[filepath].children.append(self._parse_java_file(dep_filepath))
    
        return self._java_code[filepath]
    
    def _lookup_argument(self, java_code: JavaCode) -> set:
        # get all arguments from the source code
        target_with_argc = self._get_all_argc(java_code)
                    
        # Assume that there is only one java file
        if len(target_with_argc) != 1:
            err_msg = f'harness pattern is abnormal: {java_code.filepath}\n'
            err_msg += f'argc: {len(target_with_argc)} - {target_with_argc}'
            Log.d(err_msg)
            # return None
        
        # if no arguments, do dumb fuzzing. 
        if len(target_with_argc) == 0:
            raise InvalidHarnessException('No arguments are defined in the source code')
        
        file_path, argc = target_with_argc.popitem()
        
        return (file_path, argc)
    
    # extract argc from all following source code
    def _get_all_argc(self, java_code: JavaCode, is_follow_child=True) -> dict:
        file_path = java_code.filepath
        res = {}
                
        argc = self._extract_argc_with_regex(java_code.source_code)
        
        if argc is not None:
            res[file_path] = argc
            
        if is_follow_child:
            for child_java_code in java_code.children:
                res.update(self._get_all_argc(child_java_code))
            
        return res
    
    # extract argc from source code
    def _extract_argc_with_regex(self, source_code) -> int: 
        m = re.search('.*(split\("\\\\0"\)).*', source_code)
        
        if m:
            split_end_idx = m.regs[0][1]
            argc = re.findall('.*\.length.*==.*([0-9]+).*', source_code[split_end_idx:])
            if argc:
                return int(argc[0])
            
            argc = re.findall('.*\.length.*!=.*([0-9]+).*', source_code[split_end_idx:])
            if argc:
                return int(argc[0])
            
            argc = re.findall('.*([0-9]+).*==.*\.length.*', source_code[split_end_idx:])
            if argc:
                return int(argc[0])
            
            argc = re.findall('.*([0-9]+).*!=.*\.length.*', source_code[split_end_idx:])
            if argc:
                return int(argc[0])
            
            raise ArgumentLengthNotDefinedException('Argument length is not defined in the source code')
        
        return None

class CodeSerializer(object):
    def __init__(self):
        self.values = {}
        self.body = None
        self.index = -1
        self.fowrules = []
        self.backrules = []

    def get_symbols(self, node):
        res = set()
        if node is None:
            return res
        if isinstance(node, list):
            for n in node:
                res = res.union(self.get_symbols(n))
        elif isinstance(node, dict):
            for k, v in node.items():
                res = res.union(self.get_symbols(n))
        elif isinstance(node, set):
            for n in node:
                res = res.union(self.get_symbols(n))
        elif isinstance(node, javalang.tree.Node):
            for attr in node.attrs:
                res = res.union(self.get_symbols(getattr(node, attr)))
        else:
            res.add(node)
        return res

# JavaPrinter().print(jc.children[0].classes['PipelineCommandUtilFuzzer'].methods['fuzzerTestOneInput'].obj)
# jc.classes['PipelineCommandUtilPovRunner'].methods['fuzzerTestOneInput'].obj
# jc.children[0].classes['PipelineCommandUtilFuzzer'].methods['fuzzerTestOneInput'].obj

# from modules.analyzer.TaintAnalyzer import TaintAnalyzer
# taint_analyzer = TaintAnalyzer()
# # taint_analyzer.add_rule(TaintRule())
# taint_analyzer.add_source('.*\.getenv("POV_FILENAME").*');
# taint_analyzer.add_sink("*.")
