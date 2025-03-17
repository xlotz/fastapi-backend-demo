from datetime import datetime
from fastapi import APIRouter, Depends, Form, Query, Request
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.menu_vo import MenuModel, MenuQueryModel, DeleteMenuModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService
from module_admin.service.menu_service import MenuService
from utils.get_db import get_db
from utils.log_util import logger
from utils.response_util import ResponseUtil


menuController = APIRouter(prefix="/system/menu", dependencies=[Depends(LoginService.get_current_user)])


@menuController.get('/treeselect')
async def get_system_menu_tree(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    获取菜单树
    :param request:
    :param db:
    :param current_user:
    :return:
    """
    menu_tree = await MenuService.get_menu_tree_services(db, current_user)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=menu_tree)


@menuController.get('/roleMenuTreeselect/{role_id}')
async def get_system_role_menu_tree(
        request: Request,
        role_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    根据角色id获取菜单树
    :param request:
    :param role_id:
    :param db:
    :param current_user:
    :return:
    """
    role_menu_query_result = await MenuService.get_role_menu_tree_services(db, role_id, current_user)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=role_menu_query_result)


@menuController.get(
    '/list',
    response_model=List[MenuModel],
    dependencies=[Depends(CheckUserInterfaceAuth('system:menu:list'))])
async def get_system_menu_list(
    request: Request,
    menu_query: MenuQueryModel = Query(),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    获取分页数据
    :param request:
    :param menu_query:
    :param db:
    :param current_user:
    :return:
    """
    menu_query_result = await MenuService.get_menu_list_services(db, menu_query, current_user)
    logger.info('获取成功')
    return ResponseUtil.success(data=menu_query_result)


@menuController.post('', dependencies=[Depends(CheckUserInterfaceAuth('system:menu:add'))])
@ValidateFields(validate_model='add_menu')
@Log(title='菜单管理', business_type=BusinessType.INSERT)
async def add_system_menu(
    request: Request,
    add_menu: MenuModel,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    添加菜单
    :param request:
    :param add_menu:
    :param db:
    :param current_user:
    :return:
    """
    add_menu.create_by = current_user.user.user_name
    add_menu.create_time = datetime.now()
    add_menu.update_by = current_user.user.user_name
    add_menu.update_time = datetime.now()
    add_menu_result = await MenuService.add_menu_services(db, add_menu)
    logger.info(add_menu_result.message)
    return ResponseUtil.success(msg=add_menu_result.message)


@menuController.put('', dependencies=[Depends(CheckUserInterfaceAuth('system:menu:edit'))])
@ValidateFields(validate_model='edit_menu')
@Log(title='菜单管理', business_type=BusinessType.UPDATE)
async def edit_system_menu(
    request: Request,
    edit_menu: MenuModel,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    编辑菜单
    :param request:
    :param edit_menu:
    :param db:
    :param current_user:
    :return:
    """
    edit_menu.update_by = current_user.user.user_name
    edit_menu.update_time = datetime.now()
    edit_menu_result = await MenuService.edit_menu_services(db, edit_menu)
    logger.info(edit_menu_result.message)
    return ResponseUtil.success(msg=edit_menu_result.message)


@menuController.delete('/{menu_ids}', dependencies=[Depends(CheckUserInterfaceAuth('system:menu:remove'))])
@Log(title='菜单管理', business_type=BusinessType.DELETE)
async def delete_system_menu(
    request: Request,
    menu_ids: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除菜单
    :param request:
    :param menu_ids:
    :param db:
    :return:
    """
    delete_menu = DeleteMenuModel(menu_ids=menu_ids)
    delete_menu_result = await MenuService.delete_menu_services(db, delete_menu)
    logger.info(delete_menu_result.message)
    return ResponseUtil.success(msg=delete_menu_result.message)


@menuController.get(
    '/{menu_id}', response_model=MenuModel, dependencies=[Depends(CheckUserInterfaceAuth('system:menu:query'))])
async def query_detail_system_menu(
    request: Request,
    menu_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    根据菜单id获取菜单详情
    :param request:
    :param menu_id:
    :param db:
    :return:
    """
    menu_detail = await MenuService.query_menu_detail_services(db, menu_id)
    logger.info('获取成功')
    return ResponseUtil.success(data=menu_detail)
