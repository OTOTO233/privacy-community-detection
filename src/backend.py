"""Compatibility entrypoint for the integrated deployable backend framework."""

from __future__ import annotations

from .backend_framework import app, create_app

__all__ = ["app", "create_app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
