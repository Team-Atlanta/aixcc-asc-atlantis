import javalang


class JavaCode:
    def __init__(self):
        self.source_code = ""
        self.filepath = ""
        self.children = []
        self.classes = {}
        self.package = ""
        self.obj = None

    def from_file(filepath):
        with open(filepath, 'r') as f:
            source_code = f.read()
        java_code = JavaCode.from_str(source_code)
        java_code.filepath = filepath
        return java_code

    def from_str(source_code):
        self = JavaCode()
        self.source_code = source_code
        self.obj = javalang.parse.parse(source_code)
        if self.obj.package is not None:
            self.package = self.obj.package.name if self.obj.package.name else ""

        for path, java_class in self.obj.filter(javalang.tree.ClassDeclaration):
            self.classes[java_class.name] = JavaClass.from_obj(java_class)

        return self


class JavaClass:
    def __init__(self):
        self.obj = None
        self.name = ""
        self.body = ""
        self.package = ""
        self.methods = {}
    
    def from_obj(java_class: javalang.tree.ClassDeclaration):
        self = JavaClass()
        self.obj = java_class
        self.name = self.obj.name
        self.body = self.obj.body
        for method in self.obj.methods:
            self.methods[method.name] = JavaMethod.from_obj(method)
            self.methods[method.name].parent_class = self
            
        return self
    
    
class JavaMethod:
    def __init__(self):
        self.obj = None
        self.name = ""
        self.invocations = []
        self.values = {}
        self.body = None
        self.parent_class = None

    def from_obj(method: javalang.tree.MethodDeclaration):
        self = JavaMethod()
        self.obj = method
        self.name = self.obj.name
        
        self.body = self.obj.body
        self.cache()
        return self
    
    # caching in body such as invocation code or values
    def cache(self):
        for path, node in self.obj.filter(javalang.tree.MethodInvocation):
            self.invocations.append(node)
            
