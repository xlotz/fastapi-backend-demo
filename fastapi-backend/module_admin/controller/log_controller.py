from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.log_vo import (
    LoginLogPageQueryModel, OperLogPageQueryModel,
    DeleteLoginLogModel, DeleteOperLogModel, UnlockUser
)
from module_admin.service.log_service import LoginLogService, OperationLogService
from module_admin.service.login_service import LoginService
from utils.get_db import get_db
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil


logController = APIRouter(prefix="/monitor", dependencies=[Depends(LoginService.get_current_user)])


@logController.get(
    '/operlog/list',
    response_model=PageResponseModel,
    dependencies=[Depends(CheckUserInterfaceAuth('monitor:operlog:list'))])
async def get_system_operlog_list(
    request: Request,
    oper_log_page_query: OperLogPageQueryModel = Query(),
    db: AsyncSession = Depends(get_db),
):
    """
    获取分页数据
    :param request:
    :param oper_log_page_query:
    :param db:
    :return:
    """
    oper_log_page_result = await OperationLogService.get_operation_log_list(db, oper_log_page_query, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=oper_log_page_result)


@logController.delete('/operlog/clean', dependencies=[Depends(CheckUserInterfaceAuth('monitor:operlog:remove'))])
@Log(title='操作日志', business_type=BusinessType.DELETE)
async def clear_system_oper_log(
    request: Request,
    oper_ids: str,
    db: AsyncSession = Depends(get_db),
):
    """
    清空操作日志
    :param oper_ids:
    :param request:
    :param db:
    :return:
    """
    delete_oper_log = DeleteOperLogModel(oper_ids=oper_ids)
    delete_oper_log_result = await OperationLogService.delete_operation_log_services(db, delete_oper_log)
    logger.info(delete_oper_log_result.message)
    return ResponseUtil.success(msg=delete_oper_log_result.message)


@logController.post('/operlog/export', dependencies=[Depends(CheckUserInterfaceAuth('monitor:operlog:export'))])
@Log(title='操作日志', business_type=BusinessType.EXPORT)
async def export_system_oper_log_list(
    request: Request,
    oper_log_page_query: OperLogPageQueryModel = Form(),
    db: AsyncSession = Depends(get_db),
):
    """
    导出操作日志
    :param request:
    :param oper_log_page_query:
    :param db:
    :return:
    """

    oper_log_result = await OperationLogService.get_operation_log_list(db, oper_log_page_query, is_page=False)
    oper_log_export = await OperationLogService.export_operation_log_list_services(request, oper_log_result)
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(oper_log_export))


@logController.get(
    '/logininfor/list',
    response_model=PageResponseModel,
    dependencies=[Depends(CheckUserInterfaceAuth('monitor:loginlog:list'))])
async def get_system_login_log_list(
    request: Request,
    login_log_page_query: LoginLogPageQueryModel = Query(),
    db: AsyncSession = Depends(get_db),
):
    """
    获取登录日志
    :param request:
    :param login_log_page_query:
    :param db:
    :return:
    """
    login_log_page_query_result = await LoginLogService.get_login_log_list(db, login_log_page_query, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=login_log_page_query_result)


@logController.delete(
    '/logininfor/{info_ids}', dependencies=[Depends(CheckUserInterfaceAuth('monitor:logininfor:remove'))])
@Log(title='登录日志', business_type=BusinessType.DELETE)
async def delete_system_login_log(
    request: Request,
    info_ids: str,
    db: AsyncSession = Depends(get_db),
):
    """
    清空登录日志
    :param request:
    :param info_ids:
    :param db:
    :return:
    """
    delete_login_log = DeleteLoginLogModel(info_ids=info_ids)
    delete_login_log_result = await LoginLogService.delete_login_log_services(db, delete_login_log)
    logger.info(delete_login_log_result.message)
    return ResponseUtil.success(msg=delete_login_log_result.message)


@logController.delete('/logininfor/clean', dependencies=[Depends(CheckUserInterfaceAuth('monitor:logininfor:remove'))])
@Log(title='登录日志', business_type=BusinessType.CLEAN)
async def clear_system_login_log(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    删除登录日志
    :param request:
    :param db:
    :return:
    """
    clear_login_log = await LoginLogService.clear_login_log_services(db)
    logger.info(clear_login_log.message)
    return ResponseUtil.success(msg=clear_login_log.message)


@logController.post('/logininfor/export', dependencies=[Depends(CheckUserInterfaceAuth('monitor:logininfor:export'))])
@Log(title='登录日志', business_type=BusinessType.EXPORT)
async def export_system_login_log_list(
    request: Request,
    login_log_page_query: LoginLogPageQueryModel = Form(),
    db: AsyncSession = Depends(get_db),
):
    """
    导出登录日志
    :param request:
    :param login_log_page_query:
    :param db:
    :return:
    """

    login_log_query = await LoginLogService.get_login_log_list(db, login_log_page_query, is_page=False)
    login_log_export = await LoginLogService.export_login_log_list_services(login_log_query)
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(login_log_export))


@logController.get(
    '/logininfor/unlock/{user_name}', dependencies=[Depends(CheckUserInterfaceAuth('monitor:logininfor:unlock'))])
@Log(title='账户解锁', business_type=BusinessType.OTHER)
async def unlock_system_login_log(
    request: Request,
    user_name: str,
    db: AsyncSession = Depends(get_db),
):
    """
    解锁账户
    :param request:
    :param user_name:
    :param db:
    :return:
    """
    unlock_user = UnlockUser(user_name=user_name)
    unlock_user_result = await LoginLogService.unlock_user_services(request, db, unlock_user)
    logger.info(unlock_user_result.message)
    return ResponseUtil.success(msg=unlock_user_result.message)