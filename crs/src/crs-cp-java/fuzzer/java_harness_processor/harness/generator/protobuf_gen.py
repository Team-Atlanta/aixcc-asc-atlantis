import re
import javalang

from ..llm import ChatBot
from ..llm.chatter import CodeHarnessGeneratorChatter, JavaStaticConverterChatter
from ..utils.logger import Log


proto_template = '''
syntax = "proto2";

package ourfuzzdriver;
option java_package = "ourfuzzdriver";

message HarnessInput {{
{field_declaration}
}}
'''

class ProtoBufByteGenerator: 
    def __init__(self) -> None:
        self.target_arguments = []
        
    def generate(self):
        field_declaration = '\n'.join([ f'  required bytes field{i + 1} = {i + 1};' for i in range(len(self.target_arguments)) ])
        proto_code = proto_template.format(field_declaration=field_declaration)
        return proto_code

class ProtoBufMultiTypeGenerator: 
    def __init__(self) -> None:
        # int32, string, bytes, bool
        self.argument_types = []
        
    def generate(self):
        field_declaration = ""
        for i, type in enumerate(self.argument_types):
            field_declaration += f'  required {type} field{i + 1} = {i + 1};\n'
            
        proto_code = proto_template.format(field_declaration=field_declaration)
        return proto_code

        
class LLMProtobufHarnessGenerator:
    def __init__(self):
        self.main_class_name = None
        self.target_class_name = None
        self.jazzer_code = None
        self.arguments = [] # OUTPUT value
        self.harness_code = None
        self.is_valid = False
        self.is_included_origin = False
        
    def generate(self):
        protobuf_code = self._converter_protobuf(self.jazzer_code)
        self.harness_code = protobuf_code
        
        if self.is_included_origin:
            protobuf_code = self._include_origin_code(protobuf_code)
        
        self.is_valid = self._check_validation(protobuf_code)
        
        return protobuf_code
    
    def _get_chatbot(self):
        return ChatBot()
    
    def _converter_protobuf(self, code):
        chatbot = self._get_chatbot()

        gen_code = CodeHarnessGeneratorChatter.protobuf_generate(chatbot, code, self.target_class_name, self.main_class_name)[0]
        gen_code = self._extract_code(gen_code)
        gen_code = gen_code.replace("import com.code_intelligence.jazzer.api.FuzzedDataProvider;", "import ourfuzzdriver.HarnessInputOuterClass;")
        gen_code = re.sub(r'void fuzzerTestOneInput\(.*\)', "void fuzzerTestOneInput(@NotNull HarnessInputOuterClass.HarnessInput input)", gen_code)
        
        arguments = []
        consumes = self._search_consumed_field(gen_code)
        field_index = len(consumes)
        for type, start_i, end_i in consumes[::-1]:
            if type == "consumeInt":
                arguments.append('int32')
            elif type == "consumeString":
                arguments.append('string')
            elif type == "consumeBytes":
                arguments.append('bytes')
            elif type == "consumeBoolean":
                arguments.append('bool')
            else:
                raise Exception("Not supported type: " + type)
            
            if type == "consumeBytes":
                gen_code = gen_code[:start_i] + f"input.getField{field_index}().toByteArray()" + gen_code[end_i:]
            else:
                gen_code = gen_code[:start_i] + f"input.getField{field_index}()" + gen_code[end_i:]
            field_index -= 1
        
        self.arguments = arguments[::-1]
        return gen_code
    
    def _search_consumed_field(self, code):
        consumed_fields = []
        
        lang_code = javalang.parse.parse(code)
        FIELD_PATTERN = r'consumeInt|consumeString|consumeBytes|consumeBoolean'
        for _, stmt in lang_code.filter(javalang.tree.MethodInvocation):
            for _, node in stmt:
                if self._find_pattern(node, FIELD_PATTERN):
                    start_i, end_i = self._get_invoke_location(node, code)
                    # if not contains in consumed_fields
                    if not any([start_i == s_i and e_i == end_i for _, s_i, e_i in consumed_fields]):
                        consumed_fields.append((node.member, start_i, end_i))
        
        return consumed_fields
    
    # get start_i, end_i  in "input.consumeInt(0, 255)"
    def _get_invoke_location(self, ast_node: javalang.tree.Node, code: str):
        line_num = ast_node.position[0]
        col_num = ast_node.position[1]
        
        codelines = code.split("\n")
        line = codelines[line_num - 1]
        start_i = len('\n'.join(codelines[:line_num - 1])) + col_num
        
        # parse invoke code method(~~)
        for i in range(start_i, start_i + len(line)):
            if code[i] == "(":
                start_ii = i
                break
        
        s = []
        for i in range(start_ii, start_ii + len(line)):
            if code[i] == "(":
                s.append(i)
            elif code[i] == ")":
                s.pop()
                if not s:
                    end_i = i + 1
                    break
        
        return start_i, end_i
    
    def _include_origin_code(self, code):
        orig_codes =[]
        orig_imports = []
        
        for line in self.jazzer_code.split("\n"):
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
    
    
    def _extract_code(self, code):
        code_candidate = re.findall(r"```java(.*?)```", code, re.DOTALL)
        
        if not code_candidate:
            return code
        
        return code_candidate[0]
    
    def _check_validation(self, code):
        # valid java code
        try:
            lang_code = javalang.parse.parse(code)
        except Exception as e:
            print(f"{__name__} javalang error: {e}")
            Log.e(f"{__name__} javalang error: {e}")
            return False
        
        # Loop check
        FIELD_PATTERN = r"getField[0-9]+"
        for _, while_statement in lang_code.filter(javalang.tree.WhileStatement):
            for _, ast_node in while_statement:
                if self._find_pattern(ast_node, FIELD_PATTERN):
                    return False
        for _, for_statement in lang_code.filter(javalang.tree.ForStatement):
            for _, ast_node in for_statement:
                if self._find_pattern(ast_node, FIELD_PATTERN):
                    return False
        for _, do_statement in lang_code.filter(javalang.tree.DoStatement):
            for _, ast_node in do_statement:
                if self._find_pattern(ast_node, FIELD_PATTERN):
                    return False
        
        return True
    
    # Check any AST tree has getField
    def _find_pattern(self, ast_node: javalang.tree.Node, pattern: str):
        for attr in ast_node.attrs:
            attr_value = getattr(ast_node, attr)
            if isinstance(attr_value, str) and re.match(pattern, attr_value):
                return True
        return False
    
