import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection
from structlog.stdlib import get_logger
from vyper import v

from competition_api.capi_client import CapiClient
from competition_api.db import VulnerabilityDiscovery, GeneratedPatch
from competition_api.models.status import GPStatusResponse, StatusResponse, VDStatusResponse
from competition_api.models.types import FeedbackStatus
from competition_api.tasks import CapiCommTaskRunner

LOGGER = get_logger(__name__)


async def get_status(
    db: AsyncConnection,
) -> StatusResponse:
    if v.get_bool("mock_mode"):
        return StatusResponse(
            vd_submissions={},
            gp_submissions={},
        )

    async with CapiClient() as client:
        await CapiCommTaskRunner(client).update_all_statuses(db, update_vds=True, update_gps=True, throttling=False)

    vd_submissions = {}

    result = (
        await db.execute(
            select(VulnerabilityDiscovery)
        )
    ).fetchall()
    for (vds_row,) in result:
        vd_submissions[vds_row.id] = VDStatusResponse(
            status=vds_row.status,
            cp_name=vds_row.cp_name,
            commit_sha1=vds_row.pou_commit_sha1,
            sanitizer=vds_row.pou_sanitizer,
            harness=vds_row.pov_harness,
            cpv_uuid=vds_row.cpv_uuid,
        )

    gp_submissions = {}

    result = (
        await db.execute(
            select(GeneratedPatch)
            .join(VulnerabilityDiscovery)
        )
    ).fetchall()
    for (gp_row,) in result:
        gp_submissions[gp_row.id] = GPStatusResponse(
            status=gp_row.status,
            cpv_uuid=gp_row.cpv_uuid,
        )

    return StatusResponse(
        vd_submissions=vd_submissions,
        gp_submissions=gp_submissions,
    )
