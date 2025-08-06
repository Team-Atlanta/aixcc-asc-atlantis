import os
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

from typing_extensions import override

from .code_analyzer import CodeAnalyzer, CCodeAnalyzer, PythonCodeAnalyzer, JavaCodeAnalyzer
from .code_writer import CodeWriter, CCodeWriter, PythonCodeWriter, JavaCodeWriter
from .challenge import BuildInfo

def get_language(file: Path) -> "Language":
    # TODO: Determine C code analyzer or C++ code analyzer for .h files
    #       Currently, C code analyzer is used for .h files
    if file.suffix == ".c":
        return C()
    elif file.suffix in [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"]:
        return Cpp()
    elif file.suffix == ".h":
        # TODO: Introduce H() class because there's no compile command for .h files
        return C()
    elif file.suffix == ".py":
        return Python()
    elif file.suffix == ".java":
        return Java()
    else:
        raise ValueError(f'invalid file: {file}')

class Language(ABC):
    @abstractmethod
    def get_analyzer(self, file: Path, build_info: Optional[BuildInfo] = None) -> CodeAnalyzer:
        pass

    @abstractmethod
    def get_writer(self, line: Optional[str]=None) -> CodeWriter:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def stop(self) -> List[str]:
        pass

class C(Language):
    @override
    def get_analyzer(self, file: Path, build_info: Optional[BuildInfo] = None) -> CodeAnalyzer:
        compile_args = self._extract_compile_args(file, build_info) if build_info else []
        return CCodeAnalyzer(file, compile_args)

    @override
    def get_writer(self, line: Optional[str]=None) -> CodeWriter:
        return CCodeWriter(line)

    @override
    @property
    def name(self) -> str:
        return "C"

    @override
    @property
    def stop(self) -> List[str]:
        # return ["int main(", "void main(", "%%"]
        # Don't know why ZeroShot used the above stop words
        return []

    def _extract_compile_args(self, file: Path, build_info: BuildInfo):
        def find_target_commands(compile_commands, relpath):
            while len(relpath) > 0:
                target_cmds = [cmd for cmd in compile_commands if cmd['file'].endswith(relpath)]
                if target_cmds:
                    return target_cmds
                relpath = os.path.sep.join(relpath.split(os.path.sep)[1:])
            return []

        def extract_options(arguments, build_info):
            args = []
            for arg in arguments:
                if arg.startswith("-D"):
                    args.append(arg)
                elif arg.startswith("-I"):
                    include_path = Path(arg[2:])
                    if include_path.is_absolute():
                        include_path = include_path.relative_to(build_info.guest_build_dir)
                    args.append(f"-I{build_info.host_build_dir / include_path}")
            return args

        relpath = os.path.relpath(str(file), build_info.host_build_dir)
        target_cmds = find_target_commands(build_info.compile_commands, relpath)

        if target_cmds:
            arguments = target_cmds[0]['arguments']
            args = extract_options(arguments, build_info)
            return args

        return []

class Cpp(C):
    @override
    @property
    def name(self) -> str:
        return "C++"

class Python(Language):
    @override
    def get_analyzer(self, file: Path, build_info: Optional[BuildInfo] = None) -> CodeAnalyzer:
        return PythonCodeAnalyzer(file)

    @override
    def get_writer(self, line: Optional[str]=None) -> CodeWriter:
        return PythonCodeWriter(line)

    @override
    @property
    def name(self) -> str:
        return "Python"

    @override
    @property
    def stop(self) -> List[str]:
        return ["@app", "@bp"]

class Java(Language):
    @override
    def get_analyzer(self, file: Path, build_info: Optional[BuildInfo] = None) -> CodeAnalyzer:
        return JavaCodeAnalyzer(file)

    @override
    def get_writer(self, line: Optional[str]=None) -> CodeWriter:
        return JavaCodeWriter(line)

    @override
    @property
    def name(self) -> str:
        return "Java"

    @override
    @property
    def stop(self) -> List[str]:
        return ["package", "import", "public class"]
