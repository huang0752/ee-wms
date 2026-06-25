from fastapi import APIRouter

from app.common.response import ResponseSchema, SuccessResponse
from app.core.assembly import get_frontend_assembly_summary

from .schema import PublicConfigInfoOut

ConfigRouter = APIRouter(prefix="/config", tags=["系统管理", "公开配置"])


@ConfigRouter.get(
    "/info",
    summary="获取公开配置摘要",
    response_model=ResponseSchema[PublicConfigInfoOut],
)
async def get_public_config_info():
    return SuccessResponse(data={"assembly": get_frontend_assembly_summary()}, msg="获取配置成功")
