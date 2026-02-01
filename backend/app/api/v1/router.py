"""API v1 router that combines all endpoint routers."""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.sources import router as sources_router
from app.api.v1.warehouse import router as warehouse_router

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(warehouse_router)
api_router.include_router(sources_router)
