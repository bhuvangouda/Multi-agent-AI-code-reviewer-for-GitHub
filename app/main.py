from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.github_router import app_router as github_router


def get_application() -> FastAPI:
    app = FastAPI(title="Multi-Agent AI Code Reviewer", version="0.1.0")
    app.include_router(health_router, prefix="/health")
    app.include_router(github_router)
    return app


app = get_application()
