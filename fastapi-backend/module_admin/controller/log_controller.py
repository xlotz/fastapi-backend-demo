from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from utils.get_db import get_db
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.log_vo import (
    DeleteOperLogModel, DeleteLoginLogModel,
    LoginLogPageQueryModel, OperLogPageQueryModel,
    UnlockUser,
)
from module_admin.service.log_service import LoginLogService, OperationLogService
from module_admin.service.login_service import LoginService
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil


logController = APIRouter(prefix='/monnitor', dependencies=[Depends(LoginService.get_current_user)])


@logController.get('/operlog/list',
                   response_model=PageResponseModel,
                   dependencies=[Depends(CheckUserInterfaceAuth('monitor:operlog:list'))])
async def get_system_operation_log_list():
    pass