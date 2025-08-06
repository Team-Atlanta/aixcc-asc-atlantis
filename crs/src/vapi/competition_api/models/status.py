from pydantic import UUID4, BaseModel, Field

from competition_api.models.types import FeedbackStatus


class VDStatusResponse(BaseModel):
    status: FeedbackStatus
    cp_name: str
    commit_sha1: str | None
    sanitizer: str | None
    harness: str
    cpv_uuid: UUID4 | None = Field(
        description="This is only provided if the VDS is accepted."
    )


class GPStatusResponse(BaseModel):
    status: FeedbackStatus
    cpv_uuid: UUID4


class StatusResponse(BaseModel):
    vd_submissions: dict[UUID4, VDStatusResponse]
    gp_submissions: dict[UUID4, GPStatusResponse]
