from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import (
    WmsBarcodeRuleModel,
    WmsCustomerModel,
    WmsLocationModel,
    WmsMaterialModel,
    WmsSupplierModel,
    WmsWarehouseModel,
    WmsZoneModel,
)
from .schema import WmsMasterResource

WMS_MASTER_MODELS = {
    "warehouse": WmsWarehouseModel,
    "zone": WmsZoneModel,
    "location": WmsLocationModel,
    "material": WmsMaterialModel,
    "supplier": WmsSupplierModel,
    "customer": WmsCustomerModel,
    "barcode-rule": WmsBarcodeRuleModel,
}


class WmsMasterCRUD(CRUDBase):
    def __init__(self, auth: AuthSchema, resource: WmsMasterResource) -> None:
        super().__init__(model=WMS_MASTER_MODELS[resource], auth=auth)


def model_for_resource(resource: WmsMasterResource):
    return WMS_MASTER_MODELS[resource]
