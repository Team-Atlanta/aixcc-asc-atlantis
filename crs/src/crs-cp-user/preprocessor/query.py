#!/usr/bin/env python3
# https://tree-sitter.github.io/tree-sitter/playground
import os
from pathlib import Path
from dataclasses import dataclass
from tree_sitter import Language, Parser
import tree_sitter_c

@dataclass
class FunctionSummary:
    filename: str
    signature: str
    name: str
    start: str
    start_line: int
    definition: str

class CodeQuery:
    _captures = []
    _i = 0
    _parsed = []
    _src = bytes("", 'utf-8')
    _tree = None
    _filename = ""
    _parser = None

    def __init__(self):
        raise NotImplementedError()

    def _capture_functions(self):
        raise NotImplementedError()

    def _parse_captures(self):
        raise NotImplementedError()
        
    def _get_summary_from_parse(self, parse_ctx):
        raise NotImplementedError()
    
    # Given a capture by its index _i, return its string and inc _i, else None
    def _get_expected_capture(self, expect):
        if self._i < len(self._captures) and self._captures[self._i][1] == expect:
            ret = self._captures[self._i][0]
            self._i += 1
        else:
            ret = None
        return ret

    # Given a tree-sitter node, find its code text from the source file
    def _get_code_text(self, node):
        return str(self._src[node.start_byte:node.end_byte], 'utf-8')

    def _get_start_line(self, start_byte):
        """ Zero indexed
        """
        return self._src.count(bytes('\n', 'utf-8'), 0, start_byte)
        
    def set_file(self, filename):
        with open(filename) as f: self._src = bytes(f.read(), 'utf-8')
        self._tree = self._parser.parse(self._src)
        self._filename = filename

    # Get all function signatures from given source code file
    def get_function_signatures(self):
        all_sigs = []
        self._capture_functions()
        self._parse_captures()
        for par in self._parsed:
            s = self._get_summary_from_parse(par)
            if s is not None:
                all_sigs.append(s)
        return all_sigs

@dataclass
class CParseCtx:
    defn: str
    ty: str
    decl: str

class CCodeQuery(CodeQuery):
    def __init__(self, filename):
        self._language = Language(tree_sitter_c.language())
        self._parser = Parser(self._language)
        self.set_file(filename)
        
    # Modify self._captures to collect tree-sitter queries
    def _capture_functions(self):
        query = self._language.query("""
        (function_definition
            type: (_) @type
            declarator: (_) @declarator
        ) @function
        """)
        self._captures = query.captures(self._tree.root_node)

    # Modify self._parsed to collect CParseCtx for each capture
    def _parse_captures(self):
        self._i = 0
        self._parsed = []
        while self._i < len(self._captures):
            defn = self._get_expected_capture('function')
            ty = self._get_expected_capture('type')
            decl = self._get_expected_capture('declarator')
            self._parsed.append(CParseCtx(defn, ty, decl))

    # Extract the 'declarator: identifier' from top-level declarator node
    def __get_function_identifier(self, decl_node):
        if decl_node.type == "identifier":
            return self._get_code_text(decl_node)
        for child in decl_node.children:
            ret = self.__get_function_identifier(child) 
            if ret is not None:
                return ret
        return None
            
    # Return FunctionSummary if parse_ctx can be transformed, else None
    def _get_summary_from_parse(self, parse_ctx):
        definition = self._get_code_text(parse_ctx.defn)
        typ = self._get_code_text(parse_ctx.ty)
        declarator = self._get_code_text(parse_ctx.decl)
        signature = "%s %s" % (typ, declarator)
        function_name = self.__get_function_identifier(parse_ctx.decl)
        assert(function_name is not None)
        start = parse_ctx.defn.start_byte
        start_line = parse_ctx.defn.start_point[0]
        return FunctionSummary(self._filename, signature, function_name, start, start_line, definition)


# if __name__ == '__main__':
#     queryer = CCodeQuery("/home/andrew/benchmark/c/cqe/CROMU_00041/src/stdlib.c")
#     summaries = queryer.get_function_signatures()
#     for summary in summaries:
#         print(summary.signature)
