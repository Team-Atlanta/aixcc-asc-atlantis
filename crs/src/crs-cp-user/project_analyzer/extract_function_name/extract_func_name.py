import clang.cindex

clang_library_path = '/usr/lib/llvm-10/lib/libclang.so'
clang.cindex.Config.set_library_file(clang_library_path)

def extract_function_names(file_path):
    index = clang.cindex.Index.create()
    translation_unit = index.parse(file_path)
    
    def visitor(node, func_names):
        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            func_names.append(node.spelling)
        for child in node.get_children():
            visitor(child, func_names)
    
    function_names = []
    visitor(translation_unit.cursor, function_names)
    return function_names

if __name__ == "__main__":
    file_path = '/home/yizhuo/linux/fs/fs_struct.c'
    function_names = extract_function_names(file_path)
    print("Function names found:")
    for name in function_names:
        print(name)
