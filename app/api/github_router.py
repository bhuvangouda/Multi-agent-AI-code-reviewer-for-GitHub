from fastapi import APIRouter
from app.github.webhook import router as webhook_router

app_router = APIRouter()
app_router.include_router(webhook_router, prefix="/github")
