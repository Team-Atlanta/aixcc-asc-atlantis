import re

from ..llm import ChatBot
from ..llm.chatter import JavaCodeEditChatter



class JavaCodeEditor:
    def __init__(self, code: str, class_name: str):
        self._code = code
        self._class_name = class_name
        
    def change_class_name(self, new_class_name: str):
        self._code = re.sub(rf'(class\s+){self._class_name}(\s+{{)', f'\\1{new_class_name}\\2', self._code)
        self._class_name = new_class_name
    
    def save(self, file_path: str):
        with open(file_path, 'w') as f:
            f.write(self._code)
    
    def get_code(self):
        return self._code


class LLMJavaCodeEditor:
    def __init__(self, code: str):
        self._code = code
        self.prompt = ""
        self._is_changed = False
    
    def change_class_name(self, from_class_name, to_class_name: str):
        self._is_changed = True
        self.prompt += f'Change class name from "{from_class_name}" to "{to_class_name}"\n'
    
    def change_method_name(self, method_name: str):
        self._is_changed = True
        self.prompt += f"Change method name to {method_name}\n"
        
    def change_package(self, package_name: str):
        self._is_changed = True
        if package_name == None or package_name == "":
            self.prompt += "Remove package name\n"
        else:
            self.prompt += f"Change package name to {package_name}\n"
    
    def _apply_change(self):
        self._is_changed = False
        code = JavaCodeEditChatter.edit_code(ChatBot(), self._code, self.prompt)[0]
        self._code = re.findall(r"```java(.*?)```", code, re.DOTALL)[0]
    
    def save(self, file_path: str):
        if self._is_changed:
            self._apply_change()
            
        with open(file_path, 'w') as f:
            f.write(self._code)
    
    def get_code(self):
        if self._is_changed:
            self._apply_change()
            
        return self._code