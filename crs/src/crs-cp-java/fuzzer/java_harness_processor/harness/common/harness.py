
class Harness: 
    def __init__(self):   
        self.file_path = None
        self.class_name = None
        self.source_code = None
        self.arguments = []  
        self.target_package = None
        self.target_class = None
        self.target_method = None
    
    def add_argument(self, arg: dict):
        self.arguments.append(arg)