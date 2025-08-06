import javalang

class JavaPrinter:
    def __init__(self):
        self.indent = 0
        return 
    
    def add_indent(self):
        self.indent += 1
        return
    
    def remove_indent(self):
        self.indent -= 1
        return

    def print_indent(self):
        print("  " * self.indent, end="")

    def primitive(self, c):
        if isinstance(c, str):
            return f'"{c}"'
        else:
            return f'{c}'
    
    def _println(self, c):
        self.print_indent()
        print(c)
        return
    
    def _print(self, c):
        self.print_indent()
        print(c, end="")
        return
    
    def is_primitive(self, java_obj):
        return isinstance(java_obj, (int, float, str, bool))

    def print(self, java_obj):
        if isinstance(java_obj, list):
            self._println("[")
            self.add_indent()
            for n in java_obj:
                self.print(n)
            self.remove_indent()
            self._println("]")
        elif isinstance(java_obj, dict):
            self._println("{")
            self.add_indent()
            for k, v in java_obj.items():
                if self.is_primitive(v):
                    self._println(f'"{k}": {self.primitive(v)}')
                else:
                    self._print(f'"{k}": ')
                    self.print(v)
            self.remove_indent()
            self._println("}")
        elif isinstance(java_obj, set):
            self._println("[")
            self.add_indent()
            for n in java_obj:
                self.print(n)
            self.remove_indent()
            self._println("]")
        elif isinstance(java_obj, javalang.tree.Node):
            for attr in java_obj.attrs:
                v = getattr(java_obj, attr) 
                if v is None:
                    continue
                self.add_indent()
                if self.is_primitive(v):
                    self._println(f'"{attr}": {self.primitive(v)}')
                else:
                    self._println(f'"{attr}": ')
                    self.print(v)
                self.remove_indent()

        else:
            self._println(java_obj)

        return
        
