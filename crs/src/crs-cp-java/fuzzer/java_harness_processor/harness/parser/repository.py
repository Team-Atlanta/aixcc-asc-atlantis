import os
import re

class JavaRepository:
    def __init__(self, cp_path):
        self.project_path = cp_path
        self.src_path = os.path.join(self.project_path, 'src')
        self.files = []
        self._include = [f'\.java$']
        self.escaped_path = re.escape(self.project_path)
        self._exclude = [f'.readonly']
        self.__is_cached = False
    
    def add_include(self, pattern):
        self._include.append(pattern)

    def add_exclude(self, pattern):
        self._exclude.append(pattern)

    def find_file_by_name(self, name) -> list:
        self.__cache() 
        res = []
        for file in self.files:
            if os.path.basename(file) == name:
                res.append(file)
                
        return res
    
    def path(self, filepath):
        return os.path.join(self.project_path, filepath)

    def read(self, file_path):
        with open(self.path(file_path), 'r') as f:
            return f.read()
    
    
    def __cache(self):
        if self.__is_cached:
            return
        
        for root, dirs, files in os.walk(self.src_path):
            for file in files:
                path = os.path.join(root, file)
                if self.__filter(path):
                    self.files.append(path)

        self.__is_cached = True
        
    def __filter(self, file_path):
        relative_path = os.path.relpath(file_path, self.project_path)
        for f in self._exclude:
            if relative_path.startswith(f):
                return False
        
        for f in self._include:
            if re.search(f, file_path):
                return True
            
        return False

class JenkinsRepository(JavaRepository):
    def __init__(self, cp_path):
        super().__init__(cp_path)
        self._exclude = [f'.readonly', f'src/jenkins', f'src/plugins']
        self.__is_cached = False
    