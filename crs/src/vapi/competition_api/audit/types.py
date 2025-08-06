from enum import Enum


class Disposition(Enum):
    """Some of our events do not change the FeedbackStatus, but have a bearing on the
    CRS's score."""

    GOOD = "good"
    BAD = "bad"


class GPSubmissionFailReason(Enum):
    INVALID_VDS_ID = "invalid_vds_id"
    FUNCTIONAL_TESTS_FAILED = "functional_tests_failed"
    MALFORMED_PATCH_FILE = "malformed_patch_file"
    PATCHED_DISALLOWED_FILE_EXTENSION = "patched_disallowed_file_extension"
    PATCH_FAILED_APPLY_OR_BUILD = "patch_failed_apply_or_build"
    RUN_POV_FAILED = "run_pov_failed"
    SANITIZER_FIRED_AFTER_PATCH = "sanitizer_fired_after_patch"
    CAPI_REJECTED = "capi_rejected"
    GENERAL_EXCEPTION = "general_exception"


class VDSubmissionFailReason(Enum):
    CP_NOT_IN_CP_ROOT_FOLDER = "cp_not_in_cp_root_folder"
    COMMIT_CHECKOUT_FAILED = "commit_checkout_failed"
    HEAD_BUILD_FAILED = "head_build_failed"
    DUPLICATE_COMMIT = "duplicate_commit"
    RUN_POV_FAILED = "run_pov_failed"
    SANITIZER_DID_NOT_FIRE_AT_HEAD = "sanitizer_did_not_fire_at_head"
    ALL_SANITIZERS_ALSO_FIRED_AT_INITIAL = "all_sanitizers_also_fired_at_initial"
    BISECTION_FAILED = "bisection failed"
    CAPI_REJECTED = "capi_rejected"
    GENERAL_EXCEPTION = "general_exception"


class TimeoutContext(Enum):
    BUILD = "build"
    CHECK_SANITIZERS = "check_sanitizers"
    RUN_FUNCTIONAL_TESTS = "run_functional_tests"


class EventType(Enum):
    DUPLICATE_GP_SUBMISSION_FOR_CPV_UUID = "duplicate_gp_submission_for_cpv_uuid"
    GP_SUBMISSION = "gp_submission"
    GP_SUBMISSION_FAIL = "gp_submission_failed"
    GP_PATCH_BUILT = "gp_patch_built"
    GP_FUNCTIONAL_TESTS_PASS = "gp_functional_tests_pass"
    GP_SANITIZER_DID_NOT_FIRE = "gp_sanitizer_did_not_fire"
    GP_SUBMISSION_SUCCESS = "gp_submission_success"
    TIMEOUT = "timeout"
    VD_SANITIZER_RESULT = "vd_sanitizer_result"
    VD_SUBMISSION = "vd_submission"
    VD_SUBMISSION_FAIL = "vd_submission_failed"
    VD_SUBMISSION_SUCCESS = "vd_submission_success"
    MOCK_RESPONSE = "mock_response"
