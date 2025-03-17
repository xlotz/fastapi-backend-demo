from datetime import datetime
from fastapi import APIRouter, Depends, Form, Query, Request
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.dict_vo import (
    DictDataModel, DictDataPageQueryModel, DictTypeModel, DictTypePageQueryModel,
    DeleteDictDataModel, DeleteDictTypeModel
)
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.dict_service import DictDataService, DictTypeService
from module_admin.service.login_service import LoginService
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil
from utils.get_db import get_db


dictController = APIRouter(prefix='/system/dict', dependencies=[Depends(LoginService.get_current_user)])


@dictController.get(
    '/type/list', response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('system:dict:list'))])
async def get_system_dict_type_list(
        request: Request,
        dict_type_page_query: DictTypePageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
):
    """
    获取分页数据
    :param request:
    :param dict_type_page_query:
    :param db:
    :return:
    """
    dict_type_page_result = await DictTypeService.get_dict_type_list_services(db, dict_type_page_query, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=dict_type_page_result)


@dictController.post('/type', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:add'))])
@ValidateFields(validate_model='add_dict_type')
@Log(title='字典类型', business_type=BusinessType.INSERT)
async def add_system_dict_type(
        request: Request,
        add_dict_type: DictTypeModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    添加字段类型
    :param request:
    :param add_dict_type:
    :param db:
    :param current_user:
    :return:
    """
    add_dict_type.create_by = current_user.user.user_name
    add_dict_type.create_time = datetime.now()
    add_dict_type.update_by = current_user.user.user_name
    add_dict_type.update_time = datetime.now()
    add_dict_type_result = await DictTypeService.add_dict_type_services(db, add_dict_type)
    logger.info(add_dict_type_result.message)
    return ResponseUtil.success(msg=add_dict_type_result.message)


@dictController.put('/type', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:edit'))])
@ValidateFields(validate_model='edit_dict_type')
@Log(title='字典类型', business_type=BusinessType.UPDATE)
async def edit_system_dict_type(
        request: Request,
        edit_dict_type: DictTypeModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    编辑字段类型
    :param request:
    :param edit_dict_type:
    :param db:
    :param current_user:
    :return:
    """
    edit_dict_type.update_by = current_user.user.user_name
    edit_dict_type.update_time = datetime.now()
    edit_dict_type_result = await DictTypeService.edit_dict_type_services(request, db, edit_dict_type)
    logger.info(edit_dict_type_result.message)
    return ResponseUtil.success(msg=edit_dict_type_result.message)


@dictController.delete('/type/refreshCache', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:remove'))])
@Log(title='字典类型', business_type=BusinessType.UPDATE)
async def refresh_system_dict_type(
        request: Request,
        db: AsyncSession = Depends(get_db),
):
    """
    刷新字典类型缓存
    :param request:
    :param db:
    :return:
    """
    refresh_dict_type_result = await DictTypeService.refresh_sys_dict_services(request, db)
    logger.info(refresh_dict_type_result.message)
    return ResponseUtil.success(msg=refresh_dict_type_result.message)


@dictController.delete('/type/{dict_ids}', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:remove'))])
@Log(title='字典类型', business_type=BusinessType.DELETE)
async def delete_system_dict_type(
        request: Request,
        dict_ids: str,
        db: AsyncSession = Depends(get_db),
):
    """
    删除字段类型
    :param request:
    :param dict_ids:
    :param db:
    :return:
    """
    delete_dict_type = DeleteDictTypeModel(dict_ids=dict_ids)
    delete_dict_type_result = await DictTypeService.delete_dict_type_services(request, db, delete_dict_type)
    logger.info(delete_dict_type_result.message)
    return ResponseUtil.success(msg=delete_dict_type_result.message)


@dictController.get(
    '/type/optionselect',
    response_model=List[DictTypeModel], dependencies=[Depends(CheckUserInterfaceAuth('system:dict:query'))])
async def query_detail_system_dict_type(
        request: Request,
        dict_id: int,
        db: AsyncSession = Depends(get_db),
):
    """
    查询字典详细
    :param request:
    :param dict_id:
    :param db:
    :return:
    """
    dict_type_result = await DictTypeService.dict_type_detail_services(db, dict_id)
    logger.info('查询成功')
    return ResponseUtil.success(model_content=dict_type_result)


@dictController.post('/type/export', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:export'))])
@Log(title='字典类型', business_type=BusinessType.EXPORT)
async def export_system_dict_type(
        request: Request,
        dict_type_page_query: DictTypePageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
):
    """
    导出字典类型
    :param request:
    :param dict_type_page_query:
    :param db:
    :return:
    """
    dict_type_result = await DictTypeService.get_dict_type_list_services(db, dict_type_page_query, is_page=False)
    dict_type_export = await DictTypeService.export_dict_type_list_services(dict_type_result)
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(dict_type_export))


@dictController.get('/data/type/{dict_type}')
async def query_system_dict_type_data(
        request: Request,
        dict_type: str,
        db: AsyncSession = Depends(get_db),
):
    """
    根据字典类型查询字典数据信息
    :param request:
    :param dict_type:
    :param db:
    :return:
    """
    dict_data_result = await DictDataService.query_dict_data_list_from_cache_services(request.app.state.redis, dict_type)
    logger.info('查询成功')
    return ResponseUtil.success(data=dict_data_result)


@dictController.get(
    '/data/list', response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('system:dict:list'))])
async def get_system_dict_data_list(
        request: Request,
        dict_data_page_query: DictDataPageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
):
    """
    获取分页数据
    :param request:
    :param dict_data_page_query:
    :param db:
    :return:
    """

    dict_data_result = await DictDataService.get_dict_data_list_services(db, dict_data_page_query, is_page=True)
    logger.info('查询成功')
    return ResponseUtil.success(model_content=dict_data_result)


@dictController.post('/data', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:add'))])
@ValidateFields(validate_model='add_dict_data')
@Log(title='字典数据', business_type=BusinessType.INSERT)
async def add_system_dict_data(
        request: Request,
        add_dict_data: DictDataModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    添加字典数据
    :param current_user:
    :param request:
    :param add_dict_data:
    :param db:
    :return:
    """
    add_dict_data.create_by = current_user.user.user_name
    add_dict_data.create_time = datetime.now()
    add_dict_data.update_by = current_user.user.user_name
    add_dict_data.update_time = datetime.now()
    add_dict_data_result = await DictDataService.add_dict_data_services(request, db, add_dict_data)
    logger.info(add_dict_data_result.message)
    return ResponseUtil.success(msg=add_dict_data_result.message)


@dictController.put('/data', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:edit'))])
@ValidateFields(validate_model='edit_dict_data')
@Log(title='字典数据', business_type=BusinessType.UPDATE)
async def edit_system_dict_data(
        request: Request,
        edit_dict_data: DictDataModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    编辑字典数据
    :param request:
    :param edit_dict_data:
    :param db:
    :param current_user:
    :return:
    """
    edit_dict_data.update_by = current_user.user.user_name
    edit_dict_data.update_time = datetime.now()
    edit_dict_data_result = await DictDataService.edit_dict_data_services(request, db, edit_dict_data)
    logger.info(edit_dict_data_result.message)
    return ResponseUtil.success(msg=edit_dict_data_result.message)


@dictController.delete('/data/{dict_codes}', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:remove'))])
@Log(title='字典数据', business_type=BusinessType.DELETE)
async def delete_system_dict_data(
        request: Request,
        dict_codes: str,
        db: AsyncSession = Depends(get_db),
):
    """
    删除字典数据
    :param request:
    :param dict_codes:
    :param db:
    :return:
    """
    delete_dict_data = DeleteDictDataModel(dict_codes=dict_codes)  # type: DeleteDictDataModel
    delete_dict_data_result = await DictDataService.delete_dict_data_services(request, db, delete_dict_data)
    logger.info(delete_dict_data_result.message)
    return ResponseUtil.success(msg=delete_dict_data_result.message)


@dictController.get(
    '/data/{dict_code}',
    response_model=DictDataModel,
    dependencies=[Depends(CheckUserInterfaceAuth('system:dict:query'))])
async def query_detail_system_dict_data(
        request: Request,
        dict_code: int,
        db: AsyncSession = Depends(get_db),
):
    """
    查询字典数据详细
    :param request:
    :param dict_code:
    :param db:
    :return:
    """
    dict_data_result = await DictDataService.dict_data_detail_services(db, dict_code)
    logger.info('查询成功')
    return ResponseUtil.success(data=dict_data_result)


@dictController.post('/data/export', dependencies=[Depends(CheckUserInterfaceAuth('system:dict:export'))])
@Log(title='字典数据', business_type=BusinessType.EXPORT)
async def export_system_dict_data(
        request: Request,
        dict_data_page_query: DictDataPageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
):
    """
    导出字典数据
    :param request:
    :param dict_data_page_query:
    :param db:
    :return:
    """
    dict_data_result = await DictDataService.get_dict_data_list_services(db, dict_data_page_query, is_page=False)
    dict_data_export = await DictDataService.export_dict_data_list_services(dict_data_result)  # type: bytes
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(dict_data_export))