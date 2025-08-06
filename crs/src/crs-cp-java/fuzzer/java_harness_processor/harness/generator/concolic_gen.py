import re

from ..llm import ChatBot
from ..llm.chatter import JavaStaticConverterChatter, ConcolicGenerateChatter


class LLMConcolicHarnessGenerator_v1:
    def __init__(self, **kwargs):
        self.code = ""
        self.class_name = ""
        self._kwargs = kwargs

    def generate(self):
        return self._converter_string_parameter()
            
    def _get_chatbot(self):
        return ChatBot(**self._kwargs)
    
    def _extract_code(self, code):
        code_candidate = re.findall(r"```java(.*?)```", code, re.DOTALL)
        
        if not code_candidate:
            return code
        
        return code_candidate[0]
    
    def _converter_string_parameter(self):
        chatbot = self._get_chatbot()
        code = JavaStaticConverterChatter.convert_string_parameter(chatbot, self.code, self.class_name)[0]
        return self._extract_code(code)



class LLMConcolicHarnessGenerator_v2:
    def __init__(self, **kwargs):
        self.code = ""
        self.class_name = ""
        self._kwargs = kwargs

    def generate(self):
        return self._converter_string_parameter()
            
    
    def _extract_code(self, code):
        code_candidate = re.findall(r"```java(.*?)```", code, re.DOTALL)
        
        if not code_candidate:
            return code
        
        return code_candidate[0]
    
    def _converter_string_parameter(self):
        code = ConcolicGenerateChatter.convert_byte_to_jazzer(ChatBot(), self.code)[0]
        code = self._extract_code(code)
        code = code.replace("import com.code_intelligence.jazzer.api.FuzzedDataProvider;", "import org.team_atlanta.*;")
        code = ConcolicGenerateChatter.add_main_method(ChatBot(), code)[0]
        code = self._extract_code(code)
        code = ConcolicGenerateChatter.change_class_name(ChatBot(), code, self.class_name)[0]
        code = self._extract_code(code)
        return code

