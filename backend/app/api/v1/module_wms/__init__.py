from fastapi import APIRouter

from .dashboard.controller import DashboardRouter
from .master.controller import MasterRouter

wms_router = APIRouter(prefix="/wms")

wms_router.include_router(DashboardRouter)
wms_router.include_router(MasterRouter)
