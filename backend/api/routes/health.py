from __future__ import annotations

import platform
import sys

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "python_version": sys.version,
        "platform": platform.platform(),
    }
