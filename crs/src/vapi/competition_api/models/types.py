from enum import Enum, unique
from typing import Annotated

from fastapi import Path
from pydantic import UUID4

UUIDPathParameter = Annotated[
    UUID4, Path(description="Example: 744a8ead-9ebc-40cd-9f96-8edf187868fa")
]


@unique
class FeedbackStatus(Enum):
    ACCEPTED = "accepted"
    NOT_ACCEPTED = "rejected"
    PENDING = "pending"


@unique
class CheckingStatus(Enum):
    BEGINNING = "beginning"
    READY_TO_SUBMIT_TO_CAPI = "ready_to_submit_to_capi"
    DONE = "done"  # either rejected without submitting, or response received from CAPI


@unique
class VDDBSubmissionFailReason(Enum):
    NOT_REJECTED = "not_rejected"  # default value
    CP_NOT_IN_CP_ROOT_FOLDER = "cp_not_in_cp_root_folder"
    COMMIT_CHECKOUT_FAILED = "commit_checkout_failed"
    HEAD_BUILD_FAILED = "head_build_failed"
    DUPLICATE_COMMIT = "duplicate_commit"
    SANITIZER_DID_NOT_FIRE_AT_HEAD = "sanitizer_did_not_fire_at_head"
    ALL_SANITIZERS_ALSO_FIRED_AT_INITIAL = "all_sanitizers_also_fired_at_initial"
    BISECTION_FAILED = "bisection failed"
    CAPI_REJECTED = "capi_rejected"
    GENERAL_EXCEPTION = "general_exception"
