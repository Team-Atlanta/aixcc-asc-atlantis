from fastapi import APIRouter
from structlog.stdlib import get_logger

from competition_api.db import db_session
from competition_api.models.precompilation import PrecompileRequest, PrecompileResponse

from .precompile import precompile

router = APIRouter()

LOGGER = get_logger(__name__)


@router.post("/precompile/")
async def start_precompile(
    body: PrecompileRequest,
) -> PrecompileResponse:
    async with db_session() as db:
        return await precompile(body, db)
