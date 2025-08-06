import os
from pathlib import Path

from structlog.stdlib import get_logger
from vyper import v

LOGGER = get_logger(__name__)


def generate_config():
    path = v.get('database.path')
    if path == 'memory':
        v.set("database.url", "sqlite+aiosqlite://")
        v.set("database.synchronous_url", "sqlite://")
    else:
        if path is None:
            Path('/db').mkdir(exist_ok=True)
            path = "/db/sqlite.db"
        path = Path(path).resolve()
        v.set("database.url", f"sqlite+aiosqlite:///{path.resolve()}")
        v.set("database.synchronous_url", f"sqlite:///{path.resolve()}")


def init_vyper():
    v.set_env_prefix("VAPI")
    v.automatic_env()

    generate_config()

    v.set_default("scoring.reject_duplicate_vds", True)
