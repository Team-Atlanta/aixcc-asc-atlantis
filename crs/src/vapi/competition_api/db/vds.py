from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy
from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from competition_api.db.common import Base
from competition_api.models.types import FeedbackStatus, CheckingStatus, VDDBSubmissionFailReason

if TYPE_CHECKING:
    from competition_api.db.gp import GeneratedPatch

TABLENAME = "vulnerability_discovery"


class VulnerabilityDiscovery(Base):
    __tablename__ = TABLENAME

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    remote_uuid: Mapped[UUID] = mapped_column(Uuid, nullable=True)

    cpv_uuid: Mapped[UUID] = mapped_column(Uuid, index=True, unique=True, nullable=True)
    cp_name: Mapped[str] = mapped_column(String, nullable=False)

    pou_commit_sha1: Mapped[str] = mapped_column(String, nullable=True)
    pou_sanitizer: Mapped[str] = mapped_column(String, nullable=True)
    pov_harness: Mapped[str] = mapped_column(String, nullable=False)
    pov_data_sha256: Mapped[str] = mapped_column(String, nullable=False)

    # comma-separated sha1 commit hashes
    pou_commit_hints: Mapped[str] = mapped_column(String, nullable=False)

    status: Mapped[FeedbackStatus] = mapped_column(
        sqlalchemy.Enum(FeedbackStatus, native_enum=False),
        default=FeedbackStatus.PENDING,
    )
    last_remote_status_update_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    checking_status: Mapped[CheckingStatus] = mapped_column(
        sqlalchemy.Enum(CheckingStatus, native_enum=False),
        default=CheckingStatus.BEGINNING,
    )
    fail_reason: Mapped[VDDBSubmissionFailReason] = mapped_column(
        sqlalchemy.Enum(VDDBSubmissionFailReason, native_enum=False),
        default=VDDBSubmissionFailReason.NOT_REJECTED,
    )

    gp: Mapped["GeneratedPatch"] = (  # noqa: F821 # sqlalchemy resolves this
        relationship(back_populates="vds")
    )

    def __repr__(self):
        return (
            f"VulnerabilityDiscovery<{self.cp_name},"
            f"POU<{self.pou_sanitizer}@{self.pou_commit_sha1}>,"
            f"POV<{self.pov_harness}>>"
        )

    def __str__(self):
        return repr(self)
