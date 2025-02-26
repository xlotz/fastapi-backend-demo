from datetime import datetime
from fastapi import APIRouter, Query, Depends, Form, Request
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.dept_vo import DeptModel
from module_admin.entity.vo.role_vo import AddRoleModel, DeleteRoleModel, RoleModel, RolePageQueryModel
from module_admin.entity.vo.user_vo import CrudUserRoleModel, CurrentUserModel, UserRoleQueryModel
from module_admin.service.dept_service import DeptService
from module_admin.service.login_service import LoginService
from module_admin.service.role_service import RoleService
from module_admin.service.user_service import UserService
from utils.get_db import get_db
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil


roleController = APIRouter(prefix='/system/role', dependencies=[Depends(LoginService.get_current_user)])


@roleController.get('/deptTree/{role_id}', dependencies=[Depends(CheckUserInterfaceAuth('system:role:query'))])
async def get_system_role_dept_tree(
        request: Request,
        role_id: int,
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    根据角色id获取菜单
    :param request:
    :param role_id:
    :param db:
    :param data_scope_sql:
    :return:
    """

    dept_query_result = await DeptService.get_dept_tree_services(db, DeptModel(**{}), data_scope_sql)
    role_dept_query_result = await RoleService.get_role_dept_tree_services(db, role_id)
    role_dept_query_result.depts = dept_query_result
    logger.info('获取成功')
    return ResponseUtil.success(data=role_dept_query_result)


@roleController.get('/list',
                    response_model=PageResponseModel,
                    dependencies=[Depends(CheckUserInterfaceAuth('system:role:list'))])
async def get_system_role_list(
        request: Request,
        role_page_query: RolePageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql = Depends(GetDataScope('SysDept')),
):
    """
    获取角色列表
    :param request:
    :param role_page_query:
    :param db:
    :param data_scope_sql:
    :return:
    """
    role_page_query_result = await RoleService.get_role_list_services(db, role_page_query, data_scope_sql, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=role_page_query_result)


@roleController.post('', dependencies=[Depends(CheckUserInterfaceAuth('system:role:add'))])
@ValidateFields(validate_model='add_role')
async def add_system_role(
        request: Request,
        add_role: AddRoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    添加角色
    :param request:
    :param add_role:
    :param db:
    :param current_user:
    :return:
    """

    add_role.create_by = current_user.user.user_name
    add_role.create_time = datetime.now()
    add_role.update_by = current_user.user.user_name
    add_role.update__time = datetime.now()
    add_role_result = await RoleService.add_role_services(db, add_role)
    logger.info(add_role_result.message)
    return ResponseUtil.success(msg=add_role_result)


@roleController.put('', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
@ValidateFields(validate_model='edit_role')
async def edit_system_role(
        request: Request,
        edit_role: AddRoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    修改角色
    :param data_scope_sql:
    :param request:
    :param edit_role:
    :param db:
    :param current_user:
    :return:
    """
    await RoleService.check_role_allowed_services(edit_role)
    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(edit_role.role_id), data_scope_sql)
    edit_role.update_by = current_user.user.user_name
    edit_role.update_time = datetime.now()
    edit_role_result = await RoleService.edit_role_services(db, edit_role)
    logger.info(edit_role_result.message)
    return ResponseUtil.success(msg=edit_role_result.message)


@roleController.put('/dataScope', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
async def edit_system_role_datascope(
        request: Request,
        role_data_scope: AddRoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    修改角色权限
    :param request:
    :param role_data_scope:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    await RoleService.check_role_allowed_services(role_data_scope)
    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(role_data_scope), data_scope_sql)
    edit_role = AddRoleModel(
        role_id=role_data_scope.role_id,
        data_scope=role_data_scope.data_scope,
        dept_ids=role_data_scope.dept_ids,
        dept_check_strictly=role_data_scope.dept_check_strictly,
        update_by=current_user.user.user_name,
        update_time=datetime.now(),
    )
    role_data_scope_result = await RoleService.role_datascope_services(db, edit_role)
    logger.info(role_data_scope_result.message)
    return ResponseUtil.success(msg=role_data_scope_result.message)


@roleController.delete('/{role_ids}', dependencies=[Depends(CheckUserInterfaceAuth('system:role:remove'))])
async def delete_system_role(
        request: Request,
        role_ids: str,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    删除角色
    :param request:
    :param role_ids:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    role_id_list = role_ids.split(',') if role_ids else []
    if role_id_list:
        for role_id in role_id_list:
            await RoleService.check_role_allowed_services(RoleModel(role_id=role_id))
            if not current_user.user.admin:
                await RoleService.check_role_data_scope_services(db, role_id, data_scope_sql)
    delete_role = DeleteRoleModel(role_ids=role_ids, update_by=current_user.user.user_name, update_time=datetime.now())
    delete_role_result = await RoleService.delete_role_services(db, delete_role)
    logger.info(delete_role_result.message)
    return ResponseUtil.success(msg=delete_role_result.message)


@roleController.get('/{role_id}',
                    response_model=RoleModel, dependencies=[Depends(CheckUserInterfaceAuth('system:role:query'))])
async def query_detail_system_role(
        request: Request,
        role_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    根据role_id获取角色详情
    :param request:
    :param role_id:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """

    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(role_id), data_scope_sql)
    role_detail_result = await RoleService.role_detail_services(db, role_id)
    logger.info(f'获取角色id:{role_id}信息成功')
    return ResponseUtil.success(data=role_detail_result.model_dump())


@roleController.post('/export', dependencies=[Depends(CheckUserInterfaceAuth('system:role:export'))])
async def export_system_role_list(
        request: Request,
        role_page_query: RolePageQueryModel = Form(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    导出角色列表
    :param request:
    :param role_page_query:
    :param db:
    :param data_scope_sql:
    :return:
    """
    # 获取全量数据
    role_query_result = await RoleService.get_role_list_services(db, role_page_query, data_scope_sql, is_page=False)
    role_export_result = await RoleService.export_role_list_services(role_query_result)
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(role_export_result))


@roleController.put('/changeStatus', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
async def reset_system_role_status(
        request: Request,
        change_role: AddRoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    修改角色状态
    :param request:
    :param change_role:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    await RoleService.check_role_allowed_services(change_role)
    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(change_role.role_id), data_scope_sql)
    edit_role = AddRoleModel(
        role_id=change_role.role_id,
        status=change_role.status,
        update_by=current_user.user.user_name,
        update_time=datetime.now(),
        type='status',
    )
    edit_role_result = await RoleService.edit_role_services(db, edit_role)
    logger.info(edit_role_result.message)
    return ResponseUtil.success(msg=edit_role_result.message)


@roleController.get('/authUser/allocateList',
                    response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('system:role:list'))])
async def get_system_allocated_user_list(
        request: Request,
        user_role: UserRoleQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    """
    获取已分配的角色的用户列表
    :param request:
    :param user_role:
    :param db:
    :param data_scope_sql:
    :return:
    """
    role_user_allocated_page_query_result = await RoleService.get_role_user_allocated_list_services(
        db, user_role, data_scope_sql, is_page=True
    )
    logger.info('获取成功')
    return ResponseUtil.success(model_content=role_user_allocated_page_query_result)


@roleController.get('/authUser/unallocatedList',
                    response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('system:role:list'))])
async def get_system_unallocated_user_list(
        request: Request,
        user_role: UserRoleQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    """
    获取未分配角色的用户列表
    :param request:
    :param user_role:
    :param db:
    :param data_scope_sql:
    :return:
    """
    role_user_unallocated_page_query_result = await RoleService.get_role_user_unallocated_list_services(
        db, user_role, data_scope_sql, is_page=True
    )
    logger.info('获取成功')
    return ResponseUtil.success(model_content=role_user_unallocated_page_query_result)


@roleController.put('/authUser/selectAll', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
async def add_system_role_user(
        request: Request,
        add_role_user: CrudUserRoleModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    给用户添加角色
    :param request:
    :param add_role_user:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(add_role_user.role_id), data_scope_sql)

    add_role_user_result = await UserService.add_user_role_services(db, add_role_user)
    logger.info(add_role_user_result.message)
    return ResponseUtil.success(msg=add_role_user_result.message)


@roleController.put('/authUser/cancel', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
async def cancel_system_role_user(
        request: Request,
        cancel_user_role: CrudUserRoleModel,
        db: AsyncSession = Depends(get_db),
):
    """
    取消用户角色
    :param request:
    :param cancel_user_role:
    :param db:
    :return:
    """
    cancel_user_role_result = await UserService.delete_user_role_services(db, cancel_user_role)
    logger.info(cancel_user_role_result.message)
    return ResponseUtil.success(msg=cancel_user_role_result.message)


@roleController.put('/authUser/cancelAll', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
async def batch_cancel_system_role_user(
        request: Request,
        batch_cancel_user_role: CrudUserRoleModel = Query(),
        db: AsyncSession = Depends(get_db),
):
    """
    批量取消用户角色
    :param request:
    :param batch_cancel_user_role:
    :param db:
    :return:
    """
    batch_cancel_user_role_result = await UserService.delete_user_role_services(db, batch_cancel_user_role)
    logger.info(batch_cancel_user_role_result.message)
    return ResponseUtil.success(msg=batch_cancel_user_role_result)