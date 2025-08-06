import re 

java_imports_template = '''import java.util.List;
import java.io.FileNotFoundException;
'''

harness_template = '''
class FileInputStream {{
    public static byte[] mutated_data = null;
    public FileInputStream(String name) throws FileNotFoundException {{
        if(name == "nonexistent") 
            throw new FileNotFoundException();
    }}
    
    public byte[] readAllBytes() {{
        return mutated_data;
    }}
}}

public class {class_name} {{
    private static boolean dumpOnly = false;

    public static {method_signature} throws Throwable {{
        String serialized_data = {fuzz_value};
        FileInputStream.mutated_data = serialized_data.getBytes();
        if (dumpOnly) return;
{invoke_target}
    }}

    public static void main(String[] args) throws Throwable {{
        dumpOnly = true;

        // read input 
        byte[] data = new java.io.FileInputStream(args[0]).readAllBytes();

        // transform the data to FileInputStream.mutated_data
        {transform_input_code}

        // dump to file
        new java.io.FileOutputStream(args[1]).write(FileInputStream.mutated_data);
    }}
}}
'''


class FakeFileStreamGenerator: 
    def __init__(self):
        self.imports = []
        self.main_class_name = 'FuzzerHarness'
        self.main_method_signature = 'void fuzzerTestOneInput(byte[] data)'
        self.target_code = ''
        self.target_arguments = []
        self.target_invocations = []
        self.DELIMITER = '\\0'
        self.transform_input_code = 'FileInputStream.mutated_data = data; // NAIVE transform by default'
    
    def _build_imports(self):
        res = java_imports_template
        for imp in self.imports:
            res += f'import {imp};\n'
        
        return res
    
    def _build_argument_code(self):
        if len(self.target_arguments) == 0:
            return '""'
        
        return f'"" + ' + f' + "{self.DELIMITER}" + '.join(self.target_arguments)

    def _build_invocation_code(self):
        code = ''
        for inv in self.target_invocations:
            code += f'        {inv};\n'
        return code
        
    def generate(self):
        target_code = self.target_code
        target_code = re.sub(r'System.getenv\("POV_FILENAME"\)', '""', target_code, flags=re.MULTILINE)
        target_code = re.sub(r'^package .*$\n', '', target_code, flags=re.MULTILINE) 
        target_code = re.sub(r'^import java\.io\.FileInputStream.*$\n', '', target_code, flags=re.MULTILINE) 
        target_code = re.sub(r'^public class', 'class', target_code, flags=re.MULTILINE)
        
        harness_code = harness_template.format(class_name=self.main_class_name, \
                                                method_signature=self.main_method_signature, \
                                                fuzz_value=self._build_argument_code(), \
                                                invoke_target=self._build_invocation_code(), \
                                                transform_input_code=self.transform_input_code)
        gen_code = ''
        gen_code += self._build_imports() + "\n"
        gen_code += target_code+ "\n"
        gen_code += harness_code
        
        return gen_code
