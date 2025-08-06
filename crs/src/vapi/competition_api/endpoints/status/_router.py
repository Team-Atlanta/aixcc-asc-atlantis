from uuid import UUID

from fastapi import APIRouter, Depends
from structlog.stdlib import get_logger

from competition_api.db import db_session
from competition_api.models.status import StatusResponse

from .status import get_status

router = APIRouter()

LOGGER = get_logger(__name__)


@router.get("/status/")
async def check_status() -> StatusResponse:
    async with db_session() as db:
        return await get_status(db)
