import os
import argparse
from pathlib import Path

class Javac:
    def __init__(self):
        self.classpath=[]
        
    def add_classpath(self, classpath: str):
        if classpath not in self.classpath:
            self.classpath.append(os.path.realpath(classpath))

    def compile(self, input_file_path: str, dest_dir: str = None):
        input_file_path = os.path.realpath(input_file_path)
        dest_dir = os.path.realpath(dest_dir) if dest_dir is not None else None
        
        if dest_dir is None: 
            dest_dir = str(Path(input_file_path).parent)
        
        classpath = ":".join(self.classpath)
        errno = os.system(f'javac -d "{dest_dir}" -cp "{classpath}" "{input_file_path}"')
        return errno


class CPBuilder:
    def __init__(self, cp_path: str):
        cp_path = os.path.realpath(cp_path)
        self.compiler = Javac()
        self._setup_classpath(cp_path)
        
    def _setup_classpath(self, cp_dir: str):
        SRC = Path(cp_dir, "src")
        WORK = Path(cp_dir, "work")
        ADD_PATHS = [ str(Path("/classpath/jazzer/*")) ]
        ADD_PATHS += [ str(jar) for jar in SRC.rglob("*.jar") if "classpath" in str(jar) ]
        ADD_PATHS += [ str(jar) for jar in SRC.rglob("build") ]
        ADD_PATHS += [ str(jar) for jar in WORK.rglob("*.jar") ]
        
        for cp_path in ADD_PATHS:
            self.compiler.add_classpath(cp_path)
    
    def add_classpath(self, classpath: str):
        self.compiler.add_classpath(classpath)
    
    def javac(self, input_file_path: str, dest_dir: str = None):
        input_file_path = os.path.realpath(input_file_path)
        dest_dir = os.path.realpath(dest_dir) if dest_dir is not None else None
        
        if dest_dir is None: 
            dest_dir = str(Path(input_file_path).parent)
        
        self.compiler.add_classpath(dest_dir)
        
        errno = self.compiler.compile(input_file_path, dest_dir=dest_dir)
        assert errno == 0, f"javac failed with {errno}"

# example code
'''
    CP_DIR="../../../asc-challenge-002-jenkins-cp/"
    builder = CPBuilder(CP_DIR)
    builder.javac(os.path.join(CP_DIR, "container_scripts/PipelineCommandUtilPovRunner.java"))
'''

argparser = argparse.ArgumentParser()
argparser.add_argument("input_file", help="java file to compile")
argparser.add_argument("-d", "--dest_dir", help="destination directory")
argparser.add_argument("-c", "--challenge_path", help="challenge problem directory")
argparser.add_argument("-cp", "--classpath", help="additional classpath")

if __name__ == "__main__":
    args = argparser.parse_args()
    input_file = args.input_file
    dest_dir = args.dest_dir
    classpath = args.classpath.split(":") if args.classpath is not None else []
    
    if args.challenge_path is not None:
        CP_DIR = args.challenge_path
    elif os.getenv("CP_DIR") is not None:
        CP_DIR = os.getenv("CP_DIR")
    else:
        raise Exception("CP_DIR environment variable is not set")

    builder = CPBuilder(CP_DIR)
    for cp in classpath:
        builder.add_classpath(cp)
    builder.javac(input_file, dest_dir=dest_dir)
