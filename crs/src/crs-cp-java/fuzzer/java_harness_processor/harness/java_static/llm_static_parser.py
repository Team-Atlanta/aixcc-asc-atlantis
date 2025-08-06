import re

from ..llm.chatter import StaticParseChatter
from ..llm import ChatBot


class LLMJavaStaticParser:
    def __init__(self):
        self.code = None
    
    def _get_chatbot(self, **kwargs):
        return ChatBot(**kwargs)
    
    def get_body(self, class_name: str, method_name: str):
        tcode = self.__remove_comments(self.__code)
        class_body = tcode[tcode.find(f"class {class_name}"):]
        class_body = self.__remove_brackets(class_body)[0]
        
        method_bodies = self.__remove_brackets(class_body)
        
        raw_class_body = class_body
        for method_body in method_bodies:
            method_header = raw_class_body[:raw_class_body.find(method_body)]
            if method_name in method_header:
                return method_body

            raw_class_body = raw_class_body[raw_class_body.find(method_body) + len(method_body) + 1:]
        
        return None

    def get_invocations(self, code: str, class_name: str, method_name: str):
        chatbot = self._get_chatbot(temperature=0.0, n=1)
        res = StaticParseChatter.extract_invocations(chatbot, code, class_name, method_name)[0]
        res = self.__extract_codeblock(res)
        res = res.strip()
        
        targets = re.findall(r"- \"(.*?)\"", res)
        targets = list(set(targets))
        
        return targets

    def __remove_brackets(self, code):
        stack = []
        result = []
        for i, c in enumerate(code):
            if c == '{':
                stack.append(i)
            elif c == '}':
                if stack:
                    start = stack.pop()
                    if len(stack) == 0:
                        result.append(code[start + 1:i])
                        
        return result   
    
    def __remove_comments(self, code):
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def __extract_codeblock(self, code: str):
        code_candidate = re.findall(r"```.*?\n(.*?)```", code, re.DOTALL)
        if len(code_candidate) > 0:
            code = code_candidate[0]
        
        return code
    

    # Deprecated
    def __get_body(self, code, class_name, method_name):
        chatbot = self._get_chatbot(temperature=0.0, n=1)
        res = StaticParseChatter.extract_method_body(chatbot, code, class_name, method_name)[0]
        res = self.__extract_codeblock(res)
        res = res.strip()
        return res

    
    # def get_dependencies(self, code: str, class_name, method_name: str) -> list[str]:
    #     chatbot = ChatBot(temperature=0.0, n=1)
    #     res = StaticParseChatter.extract_invocations(chatbot, code, method_name)[0]
    #     res = self.__extract_codeblock(res)
    #     res = res.strip()
    #     invocations = re.findall(r"- \"(.*?)\"", res)
    
    #     invocations = list(set(invocations))
        
    #     dependencies = []
    #     for invocation in invocations:
    #         parsed_invocation = re.findall(r'(\w+)\.(\w+)\((.*?)\)', invocation)
    #         if len(parsed_invocation) == 1:
    #             classname, methodname, arguments = parsed_invocation[0]
                
    #             for target_file in self.repository.find_file_by_name(f'{classname}.java'):
    #                 dependencies.append((target_file, classname, methodname, arguments))
    #         else: 
    #             print("Not typical java method : ", invocation)
        
    #     return dependencies

