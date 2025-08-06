import unittest
import shutil
from pathlib import Path

from .test_init import *
from harness.utils.builder import CPBuilder
from harness.common.project import Project
from .data import test_harnesses


project = Project(CP_DIR)
maven_repo = os.path.join(CP_DIR, 'work/maven_repo')
harness_out_dir = os.path.join(CP_DIR, 'out/harnesses')
TMP_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".tmp"

result_output = {
    "id_1": "com/aixcc/jenkins/harnesses/two/JenkinsTwo.class",
    "id_2": "com/aixcc/jenkins/harnesses/one/JenkinsOne.class",
    "id_3": "com/aixcc/jenkins/harnesses/three/JenkinsThree.class",
    "id_4": "com/aixcc/jenkins/harnesses/four/JenkinsFour.class",
    "id_5": "com/aixcc/jenkins/harnesses/five/JenkinsFive.class",
    "id_6": "com/aixcc/jenkins/harnesses/six/JenkinsSix.class",
    "id_7": "com/aixcc/jenkins/harnesses/seven/JenkinsSeven.class",
    "id_8": "com/aixcc/jenkins/harnesses/eight/JenkinsEight.class",
    "id_9": "com/aixcc/jenkins/harnesses/nine/JenkinsNine.class",
    "id_10": "com/aixcc/jenkins/harnesses/ten/JenkinsTen.class",
    "id_11": "com/aixcc/jenkins/harnesses/eleven/JenkinsEleven.class",
    "id_12": "com/aixcc/jenkins/harnesses/twelve/JenkinsTwelve.class",
    "id_13": "com/aixcc/jenkins/harnesses/thirteen/JenkinsThirteen.class",
    "id_14": "com/aixcc/jenkins/harnesses/fourteen/JenkinsFourteen.class",
}


class BuilderTest(unittest.TestCase):
    def setUp(self):
        if not os.path.exists(TMP_DIR):
            os.mkdir(TMP_DIR)
    
    def tearDown(self):
        shutil.rmtree(TMP_DIR)
        
    def test_origin(self):
        builder = CPBuilder(CP_DIR)
        
        source_file = Path(DOC_DIR) / "test_data/jenkins-harness-two/src/main/java/com/aixcc/jenkins/harnesses/two/JenkinsTwo.java"
        builder.javac(source_file, dest_dir=TMP_DIR)
        
        self.assertTrue(os.path.exists(str(Path(TMP_DIR) / "com/aixcc/jenkins/harnesses/two/JenkinsTwo.class")))

    def test_harness_all(self):
        builder = CPBuilder(CP_DIR)
            
        for id in test_harnesses:
            source_file = Path(DOC_DIR) / test_harnesses[id]["source"]
            builder.javac(source_file, dest_dir=TMP_DIR)
            
            self.assertTrue(os.path.exists(str(Path(TMP_DIR) / result_output[id])), f"Failed to compile: {id}")
        