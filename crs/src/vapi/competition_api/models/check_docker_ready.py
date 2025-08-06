from pydantic import BaseModel


class CheckDockerReadyResponse(BaseModel):
    status: str

    model_config = {"json_schema_extra": {"examples": [{"status": "ok"}]}}
