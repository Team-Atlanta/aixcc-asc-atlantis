from base64 import b64encode
from contextlib import asynccontextmanager, AbstractAsyncContextManager
import enum
import json
import os
import traceback

import aiohttp
from structlog.stdlib import get_logger
from vyper import v

from competition_api.models.types import FeedbackStatus
from competition_api.models.vds import VDSubmission
from competition_api.models.gp import GPSubmission


LOGGER = get_logger(__name__)


v.set_default("capi_username", "00000000-0000-0000-0000-000000000000")
v.set_default("capi_password", "secret")


class CapiSubmissionResult(enum.Enum):
    ACCEPTED_PENDING = enum.auto()
    REJECTED = enum.auto()
    ERROR_TRY_AGAIN = enum.auto()


class CapiClient(AbstractAsyncContextManager):
    def __init__(self):
        self.hostname = os.environ['AIXCC_API_HOSTNAME'].rstrip('/')
        self.auth = aiohttp.BasicAuth(v.get('capi_username'), v.get('capi_password'))
        self._active_session = None
        self.active_session = None

    async def __aenter__(self):
        self._active_session = aiohttp.ClientSession()
        self.active_session = await self._active_session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._active_session.__aexit__(exc_type, exc, tb)
        self._active_session = None
        self.active_session = None

    @asynccontextmanager
    async def _do_get(self, url_part: str):
        if self.active_session is None:
            raise RuntimeError('Must perform requests within CapiClient `async with` context')

        url = self.hostname + url_part

        await LOGGER.adebug("CAPI GET %s", url)

        try:
            async with self.active_session.get(url, auth=self.auth) as response:
                await LOGGER.adebug("CAPI response: %d %s", response.status, await response.text())

                yield response
        except Exception:
            await LOGGER.adebug(f"Exception while contacting CAPI:\n{traceback.format_exc()}")
            raise

    @asynccontextmanager
    async def _do_post(self, url_part: str, json_payload: dict):
        if self.active_session is None:
            raise RuntimeError('Must perform requests within CapiClient `async with` context')

        url = self.hostname + url_part

        await LOGGER.adebug("CAPI POST %s %s", url, json.dumps(json_payload))

        try:
            async with self.active_session.post(url, json=json_payload, auth=self.auth) as response:
                await LOGGER.adebug("CAPI response: %d %s", response.status, await response.text())

                yield response
        except Exception:
            await LOGGER.adebug(f"Exception while contacting CAPI:\n{traceback.format_exc()}")
            raise

    async def submit_vds(
        self,
        vd_submission: VDSubmission,
    ) -> tuple[CapiSubmissionResult, str | None]:
        """
        Attempt to submit a VD to CAPI.
        If CAPI tentatively accepted it
        (CapiSubmissionResult.ACCEPTED_PENDING), return the VD_UUID in
        the second return-tuple item. Otherwise, it either explicitly
        rejected it, or there was some kind of error.
        """
        try:
            async with self._do_post(
                '/submission/vds/',
                {
                    'cp_name': vd_submission.cp_name,
                    'pou': {
                        'commit_sha1': vd_submission.pou.commit_sha1.lower(),
                        'sanitizer': vd_submission.pou.sanitizer,
                    },
                    'pov': {
                        'harness': vd_submission.pov.harness,
                        'data': b64encode(vd_submission.pov.data).decode('ascii'),
                    }
                },
            ) as response:
                if response.status // 100 == 4:
                    # HTTP 4xx: our fault. Unlikely to be worth trying again.
                    return CapiSubmissionResult.REJECTED, None
                elif response.status // 100 == 2:
                    # HTTP 2xx: server probably accepted it
                    pass
                else:
                    # Something else, e.g., HTTP 5xx. Try again later?
                    await LOGGER.adebug("Unusual CAPI response to VD submission (recommending retry): %s", str(response))
                    return CapiSubmissionResult.ERROR_TRY_AGAIN, None

                response_json = await response.json()

                if response_json.get('status') not in ['pending', 'accepted']:
                    return CapiSubmissionResult.REJECTED, None

                return (
                    CapiSubmissionResult.ACCEPTED_PENDING,
                    response_json.get('vd_uuid'),
                )

        except Exception:
            # Unclear... probably not a bad idea to try again, though
            await LOGGER.adebug("Exception while attempting to submit VD to CAPI (recommending retry)")
            return CapiSubmissionResult.ERROR_TRY_AGAIN, None

    async def check_vds(self, vd_uuid: str) -> tuple[FeedbackStatus, str | None] | None:
        """
        Query CAPI for the current status of a VD submission.
        Returns the new feedback status and CPV_UUID if possible, or
        None if the request failed for some reason
        """
        try:
            async with self._do_get(f'/submission/vds/{vd_uuid}') as response:
                if response.status != 200:
                    return None

                response_json = await response.json()
                return (
                    FeedbackStatus(response_json.get('status')),
                    response_json.get('cpv_uuid'),
                )

        except Exception:
            return None

    async def submit_gp(
        self,
        gp_submission: GPSubmission
    ) -> tuple[CapiSubmissionResult, str | None]:
        """
        Attempt to submit a GP to CAPI.
        If CAPI tentatively accepted it
        (CapiSubmissionResult.ACCEPTED_PENDING), return the GP_UUID in
        the second return-tuple item. Otherwise, it either explicitly
        rejected it, or there was some kind of error.
        """
        try:
            async with self._do_post(
                '/submission/gp/',
                {
                    'cpv_uuid': str(gp_submission.cpv_uuid),
                    'data': b64encode(gp_submission.data.encode('utf-8')).decode('ascii'),
                },
            ) as response:
                if response.status // 100 == 4:
                    # HTTP 4xx: our fault. Unlikely to be worth trying again.
                    return CapiSubmissionResult.REJECTED, None
                elif response.status // 100 == 2:
                    # HTTP 2xx: server probably accepted it
                    pass
                else:
                    # Something else, e.g., HTTP 5xx. Try again later?
                    await LOGGER.adebug("Unusual CAPI response to GP submission (recommending retry): %s", str(response))
                    return CapiSubmissionResult.ERROR_TRY_AGAIN, None

                response_json = await response.json()

                if response_json.get('status') not in ['pending', 'accepted']:
                    return CapiSubmissionResult.REJECTED, None

                return (
                    CapiSubmissionResult.ACCEPTED_PENDING,
                    response_json.get('gp_uuid'),
                )

        except Exception:
            # Unclear... probably not a bad idea to try again, though
            await LOGGER.adebug("Exception while attempting to submit GP to CAPI (recommending retry)")
            return CapiSubmissionResult.ERROR_TRY_AGAIN, None

    async def check_gp(self, gp_uuid: str) -> FeedbackStatus | None:
        """
        Query CAPI for the current status of a GP submission.
        Returns the new feedback status, or None if the request failed
        for some reason
        """
        try:
            async with self._do_get(f'/submission/gp/{gp_uuid}') as response:
                if response.status != 200:
                    return None

                response_json = await response.json()
                return FeedbackStatus(response_json.get('status'))

        except Exception:
            return None
