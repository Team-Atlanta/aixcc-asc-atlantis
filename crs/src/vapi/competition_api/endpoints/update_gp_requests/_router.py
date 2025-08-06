from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection
from fastapi import APIRouter, Depends
from structlog.stdlib import get_logger

from competition_api.db import db_session
from competition_api.models.health import HealthResponse

from .update_gp_requests import update_gp_requests

router = APIRouter()

LOGGER = get_logger(__name__)


@router.post("/update_gp_requests/")
async def check_status() -> HealthResponse:
    async with db_session() as db:
        return await update_gp_requests(db)
