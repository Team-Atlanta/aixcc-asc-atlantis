from base64 import b64decode

from structlog.stdlib import get_logger
from vyper import v

from competition_api.cp_registry import CPRegistry
from competition_api.cp_workspace import CPWorkspace
from competition_api.models.check_docker_ready import CheckDockerReadyResponse

LOGGER = get_logger(__name__)


async def check_docker_ready(
    cp_name: str,
) -> CheckDockerReadyResponse:
    if v.get_bool("mock_mode"):
        return CheckDockerReadyResponse(status="ok")

    # base-64-encoded because FastAPI chokes on percent-encoded slashes in URLs
    # (ref. https://github.com/tiangolo/fastapi/issues/791), and I'm not
    # willing to gamble that the real CP names won't have any slashes
    try:
        cp_name = b64decode(cp_name.encode('utf-8')).decode('utf-8')
    except Exception:
        return CheckDockerReadyResponse(status="unknown cp")

    await LOGGER.ainfo("CP name = %s", repr(cp_name))

    if CPRegistry.instance().get(cp_name) is None:
        return CheckDockerReadyResponse(status="unknown cp")

    if await CPWorkspace.is_docker_ready(cp_name):
        return CheckDockerReadyResponse(status="ok")
    else:
        return CheckDockerReadyResponse(status="no")
