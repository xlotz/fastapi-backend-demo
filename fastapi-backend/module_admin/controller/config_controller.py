from datetime import datetime
from fastapi import APIRouter, Depends, Form, Query, Request
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.config_vo import ConfigModel, ConfigPageQueryModel, DeleteConfigModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.config_service import ConfigService
from module_admin.service.login_service import LoginService
from utils.get_db import get_db
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil


configController = APIRouter(prefix='/system/config', dependencies=[Depends(LoginService.get_current_user)])


@configController.get(
    '/list', response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('system:config:list'))])
async def get_system_config_list(
        request: Request,
        config_page_query: ConfigPageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
):
    """
    获取配置列表
    :param request:
    :param config_page_query:
    :param db:
    :return:
    """
    # 获取分页数据
    config_page_result = await ConfigService.get_config_list_services(db, config_page_query, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=config_page_result)


@configController.post('', dependencies=[Depends(CheckUserInterfaceAuth('system:config:add'))])
@ValidateFields(validate_model='add_config')
@Log(title='参数管理', business_type=BusinessType.INSERT)
async def add_system_config(
        request: Request,
        add_config: ConfigModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    添加配置
    :param request:
    :param add_config:
    :param db:
    :param current_user:
    :return:
    """
    add_config.create_by = current_user.user.user_name
    add_config.create_time = datetime.now()
    add_config.update_by = current_user.user.user_name
    add_config.update_time = datetime.now()

    add_config_result = await ConfigService.add_config_services(request, db, add_config)
    logger.info(add_config_result.message)
    return ResponseUtil.success(msg=add_config_result.message)


@configController.put('', dependencies=[Depends(CheckUserInterfaceAuth('system:user:edit'))])
@ValidateFields(validate_model='edit_config')
@Log(title='参数管理', business_type=BusinessType.UPDATE)
async def edit_system_config(
    request: Request,
    edit_config: ConfigModel,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    编辑配置
    :param request:
    :param edit_config:
    :param db:
    :param current_user:
    :return:
    """
    edit_config.update_by = current_user.user.user_name
    edit_config.update_time = datetime.now()
    edit_config_result = await ConfigService.edit_config_services(request, db, edit_config)
    logger.info(edit_config_result.message)
    return ResponseUtil.success(msg=edit_config_result.message)


@configController.delete('/refreshCache', dependencies=[Depends(CheckUserInterfaceAuth('system:config:remove'))])
@Log(title='参数管理', business_type=BusinessType.UPDATE)
async def refresh_system_config(
        request: Request,
        db: AsyncSession = Depends(get_db),
):
    """
    删除换成
    :param request:
    :param db:
    :return:
    """
    refresh_cache_result = await ConfigService.refresh_sys_config_services(request, db)  # 刷新缓存
    logger.info(refresh_cache_result.message)
    return ResponseUtil.success(msg=refresh_cache_result.message)


@configController.delete('/{config_ids}', dependencies=[Depends(CheckUserInterfaceAuth('system:config:remove'))])
@Log(title='参数管理', business_type=BusinessType.DELETE)
async def delete_system_config(
        request: Request,
        config_ids: str,
        db: AsyncSession = Depends(get_db),
):
    """
    删除配置
    :param request:
    :param config_ids:
    :param db:
    :return:
    """
    delete_config = DeleteConfigModel(config_ids=config_ids)
    delete_config_result = await ConfigService.delete_config_services(request, db, delete_config)
    logger.info(delete_config_result.message)
    return ResponseUtil.success(msg=delete_config_result.message)


@configController.get(
    '/{config_id}', response_model=ConfigModel, dependencies=[Depends(CheckUserInterfaceAuth('system:config:query'))])
async def query_detail_system_config(
        request: Request,
        config_id: int,
        db: AsyncSession = Depends(get_db),
):
    """
    查询配置详情
    :param request:
    :param config_id:
    :param db:
    :return:
    """
    config_detail = await ConfigService.config_detail_services(db, config_id)
    logger.info('查询成功')
    return ResponseUtil.success(data=config_detail)


@configController.get('/configKey/{config_key}')
async def query_system_config(request: Request, config_key: str):
    """
    根据config_key查询参数值
    :param request:
    :param config_key:
    :return:
    """
    config_query = await ConfigService.query_config_list_from_cache_services(request.app.state.redis, config_key)
    logger.info('查询成功')
    return ResponseUtil.success(data=config_query)


@configController.post('/export', dependencies=[Depends(CheckUserInterfaceAuth('system:config:export'))])
@Log(title='参数管理', business_type=BusinessType.EXPORT)
async def export_system_config(
        request: Request,
        config_page_query: ConfigPageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
):
    """
    导出配置
    :param request:
    :param config_page_query:
    :param db:
    :return:
    """

    config_result = await ConfigService.get_config_list_services(db, config_page_query, is_page=False)
    config_export = await ConfigService.export_config_list_services(config_result)  # 导出配置
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(config_export))