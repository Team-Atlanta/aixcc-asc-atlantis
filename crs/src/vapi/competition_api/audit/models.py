from datetime import UTC, datetime
from typing import Union
from uuid import UUID

from pydantic import BaseModel, Field

from competition_api.models.types import FeedbackStatus

from .types import (
    Disposition,
    EventType,
    GPSubmissionFailReason,
    TimeoutContext,
    VDSubmissionFailReason,
)


class TimeoutEvent(BaseModel):
    """One of the tests timed out before completing."""

    disposition: Disposition = Disposition.BAD

    cp_name: str
    context: TimeoutContext

    vd_uuid: UUID | None = None
    gp_uuid: UUID | None = None
    cpv_uuid: UUID | None = None


class MockResponseEvent(BaseModel):
    """Emitted if the cAPI is operating in mock mode."""

    mock_content: bool = True
    description: str = "Mock content returned to client"


class GPSubmissionEvent(BaseModel):
    """A CRS has submitted a generated patch."""

    gp_uuid: UUID
    submitted_cpv_uuid: UUID
    patch_sha256: str


class GPEvent(BaseModel):
    vd_uuid: UUID
    cp_name: str
    gp_uuid: UUID
    cpv_uuid: UUID


class GPSubmissionDuplicateCPVEvent(GPEvent):
    """A CRS submitted another GP for a CPV they've already submitted for"""


class GPPatchBuiltEvent(GPEvent):
    """A CP was built successfully with a patch"""

    disposition: Disposition = Disposition.GOOD


class GPFunctionalTestsPass(GPEvent):
    """A CP's functional tests passed after the patch was applied"""

    disposition: Disposition = Disposition.GOOD


class GPSanitizerDidNotFire(GPEvent):
    """After the GP's patch, the vulnerability no longer existed"""

    disposition: Disposition = Disposition.GOOD


class GPSubmissionFailEvent(GPEvent):
    """The generated patch failed at a necessary part of the process."""

    disposition: Disposition = Disposition.BAD
    feedback_status: FeedbackStatus = FeedbackStatus.NOT_ACCEPTED

    reason: GPSubmissionFailReason


class GPSubmissionSuccessEvent(GPEvent):
    """The GP passed all tests."""

    disposition: Disposition = Disposition.GOOD
    feedback_status: FeedbackStatus = FeedbackStatus.ACCEPTED


class VDEvent(BaseModel):
    """All events associated with the vulnerability discovery lifecycle will have
    these two fields."""

    vd_uuid: UUID
    cp_name: str


class VDSubmissionEvent(VDEvent):
    """A CRS has submitted a vulnerability discovery."""

    harness: str
    pov_blob_sha256: str


class VDSubmissionFailEvent(VDEvent):
    """The vulnerability discovery failed one of the tests."""

    disposition: Disposition = Disposition.BAD
    feedback_status: FeedbackStatus = FeedbackStatus.NOT_ACCEPTED

    reason: VDSubmissionFailReason


class VDSubmissionSuccessEvent(VDEvent):
    """The vulnerability discovery has passed all tests."""

    disposition: Disposition = Disposition.GOOD
    feedback_status: FeedbackStatus = FeedbackStatus.ACCEPTED


class VDSanitizerResultEvent(VDEvent):
    """The vulnerability discovery's input blob has been passed to the challenge
    problem at a particular commit.  This event contains the results of that test,
    including what sanitizers fired.

    We include the disposition field to indicate whether the result is good or
    bad."""

    source: str
    commit_sha: str
    disposition: Disposition
    sanitizers_triggered: list[str]


class EventWrapper(BaseModel):
    schema_version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: EventType
    event: Union[
        GPFunctionalTestsPass,
        GPPatchBuiltEvent,
        GPSanitizerDidNotFire,
        GPSubmissionDuplicateCPVEvent,
        GPSubmissionEvent,
        GPSubmissionFailEvent,
        GPSubmissionSuccessEvent,
        MockResponseEvent,
        TimeoutEvent,
        VDSanitizerResultEvent,
        VDSubmissionEvent,
        VDSubmissionFailEvent,
        VDSubmissionSuccessEvent,
    ]
