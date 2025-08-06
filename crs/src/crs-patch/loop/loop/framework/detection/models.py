import re
import tomllib
from pathlib import Path
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, BeforeValidator

PathStr = Annotated[Path, AfterValidator(lambda x: Path(x))]
CommitStr = Annotated[
    str, BeforeValidator(lambda x: x if re.match(r"^[a-f0-9]{40}$", x) else None)
]


class Detection(BaseModel):
    cp_name: str
    blob_file: PathStr
    harness_id: str
    sanitizer_id: str
    bug_introduce_commit: CommitStr

    @classmethod
    def from_toml(cls, content_or_path: str | Path) -> Self:
        match content_or_path:
            case str():
                content = content_or_path
            case Path():
                content = content_or_path.read_text()

        return cls(**tomllib.loads(content))
