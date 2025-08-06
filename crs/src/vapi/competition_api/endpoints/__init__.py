from .check_docker_ready import router as CheckDockerReadyRouter
from .gp import router as GPRouter
from .health import router as HealthRouter
from .precompile import router as PrecompileRouter
from .status import router as StatusRouter
from .update_gp_requests import router as UpdateGPRequestsRouter
from .vds import router as VDSRouter

__all__ = ["CheckDockerReadyRouter", "GPRouter", "HealthRouter", "PrecompileRouter", "StatusRouter", "UpdateGPRequestsRouter", "VDSRouter"]
