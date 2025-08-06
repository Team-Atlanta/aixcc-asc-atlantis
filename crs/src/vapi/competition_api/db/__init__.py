# all models must be imported and added to __all__ for migration generation to work

from .gp import GeneratedPatch
from .precompilation import PrecompilationCommitHint
from .session import db_session, fastapi_get_db
from .vds import VulnerabilityDiscovery

__all__ = [
    "VulnerabilityDiscovery",
    "GeneratedPatch",
    "PrecompilationCommitHint",
    "db_session",
    "fastapi_get_db",
]
