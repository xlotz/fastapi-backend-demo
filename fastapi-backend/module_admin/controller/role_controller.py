from datetime import datetime
from fastapi import APIRouter, Depends, Form, Query, Request
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.dept_vo import DeptModel
from module_admin.entity.vo.role_vo import RoleModel, RolePageQueryModel, AddRoleModel, DeleteRoleModel
from module_admin.entity.vo.user_vo import UserRolePageQueryModel, CrudUserRoleModel, CurrentUserModel
from module_admin.service.dept_service import DeptService
from module_admin.service.login_service import LoginService
from module_admin.service.role_service import RoleService
from module_admin.service.user_service import UserService
from utils.get_db import get_db
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil


roleController = APIRouter(prefix="/system/role", dependencies=[Depends(LoginService.get_current_user)])


@roleController.get('/deptTree/{role_id}', dependencies=[Depends(CheckUserInterfaceAuth('system:role:query'))])
async def get_system_role_dept_tree(
        request: Request,
        role_id: int,
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    根据角色id获取部门树
    :param data_scope_sql:
    :param request:
    :param role_id:
    :param db:
    :return:
    """
    dept_result = await DeptService.get_dept_tree_services(db, DeptModel(**{}), data_scope_sql)
    role_dept_result = await RoleService.get_role_dept_tree_services(db, role_id)
    role_dept_result.depts = dept_result
    logger.info('获取成功')
    return ResponseUtil.success(model_content=role_dept_result)


@roleController.get(
    '/list', response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('system:role:list'))])
async def get_system_role_list(
        request: Request,
        role_page_query: RolePageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    获取角色列表
    :param request:
    :param role_page_query:
    :param db:
    :param data_scope_sql:
    :return:
    """
    role_query_result = await RoleService.get_role_list_services(db, role_page_query, data_scope_sql, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=role_query_result)


@roleController.post('', dependencies=[Depends(CheckUserInterfaceAuth('system:role:add'))])
@ValidateFields(validate_model='add_role')
@Log(title='角色管理', business_type=BusinessType.INSERT)
async def add_system_role(
        request: Request,
        add_role: AddRoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    新增角色
    :param request:
    :param add_role:
    :param db:
    :param current_user:
    :return:
    """
    add_role.create_by = current_user.user.user_name
    add_role.create_time = datetime.now()
    add_role.update_by = current_user.user.user_name
    add_role.update_time = datetime.now()
    add_role_result = await RoleService.add_role_services(db, add_role)
    logger.info(add_role_result.message)
    return ResponseUtil.success(msg=add_role_result.message)


@roleController.put('', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
@ValidateFields(validate_model='edit_role')
@Log(title='角色管理', business_type=BusinessType.UPDATE)
async def edit_system_role(
        request: Request,
        edit_role: RoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    编辑角色
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
@Log(title='角色管理', business_type=BusinessType.GRANT)
async def edit_system_role_datascope(
        request: Request,
        role_data_scope: AddRoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    编辑角色数据权限
    :param request:
    :param role_data_scope:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """

    await RoleService.check_role_allowed_services(role_data_scope)
    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(role_data_scope.role_id), data_scope_sql)

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
@Log(title='角色管理', business_type=BusinessType.DELETE)
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
                await RoleService.check_role_data_scope_services(db, str(role_id), data_scope_sql)
    delete_role = DeleteRoleModel(role_ids=role_ids, update_by=current_user.user.user_name, update_time=datetime.now())
    delete_role_result = await RoleService.delete_role_services(db, delete_role)
    logger.info(delete_role_result.message)
    return ResponseUtil.success(msg=delete_role_result.message)


@roleController.get(
    '/{role_id}', response_model=RoleModel, dependencies=[Depends(CheckUserInterfaceAuth('system:role:query'))])
async def query_detail_system_role(
        request: Request,
        role_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    根据角色id获取角色详情
    :param request:
    :param role_id:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """

    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(role_id), data_scope_sql)  # 检查数据权限

    role_detail_result = await RoleService.get_role_detail_services(db, role_id)
    logger.info('获取成功')
    return ResponseUtil.success(data=role_detail_result)


@roleController.post('/export', dependencies=[Depends(CheckUserInterfaceAuth('system:role:export'))])
@Log(title='角色管理', business_type=BusinessType.EXPORT)
async def export_system_role(
        request: Request,
        role_query: RolePageQueryModel = Form(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    导出角色
    :param request:
    :param role_query:
    :param db:
    :param data_scope_sql:
    :return:
    """

    role_result = await RoleService.get_role_list_services(db, role_query, data_scope_sql, is_page=False)

    role_export_result = await RoleService.export_role_list_services(role_result)
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(role_export_result))


@roleController.put('/changeStatus', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
@Log(title='角色管理', business_type=BusinessType.UPDATE)
async def reset_system_role_status(
        request: Request,
        change_role: AddRoleModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    批量修改角色状态
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


@roleController.get(
    '/authUser/allocatedList',
    response_model=PageResponseModel,
    dependencies=[Depends(CheckUserInterfaceAuth('system:role:list'))])
async def get_system_allocated_user_list(
        request: Request,
        user_role_page_query: UserRolePageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    查询已分配用户角色列表
    :param request:
    :param user_role_page_query:
    :param db:
    :param data_scope_sql:
    :return:
    """

    role_user_allocated_page_result = await RoleService.get_role_user_allocated_list_services(
        db, user_role_page_query, data_scope_sql, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(data=role_user_allocated_page_result)


@roleController.get(
    '/authUser/unallocatedList',
    response_model=PageResponseModel,
    dependencies=[Depends(CheckUserInterfaceAuth('system:role:list'))])
async def get_system_allocated_user_list(
        request: Request,
        user_role_page_query: UserRolePageQueryModel = Query(),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    查询未分配用户角色列表
    :param request:
    :param user_role_page_query:
    :param db:
    :param data_scope_sql:
    :return:
    """

    role_user_unallocated_page_result = await RoleService.get_role_user_unallocated_list_services(
        db, user_role_page_query, data_scope_sql, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(data=role_user_unallocated_page_result)


@roleController.put('/authUser/selectAll', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
@Log(title='角色管理', business_type=BusinessType.GRANT)
async def add_system_role_user(
        request: Request,
        crud_user_role: CrudUserRoleModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    批量分配用户角色
    :param request:
    :param crud_user_role:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """

    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(crud_user_role.role_id), data_scope_sql)

    crud_user_role_result = await UserService.add_user_role_services(db, crud_user_role)
    logger.info(crud_user_role_result.message)
    return ResponseUtil.success(msg=crud_user_role_result.message)


@roleController.put('/authUser/cancel', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
@Log(title='角色管理', business_type=BusinessType.GRANT)
async def cancel_system_role_user(
        request: Request,
        crud_user_role: CrudUserRoleModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    取消用户角色
    :param request:
    :param crud_user_role:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(crud_user_role.role_id), data_scope_sql)

    crud_user_role_result = await UserService.delete_user_role_services(db, crud_user_role)
    logger.info(crud_user_role_result.message)
    return ResponseUtil.success(msg=crud_user_role_result.message)


@roleController.put('/authUser/cancelAll', dependencies=[Depends(CheckUserInterfaceAuth('system:role:edit'))])
@Log(title='角色管理', business_type=BusinessType.GRANT)
async def cancel_system_role_user(
        request: Request,
        crud_user_role: CrudUserRoleModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """
    批量取消用户角色
    :param request:
    :param crud_user_role:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    if not current_user.user.admin:
        await RoleService.check_role_data_scope_services(db, str(crud_user_role.role_id), data_scope_sql)

    crud_user_role_result = await UserService.delete_user_role_services(db, crud_user_role)
    logger.info(crud_user_role_result.message)
    return ResponseUtil.success(msg=crud_user_role_result.message)