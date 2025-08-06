import os
import re

from .repository import JavaRepository
from .gen import generate_example_body
from ..llm import ChatBot
from ..java_static import LLMJavaStaticParser
from ..common.harness import Harness
from ..common.project import Project
from ..utils.logger import Log

PROMPT = {'parse_class': '''Parse the class name from the following code:

```java
{code}
```

Print the class name only.
''', 'get_harness_method': '''Extract the harness class and method in the following target code. 

```java
{code}
```

Print the class name and method name only.

# Output format example

- TargetClass.fuzzerTestOneInput

'''}

class LLMHarnessParser:
    def __init__(self, project: Project):
        self.harnesses = {}
        self._project = project 
        self._repository = JavaRepository(project.project_path)
        
        # exclude external source directories
        for source_dir in self._project.cp_sources:
            self._repository.add_exclude(os.path.join('src', source_dir))
        
        self._harness_file_path = {id: self._repository.path(project.harnesses[id]['source']) for id in project.harnesses}
        
    
    def _parse_harness(self, code: str) -> str:
        chatbot = ChatBot()
        chatbot.add_user_message(PROMPT['get_harness_method'].format(code=code))
        res = chatbot.run()
        return res[0]
    
    def get_harnesses(self) -> dict[str: Harness]:
        return self.harnesses
        
    def get_harness(self, id) -> Harness:
        with open(self._harness_file_path[id], 'r') as f:
            code = f.read()
        
        harness = Harness()
        harness.source_code = code
        harness_method = self._parse_harness(code)
        
        match = re.findall(r'- (.*)\.(.*)', harness_method)
        if not match:
            Log.e(f'Failed to parse harness method: {harness_method}')
            return None
        
        harness.target_class = match[0][0]
        harness.target_method = match[0][1]
        
        return harness


class LLMDeepJavaProjectParser:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._parser = LLMJavaStaticParser()
        self._repository = JavaRepository(self._project.project_path)
        
        # exclude external source directories
        for source_dir in self._project.cp_sources:
            self._repository.add_exclude(os.path.join('src', source_dir))
        
        self._invocation_code = {}
        self._dependencies = {}
    
    def get_harness(self, harness_file) -> Harness:
        class_name = os.path.basename(harness_file).replace(".java", "")
        
        Log.d(f'Parsing harness - {id}: {class_name}')
        self._visit(harness_file, class_name, "fuzzerTestOneInput", ["byte[] data"])
        Log.d(f'Parsing harness Done')        
        Log.d(f'Visited {len(self._invocation_code)} files')
        
        harness_code = self._invocation_code[harness_file][class_name]["fuzzerTestOneInput"]
        
        harness = Harness()
        harness.source_code = harness_code
        harness.class_name = "FuzzerHarness"
        harness.target_class = class_name
        harness.target_method = "fuzzerTestOneInput"
        
        return harness
        
    def _is_visited(self, file_path: str, class_name: str, method_name: str):
        if file_path in self._invocation_code:
            if class_name in self._invocation_code[file_path]:
                if method_name in self._invocation_code[file_path][class_name]:
                    return True
        return False
    
    def _set_visited(self, file_path: str, class_name: str, method_name: str):
        if file_path not in self._invocation_code:
            self._invocation_code[file_path] = {}
            self._dependencies[file_path] = {}
        
        if class_name not in self._invocation_code[file_path]:
            self._invocation_code[file_path][class_name] = {}
            self._dependencies[file_path][class_name] = {}
        
        self._invocation_code[file_path][class_name][method_name] = None
        self._dependencies[file_path][class_name][method_name] = []
    
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
        
        invocations = self._parser.get_invocations(code, class_name, method_name)
        for invocation in invocations:
            parsed_invocation = re.findall(r'(\w+)\.(\w+)\((.*?)\)', invocation)
            if len(parsed_invocation) == 1:
                classname, methodname, arguments = parsed_invocation[0]
                
                for target_file in self._repository.find_file_by_name(f'{classname}.java'):
                    dependencies.append((target_file, classname, methodname, arguments))
            else: 
                Log.d(f'Not typical java method : {invocation}')
        
        return dependencies

    
    def _remove_comments(self, code: str):
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def _visit(self, file_path: str, class_name: str, method_name: str, intersting_args: list, depth: int = 0, max_depth: int = 3):
        if depth > max_depth:
            return
        
        if self._is_visited(file_path, class_name, method_name):
            return
        
        Log.d(f'Visiting: {file_path}, {class_name}, {method_name}, {intersting_args}')
        self._set_visited(file_path, class_name, method_name)
        
        with open(file_path, "r") as f:
            code = f.read()
        
        code = self._remove_comments(code)
        
        dependencies = self._get_dependencies(code, class_name, method_name)
        self._dependencies[file_path][class_name][method_name] = dependencies
        
        for child_file, child_class_name, child_method_name, arguments in dependencies:
            child_args = self._extract_argument(arguments, ["String", "int", "byte[]", "boolean"])
            Log.d(f"invoke -> {child_file}, {child_class_name}.{child_method_name}({child_args})")
            if len(child_args) != 0:
                self._visit(child_file, child_class_name, child_method_name, child_args, depth+1, max_depth)
        
        dependencies_code = []
        for child_file, child_class_name, child_method_name, arguments in dependencies:
            if not self._is_visited(child_file, child_class_name, child_method_name):
                continue 
            
            sample_code = self._invocation_code[child_file][child_class_name][child_method_name]
            if sample_code is not None:
                dependencies_code.append((child_class_name, child_method_name, sample_code))
        
        chatbot = ChatBot(temperature=0.0)
        invocation_code = generate_example_body(chatbot, code, class_name, method_name, intersting_args, dependencies_code)
        self._invocation_code[file_path][class_name][method_name] = invocation_code
        
        return
        