from uuid import UUID, uuid4

import sqlalchemy
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from competition_api.db.common import Base

TABLENAME = "precompilation_commit_hint"


class PrecompilationCommitHint(Base):
    __tablename__ = TABLENAME

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    cp_name: Mapped[str] = mapped_column(String, nullable=False)
    commit_sha1: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self):
        return f"PrecompilationCommitHint<{self.cp_name},{self.commit_sha1}>"

    def __str__(self):
        return repr(self)
