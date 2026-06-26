from fastapi import APIRouter

from .dashboard.controller import DashboardRouter

wms_router = APIRouter(prefix="/wms")

wms_router.include_router(DashboardRouter)
