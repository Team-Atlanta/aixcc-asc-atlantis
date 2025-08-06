import re
from ..java_static import LLMJavaCodeEditor

template_code = '''
import java.io.File;
import java.io.FileOutputStream;

public class {class_name} {{
    public static void fuzzerTestOneInput(byte[] data) throws Throwable 
    {{
        String filename = System.getenv("POV_FILENAME");
        if (null == filename) 
            filename = "{file_path}";
            
        FileOutputStream fos = new FileOutputStream(filename);
        fos.write(data);
        fos.close();
        
        {target_class}.fuzzerTestOneInput(data);
    }}
}}
'''

class BlobGenerator:
    def __init__(self):
        self.main_class_name = 'BlobGenerator'
        self.target_class = ''
        self.file_path = '/work/tmp_blob'
    def generate(self):
        return template_code.format(class_name=self.main_class_name, target_class=self.target_class, file_path=self.file_path)


local_blob_template_code = '''
{code}

class LocalBlobGenerator {{
    public static void fuzzerTestOneInput(byte[] data) throws Exception, Throwable 
    {{
        String filename = System.getenv("POV_FILENAME");
        if (null == filename) 
            filename = "{file_path}";
            
        java.io.FileOutputStream fos = new java.io.FileOutputStream(filename);
        fos.write(data);
        fos.close();
        
        {target_class}.fuzzerTestOneInput(data);
    }}
}}
'''
# LocalBlobGenerator
# it changes the harness to use the LocalBlobGenerator instead of the original target_class.
#   target_class: the original target class name
#   code: the original harness code
class LocalBlobConverter:
    def __init__(self):
        self.code = None
        self.from_class_name = None
        self.to_class_name = None
        self.target_class = None
        self.file_path = '/work/tmp_blob'

    def generate(self):
        if self.code is None or self.target_class is None:
            raise Exception('code and target_class must be set before calling generate()')
        if self.from_class_name is None or self.to_class_name is None:
            raise Exception('"from_class_name" and "to_class_name" must be set before calling generate()')
        
        editor = LLMJavaCodeEditor(self.code)
        editor.change_class_name(self.from_class_name, self.to_class_name)
        code = editor.get_code()
        code = code.replace(f'{self.target_class}.fuzzerTestOneInput', 'LocalBlobGenerator.fuzzerTestOneInput')
        return local_blob_template_code.format(code=code, target_class=self.target_class, file_path=self.file_path)


protobuf_blob_template_code = '''
{code}

class LocalBlobGenerator {{
    public static String dest_file = "{file_path}";
    public static void fuzzerTestOneInput(byte[] data)
    {{
        try {{      
            java.io.FileOutputStream fos = new java.io.FileOutputStream(LocalBlobGenerator.dest_file);
            fos.write(data);
            fos.close();
        }} catch (Exception e) {{
            e.printStackTrace();
        }}
    }}
    
    public static void main(String[] args) throws Throwable, Exception {{
        LocalBlobGenerator.dest_file = args[1];
        
        // read input 
        byte[] data = new java.io.FileInputStream(args[0]).readAllBytes();

        // transform the data to FileInputStream.mutated_data
        {target_class}.fuzzerTestOneInput(HarnessInputOuterClass.HarnessInput.parseFrom(data));
    }}
}}
'''
# LocalBlobGenerator
# it changes the harness to use the LocalBlobGenerator instead of the original target_class.
#   target_class: the original target class name
#   code: the original harness code
class ProtobufBlobConverter:
    def __init__(self):
        self.code = None
        self.from_class_name = None
        self.to_class_name = None
        self.target_class = None
        self.file_path = '/work/tmp_blob'

    def generate(self):
        if self.code is None or self.target_class is None:
            raise Exception('code and target_class must be set before calling generate()')
        if self.from_class_name is None or self.to_class_name is None:
            raise Exception('"from_class_name" and "to_class_name" must be set before calling generate()')
        
        editor = LLMJavaCodeEditor(self.code)
        editor.change_class_name(self.from_class_name, self.to_class_name)
        code = editor.get_code()
        code = code.replace(f'{self.target_class}.fuzzerTestOneInput', 'LocalBlobGenerator.fuzzerTestOneInput')
        return protobuf_blob_template_code.format(code=code, target_class=self.to_class_name, file_path=self.file_path)

jazzer_blob_template_code = '''
{code}

class LocalBlobGenerator {{
    public static String dest_file = "{file_path}";
    public static void fuzzerTestOneInput(byte[] data)
    {{
        try {{
            java.io.FileOutputStream fos = new java.io.FileOutputStream(LocalBlobGenerator.dest_file);
            fos.write(data);
            fos.close();
        }} catch (Exception e) {{
            e.printStackTrace();
        }}
    }}
    
    public static void main(String[] args) throws Throwable, Exception {{
        LocalBlobGenerator.dest_file = args[1];
        
        // read input 
        java.io.FileInputStream fis = new java.io.FileInputStream(args[0]);
        fis.skip(5);
        byte[] data = fis.readAllBytes();
        
        {target_class}.fuzzerTestOneInput(com.code_intelligence.jazzer.driver.FuzzedDataProviderImpl.withJavaData(data));
    }}
}}
'''

class JazzerBlobConverter:
    def __init__(self):
        self.code = None
        self.from_class_name = None
        self.to_class_name = None
        self.target_class = None
        self.file_path = '/work/tmp_blob'

    def generate(self):
        if self.code is None or self.target_class is None:
            raise Exception('code and target_class must be set before calling generate()')
        if self.from_class_name is None or self.to_class_name is None:
            raise Exception('"from_class_name" and "to_class_name" must be set before calling generate()')
        
        editor = LLMJavaCodeEditor(self.code)
        editor.change_class_name(self.from_class_name, self.to_class_name)
        code = editor.get_code()
        code = code.replace(f'{self.target_class}.fuzzerTestOneInput', 'LocalBlobGenerator.fuzzerTestOneInput')
        return jazzer_blob_template_code.format(code=code, target_class=self.to_class_name, file_path=self.file_path)


static_template_code = '''
{code}

Change the main method to the following:

public static void main(String[] args) throws Exception {{
    BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
    
    {target_class}.fuzzerTestOneInput(bal.readAsBytes());
}}

'''
class StaticBlobGenerator:
    def __init__(self):
        self.code = None
        self.target_class = None

    def generate(self):
        if self.code is None or self.target_class is None:
            raise Exception('code and target_class must be set before calling generate()')
        
        code = self.code
        return local_blob_template_code.format(code=code, target_class=self.target_class)

