from pathlib import Path
import unittest
from .test_init import *
from harness.generator import BlobGenerator, FakeFileStreamGenerator, ProtoBufByteGenerator
from harness.common.project import Project
import os
import shutil


HARNESS_MAX=14
HARNESS_EXCEPT=[4]


PROTOC_BIN = os.path.join(CP_DIR, 'container_scripts/protoc/bin/protoc')
PROTO_JAR = os.path.join(CP_DIR, 'container_scripts/protoc/jar/protobuf-java-3.25.3.jar')


class RealSettingTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.tmpDir = Path(os.path.dirname(os.path.abspath(__file__))) / "harnesses"
        if self.tmpDir.exists():
            shutil.rmtree(self.tmpDir)
        os.mkdir(self.tmpDir)
        self.project = Project(CP_DIR)
        self.cp = CP_DIR
        for i in range(1, HARNESS_MAX):
            if i in HARNESS_EXCEPT:
                continue
            harness_id = f'id_{i}'
            os.system('python3 main.py -f protobuf -o ' + str(self.tmpDir) + ' ' + self.cp + ' ' + harness_id)
        self.classpath=''

    def test_1_generation(self):
        harnesses = os.listdir(self.tmpDir)
        for i in range(1, HARNESS_MAX):
            if i in HARNESS_EXCEPT:
                continue
            harness_id = f'id_{i}'
            source = Path(self.project.harnesses[harness_id]["source"])
            harness_id = source.stem
            self.assertTrue(harness_id + '_Fuzz.java' in harnesses and harness_id + '_Fuzz.proto' in harnesses)
    
    def setup_classpath(self):
        SRC = f"{CP_DIR}/src"
        WORK = f"{CP_DIR}/work"
        
        ADD_PATHS = [ "/classpath/jazzer/*" ]
        # $(find "${SRC}" -name "classpath" -type d -exec find {} -type f -name "*.jar" -printf "%p:" \;)
        ADD_PATHS += [ str(jar) for jar in Path(f"{SRC}").rglob("*.jar") if "classpath" in str(jar) ]
        # $(find "${SRC}" -name "build" -type d -printf "%p:")
        ADD_PATHS += [ str(jar) for jar in Path(f"{SRC}").rglob("build") ]
        ADD_PATHS += [ str(jar) for jar in Path(f"{WORK}").rglob("*.jar") ]
        
        self.classpath = ":".join(ADD_PATHS)

    # this is executed in docker container of `crs-cp-jenkins` only
    def test_2_compile(self):
        if COMPILE_TEST != 'enabled':
            print("Skip compile test")
            return
        
        self.setup_classpath()

        harnesses = list(filter(lambda x: x.endswith(".java"), os.listdir(self.tmpDir)))
        for harness_id in harnesses:
            # it is easier to let protoc working on different directories for these harnesses
            harness_id = harness_id[:-5]

            harness_compile_dir = self.tmpDir / harness_id
            # 1. clean the harness directory if exists and recreate it
            if harness_compile_dir.exists():
                shutil.rmtree(harness_compile_dir)
            os.mkdir(harness_compile_dir)

            # 2. copy .proto file to the directory as HarnessInput.proto 
            os.system('cp ' + str(self.tmpDir) + '/' + harness_id + '.proto ' + str(harness_compile_dir) + '/HarnessInput.proto')

            # 3. run protoc to generate java file
            os.system(PROTOC_BIN + ' --proto_path=' + str(harness_compile_dir) + ' --java_out=' + str(harness_compile_dir) + ' ' + str(harness_compile_dir) + '/HarnessInput.proto')

            # 4. compile the harness with updated classpath
            harness_classpath = self.classpath + ":" + str(harness_compile_dir) + ":" + str(harness_compile_dir / 'ourfuzzzdriver') + ":" + PROTO_JAR
            os.system('javac -d ' + str(harness_compile_dir) + ' -cp ' + harness_classpath + ' ' + str(self.tmpDir) + '/' + harness_id + '.java')

            self.assertTrue(os.path.exists(harness_compile_dir / (harness_id + '.class')))

        
