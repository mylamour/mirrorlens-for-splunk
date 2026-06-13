from .config import router as config_router
from .investigate import router as investigate_router
from .report import router as report_router
from .snapshot import router as snapshot_router
from .stream import router as stream_router

__all__ = [
    "config_router",
    "investigate_router",
    "report_router",
    "snapshot_router",
    "stream_router",
]
