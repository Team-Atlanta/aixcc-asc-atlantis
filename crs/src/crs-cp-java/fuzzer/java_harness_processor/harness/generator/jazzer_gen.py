import re
import javalang

from ..llm import ChatBot
from ..llm.chatter import CodeHarnessGeneratorChatter, JavaStaticConverterChatter
from ..utils.logger import Log


class LLMByteHarnessGenerator:
    def __init__(self, **kwargs):
        self.code = ""
        self.class_name = ""
        self._kwargs = kwargs

    def generate(self):
        return self._converter_byte_parameter()
            
    def _get_chatbot(self):
        return ChatBot(**self._kwargs)
    
    def _extract_code(self, code):
        code_candidate = re.findall(r"```java(.*?)```", code, re.DOTALL)
        
        if not code_candidate:
            return code
        
        return code_candidate[0]
    
    def _converter_byte_parameter(self):
        chatbot = self._get_chatbot()
        code = JavaStaticConverterChatter.convert_byte_parameter(chatbot, self.code, self.class_name)[0]
        return self._extract_code(code)


class LLMJazzerHarnessGenerator_v1:
    def __init__(self, **kwargs):
        self.code = None
        self.class_name = None
        self._kwargs = kwargs
        self.harness_code = None
        self.is_valid = False
        self.is_included_origin = False
        
    def generate(self):
        code = self.code
        if 'System.getenv("POV_FILENAME")' in code:
            code = self._converter_byte_parameter(code)
        
        harness_code = self._converter_provider3(code)
        self.harness_code = harness_code
        
        if self.is_included_origin:
            harness_code = self._include_origin_code(harness_code)
        
        self.is_valid = self._check_validation(harness_code)

        return harness_code
            
    def _get_chatbot(self):
        return ChatBot(**self._kwargs)
    
    def _extract_code(self, code):
        code_candidate = re.findall(r"```java(.*?)```", code, re.DOTALL)
        
        if not code_candidate:
            return code
        
        return code_candidate[0]
    
    def _converter_byte_parameter(self, code):
        chatbot = self._get_chatbot()
        code = JavaStaticConverterChatter.convert_byte_parameter(chatbot, code)[0]
        return self._extract_code(code)
    
    def _converter_provider1(self, code):
        chatbot = self._get_chatbot()
        code = CodeHarnessGeneratorChatter.harness_generate(chatbot, code)[0]
        
        return self._extract_code(code)
    
    def _converter_provider2(self, code):
        chatbot = self._get_chatbot()
        code = CodeHarnessGeneratorChatter.harness_generate2(chatbot, code)[0]
        
        return self._extract_code(code)

    def _converter_provider3(self, code):
        chatbot = self._get_chatbot()

        code = CodeHarnessGeneratorChatter.harness_generate4(chatbot, code, self.class_name)[0]
        
        # Give a change to keep printing once. 
        if not self._check_EOF(code):
            print("EOF")
            chatbot.add_user_message("keep printing.")
            sub_code = chatbot.run()[0]
            sub_code = self._extract_code(sub_code)
            
            # delete last line
            code = code.replace("```java\n", "")
            code = code.split("\n")
            code = code[:-1]
            code = "\n".join(code)
            code += sub_code
        else:
            code = self._extract_code(code)
        
        return code
    
    def _include_origin_code(self, code):
        orig_codes =[]
        orig_imports = []
        
        for line in self.code.split("\n"):
            line = line.strip()
            if line.startswith("import"):
                orig_imports.append(line)
            elif line.startswith("package"):
                pass
            else:
                if "public class" in line:
                    class_name = re.findall("public class\s+(\w+)", line)[0]
                    line = line.replace("public class", "class")
                orig_codes.append(line)
        
        # remove class_name in orig_imports
        code = re.sub(rf'import .*\.{class_name}\s*;', '', code)
        
        prefix = "\n".join(orig_imports) + "\n"
        postfix = "\n".join(orig_codes) + "\n"
        
        return prefix + code + postfix
    
    
    def _check_EOF(self, code):
        code = code.strip() 
        if code.startswith("```java") and not code.endswith("```"):
            return False
        
        return True

    def _check_validation(self, code):
        # valid java code
        try:
            lang_code = javalang.parse.parse(code)
        except Exception as e:
            print(f"{__name__} javalang error: {e}")
            Log.e(f"{__name__} javalang error: {e}")
            return False
        return True


class LLMJazzerHarnessGenerator_v2:
    def __init__(self, **kwargs):
        self.code = None
        self.class_name = None


