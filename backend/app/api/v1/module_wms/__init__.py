from fastapi import APIRouter

from .arrival.controller import ArrivalRouter
from .dashboard.controller import DashboardRouter
from .inbound.controller import InboundRouter
from .inspection.controller import InspectionRouter
from .issue.controller import IssueRouter
from .master.controller import MasterRouter
from .outbound.controller import OutboundRouter
from .stock.controller import StockRouter

wms_router = APIRouter(prefix="/wms")

wms_router.include_router(DashboardRouter)
wms_router.include_router(MasterRouter)
wms_router.include_router(StockRouter)
wms_router.include_router(ArrivalRouter)
wms_router.include_router(InspectionRouter)
wms_router.include_router(InboundRouter)
wms_router.include_router(OutboundRouter)
wms_router.include_router(IssueRouter)
