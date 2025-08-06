import asyncio

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncConnection
from structlog.contextvars import bind_contextvars, clear_contextvars
from structlog.stdlib import get_logger
from vyper import v

from competition_api.audit import get_auditor
from competition_api.db.precompilation import PrecompilationCommitHint
from competition_api.models.precompilation import PrecompileRequest, PrecompileResponse
from competition_api.tasks import TaskRunner

LOGGER = get_logger(__name__)


async def precompile(
    body: PrecompileRequest,
    db: AsyncConnection,
) -> PrecompileResponse:
    clear_contextvars()
    auditor = get_auditor()

    bind_contextvars(cp_name=body.cp_name, endpoint="precompile")
    auditor.push_context(cp_name=body.cp_name)

    if v.get_bool("mock_mode"):
        return PrecompileResponse(status="ok")

    if body.commit_hints:
        await db.execute(
            insert(PrecompilationCommitHint),
            [
                {
                    "cp_name": body.cp_name,
                    "commit_sha1": hint.lower(),
                }
                for hint in body.commit_hints
            ],
        )
        await db.commit()

    asyncio.create_task(TaskRunner(body.cp_name, auditor).precompile())

    return PrecompileResponse(status="ok")
