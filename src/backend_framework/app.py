"""Application factory for the deployable backend framework."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import pipeline_router, system_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Privacy Community Detection API",
        description="基于隐私保护的多层网络社区检测系统",
        version="0.3.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(system_router)
    app.include_router(pipeline_router)
    return app


app = create_app()
