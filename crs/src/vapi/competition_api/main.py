import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from structlog.stdlib import get_logger
from vyper import v

from competition_api.config import init_vyper
from competition_api.cp_registry import CPRegistry
from competition_api.endpoints import CheckDockerReadyRouter, GPRouter, HealthRouter, PrecompileRouter, StatusRouter, UpdateGPRequestsRouter, VDSRouter
from competition_api.logging import logging_middleware, setup_logging

LOGGER = get_logger()

VAPI_API_VERSION = os.environ.get("VAPI_API_VERSION", "0.0.0")

tags_metadata = [
    {
        "name": "health",
        "description": "This endpoint will be used to check health of API.",
    },
    {
        "name": "submission",
        "description": "This endpoint will be used to submit VD and GP.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_vyper()
    setup_logging()

    if not v.get_bool("mock_mode"):
        # initialize cp registry
        CPRegistry.instance()

    yield


app = FastAPI(
    title=f"VAPI v{VAPI_API_VERSION} - Team-Atlanta Verifier API",
    lifespan=lifespan,
    version=VAPI_API_VERSION,
    description="""
# Team-Atlanta Verifier API

This is a fork of the AIxCC cAPI server used as part of the CRS to verify PoVs and generate PoU info before submitting to cAPI.
""",
    terms_of_service="https://aicyberchallenge.com/terms-condition/",
    openapi_tags=tags_metadata,
    contact={
        "name": "AIXCC",
        "url": "https://aicyberchallenge.com/faqs/",
    },
)

app.middleware("http")(logging_middleware)

for router in [PrecompileRouter, GPRouter, VDSRouter, HealthRouter, StatusRouter, UpdateGPRequestsRouter, CheckDockerReadyRouter]:
    app.include_router(router)
