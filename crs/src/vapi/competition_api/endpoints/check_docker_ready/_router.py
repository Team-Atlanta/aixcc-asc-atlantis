from fastapi import APIRouter
from structlog.stdlib import get_logger

from competition_api.models.check_docker_ready import CheckDockerReadyResponse

from .check_docker_ready import check_docker_ready

router = APIRouter()

LOGGER = get_logger(__name__)


@router.get("/check_docker_ready/{cp_name}")
async def check_docker_ready_endpoint(
    cp_name: str,
) -> CheckDockerReadyResponse:
    return await check_docker_ready(cp_name)
