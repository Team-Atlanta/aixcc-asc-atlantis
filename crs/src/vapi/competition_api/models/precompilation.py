from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

SHA1_REGEX = r"[0-9a-f]{40}"
SHA1_CONSTRAINTS = StringConstraints(
    strip_whitespace=True,
    to_upper=True,
    pattern=SHA1_REGEX,
    max_length=40,
    min_length=40,
)


class PrecompileRequest(BaseModel):
    cp_name: str
    commit_hints: list[Annotated[str, SHA1_CONSTRAINTS]] = Field(default_factory=list)

class PrecompileResponse(BaseModel):
    status: str

    model_config = {"json_schema_extra": {"examples": [{"status": "ok"}]}}
