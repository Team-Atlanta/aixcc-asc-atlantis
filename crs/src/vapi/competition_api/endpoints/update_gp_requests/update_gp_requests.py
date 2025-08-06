import asyncio

from sqlalchemy.ext.asyncio import AsyncConnection
from structlog.stdlib import get_logger
from vyper import v

from competition_api.models.health import HealthResponse
from competition_api.tasks import UpdateGpRequestsTaskRunner

LOGGER = get_logger(__name__)


async def update_gp_requests(
    db: AsyncConnection,
) -> HealthResponse:
    if v.get_bool("mock_mode"):
        return

    asyncio.create_task(UpdateGpRequestsTaskRunner().update_gp_requests(None))

    return HealthResponse(status="ok")
