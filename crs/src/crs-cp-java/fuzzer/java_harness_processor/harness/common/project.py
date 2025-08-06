import yaml
import os

class Project(object):
    def __init__(self, project_path):
        self.project_path: str = project_path
        with open(os.path.join(project_path, 'project.yaml'), 'r') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)
        
        self.cp_name = self.config.get('cp_name', "")
        self.language = self.config.get('language', "")
        self.cp_sources = self.config.get('cp_sources', {})
        self.docker_image = self.config.get('docker_image', "")
        self.harnesses = self.config.get('harnesses', {})
        self.sanitizers = self.config.get('sanitizers', {})
