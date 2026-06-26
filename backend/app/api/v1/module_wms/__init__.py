from fastapi import APIRouter

from .arrival.controller import ArrivalRouter
from .check.controller import CheckRouter
from .dashboard.controller import DashboardRouter
from .inbound.controller import InboundRouter
from .inspection.controller import InspectionRouter
from .issue.controller import IssueRouter
from .master.controller import MasterRouter
from .outbound.controller import OutboundRouter
from .stock.controller import StockRouter
from .transfer.controller import TransferRouter
from .warning.controller import WarningRouter

wms_router = APIRouter(prefix="/wms")

wms_router.include_router(DashboardRouter)
wms_router.include_router(MasterRouter)
wms_router.include_router(StockRouter)
wms_router.include_router(ArrivalRouter)
wms_router.include_router(InspectionRouter)
wms_router.include_router(InboundRouter)
wms_router.include_router(OutboundRouter)
wms_router.include_router(IssueRouter)
wms_router.include_router(TransferRouter)
wms_router.include_router(CheckRouter)
wms_router.include_router(WarningRouter)
