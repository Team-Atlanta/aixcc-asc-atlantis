import unittest
from .test_init import *
from harness.generator import BlobGenerator, FakeFileStreamGenerator, ProtoBufByteGenerator


blob_code = '''
import java.io.File;
import java.io.FileOutputStream;

public class BlobHarness {
    public static void fuzzerTestOneInput(byte[] data) throws Throwable 
    {
        String filename = System.getenv("POV_FILENAME");
        if (null == filename) 
            filename = "/work/tmp_blob";
            
        FileOutputStream fos = new FileOutputStream(filename);
        fos.write(data);
        fos.close();
        
        TargetClass.fuzzerTestOneInput(data);
    }
}
'''

fake_file_stream_code = '''import java.util.List;
import java.io.FileNotFoundException;
import com.code_intelligence.jazzer.api.FuzzedDataProvider;

class TargetClass {
    public static void fuzzerTestOneInput(byte[] data) {
    }
}

class FileInputStream {
    public static byte[] mutated_data = null;
    public FileInputStream(String name) throws FileNotFoundException {
        if(name == "nonexistent") 
            throw new FileNotFoundException();
    }
    
    public byte[] readAllBytes() {
        return mutated_data;
    }
}

public class FakeFileStreamHarness {
    private static boolean dumpOnly = false;

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Throwable {
        String serialized_data = "" + provider.consumeString(100);
        FileInputStream.mutated_data = serialized_data.getBytes();
        if (dumpOnly) return;
        TargetClass.fuzzerTestOneInput(null);

    }

    public static void main(String[] args) throws Throwable {
        dumpOnly = true;

        // read input 
        byte[] data = new java.io.FileInputStream(args[0]).readAllBytes();

        // transform the data to FileInputStream.mutated_data
        FileInputStream.mutated_data = data; // NAIVE transform by default

        // dump to file
        new java.io.FileOutputStream(args[1]).write(FileInputStream.mutated_data);
    }
}
'''

protobuf_code = '''
syntax = "proto2";

package ourfuzzdriver;
option java_package = "ourfuzzdriver";

message HarnessInput {
  required bytes field1 = 1;
  required bytes field2 = 2;
}
'''

class GeneratorTest(unittest.TestCase):
    def test_blob(self):
        generator = BlobGenerator()
        generator.main_class_name = 'BlobHarness'
        generator.target_class = 'TargetClass'
        code = generator.generate()
        self.assertEqual(code, blob_code)
    
    def test_fake_file_stream(self):
        generator = FakeFileStreamGenerator()
        generator.imports.append('com.code_intelligence.jazzer.api.FuzzedDataProvider')
        generator.main_class_name = 'FakeFileStreamHarness'
        generator.main_method_signature = 'void fuzzerTestOneInput(FuzzedDataProvider provider)'
        generator.target_code = 'class TargetClass {\n    public static void fuzzerTestOneInput(byte[] data) {\n    }\n}'
        generator.target_arguments = ["provider.consumeString(100)"]
        generator.target_invocations.append('TargetClass.fuzzerTestOneInput(null)')
        code = generator.generate()
        # print(code)
        self.assertEqual(code, fake_file_stream_code)
        
    def test_protobuf(self):
        generator = ProtoBufByteGenerator()
        generator.target_arguments = [{'name': 'arg1'}, {'name': 'arg2'}]
        code = generator.generate()
        self.assertEqual(code, protobuf_code)