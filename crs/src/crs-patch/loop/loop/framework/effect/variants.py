from dataclasses import dataclass


@dataclass
class WrongPatchEffect:
    diff: str


@dataclass
class DumbEffect:
    diff: str
    stderr: str


@dataclass
class CompilableEffect: ...


@dataclass
class VulnerableEffect:
    run_pov_stdout: str


@dataclass
class SoundEffect: ...


@dataclass
class WrongFormatEffect:
    error: Exception


@dataclass
class EmptyEffect: ...


@dataclass
class UnknownErrorEffect:
    error: Exception
