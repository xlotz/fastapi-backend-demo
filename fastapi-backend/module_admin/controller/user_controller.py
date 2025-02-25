import os
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal, Optional, Union
from pydantic_validation_decorator import ValidateFields
from utils.get_db import get_db
from config.enums import BusinessType
from config.env import UploadConfig
# from module_admin.annotation
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.dept_vo import DeptModel
from module_admin.entity.vo.user_vo import (
    AddUserModel, CrudUserRoleModel, CurrentUserModel, DeleteUserModel, EditUserModel,
    ResetUserModel, ResetPasswordModel, UserDetailModel, UserInfoModel, UserModel,
    UserPageQueryModel, UserProfileModel, UserRoleQueryModel, UserRoleResponseModel,
)
from module_admin.service.login_service import LoginService
from module_admin.service.user_service import UserService
from module_admin.service.role_service import RoleService
from module_admin.service.dept_service import DeptService
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.pwd_util import PwdUtil
from utils.response_util import ResponseUtil
from utils.upload_util import UploadUtil


userController = APIRouter(prefix='/system/user', dependencies=[Depends(LoginService.get_current_user)])


@userController.get('/deptTree', dependencies=[Depends(CheckUserInterfaceAuth('system:user:list'))])
async def get_system_dept_tree(
        request: Request,
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    """

    :param request:
    :param db:
    :param data_scope_sql:
    :return:
    """

    dept_query_result = await DeptService.get_dept_tree_services(db, DeptModel(**{}), data_scope_sql)
    logger.info('获取成功')
    return ResponseUtil.success(data=dept_query_result)


@userController.get('/list', response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('system:user:list'))])
async def get_system_user_list(
        request: Request,
        user_page_query: UserPageQueryModel = Depends(UserPageQueryModel.as_query),
        db: AsyncSession = Depends(get_db),
        data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    """
    获取分页数据
    :param request:
    :param user_page_query:
    :param db:
    :param data_scope_sql:
    :return:
    """
    user_page_query_result = await UserService.get_user_list_services(db, user_page_query, data_scope_sql, is_page=True)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=user_page_query_result)


@userController.post('', dependencies=[Depends(CheckUserInterfaceAuth('system:user:add'))])
@ValidateFields(validate_model='add_user')
async def add_system_user(
        request: Request,
        add_user: AddUserModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        dept_data_scope_sql: str = Depends(GetDataScope('SysDept')),
        role_data_scope_sql: str = Depends(GetDataScope('SysRole')),
):
    """
    添加用户
    :param request:
    :param add_user:
    :param db:
    :param current_user:
    :param dept_data_scope_sql:
    :param role_data_scope_sql:
    :return:
    """
    if not current_user.user.admin:
        await DeptService.check_dept_data_scope_services(db, add_user.dept_id, dept_data_scope_sql)
        await RoleService.check_role_data_scope_services(
            db, ','.join([str(item) for item in add_user.role_ids]), role_data_scope_sql)
        add_user.password = PwdUtil.get_password_hash(add_user.password)
        add_user.create_by = current_user.user.user_name
        add_user.create_by = datetime.now()
        add_user.update_by = current_user.user.user_name
        add_user.update_by = datetime.now()
        add_user_result = await UserService.add_user_services(db, add_user)
        logger.info(add_user_result.message)
        return ResponseUtil.success(msg=add_user_result.message)


@userController.put('', dependencies=[Depends(CheckUserInterfaceAuth('system:user:edit'))])
@ValidateFields(validate_model='edit_user')
async def edit_system_user(
        request: Request,
        edit_user: EditUserModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        user_data_scope_sql: str = Depends(GetDataScope('SysUser')),
        dept_data_scope_sql: str = Depends(GetDataScope('SysDept')),
        role_data_scope_sql: str = Depends(GetDataScope('SysRole')),
):
    """
    修改用户
    :param request:
    :param edit_user:
    :param db:
    :param current_user:
    :param user_data_scope_sql:
    :param dept_data_scope_sql:
    :param role_data_scope_sql:
    :return:
    """

    await UserService.check_user_allowed_services(edit_user)
    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(db, edit_user.user_id, user_data_scope_sql)
        await DeptService.check_dept_data_scope_services(db, edit_user.dept_id, dept_data_scope_sql)
        await RoleService.check_role_data_scope_services(
            db, ','.join([str(item) for item in edit_user.role_ids]), role_data_scope_sql)
        edit_user.update_by = current_user.user.user_name
        edit_user.update_time = datetime.now()

        edit_user_result = await UserService.edit_user_services(db, edit_user)
        logger.info(edit_user_result.message)
        return ResponseUtil.success(msg=edit_user_result.message)


@userController.delete('/{user_ids}', dependencies=[Depends(CheckUserInterfaceAuth('system:user:remove'))])
async def delete_system_user(
        request: Request,
        user_ids: str,
        db: AsyncSession = Depends(get_db),
        current_user: str = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    """
    删除用户
    :param request:
    :param user_ids:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    user_id_list = user_ids.split(',') if user_ids else []
    if user_id_list:
        if current_user.user.user_id in user_id_list:
            logger.warning('当前登录用户不能删除')
            return ResponseUtil.failure(msg='当前登录用户不能删除')
        for user_id in user_id_list:
            await UserService.check_user_allowed_services(UserModel(user_id=int(user_id)))

    delete_user = DeleteUserModel(user_ids=user_ids, update_by=current_user.user.user_name, update_time=datetime.now())
    delete_user_result = await UserService.delete_user_services(db, delete_user)
    logger.info(delete_user_result.message)
    return ResponseUtil.success(msg=delete_user_result.message)


@userController.put('/resetPwd', dependencies=[Depends(CheckUserInterfaceAuth('system:user:resetPwd'))])
async def reset_system_user_pwd(
        request: Request,
        reset_user: EditUserModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    """
    重置用户密码
    :param request:
    :param reset_user:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """

    await UserService.check_user_allowed_services(reset_user)
    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(db, reset_user.user_id, data_scope_sql)
    edit_user = EditUserModel(
        user_id=reset_user.user_id,
        password=PwdUtil.get_password_hash(reset_user.password),
        update_by=current_user.user.user_name,
        update_time=datetime.now(),
        type='pwd',
    )
    edit_user_result = await UserService.edit_user_services(db, edit_user)
    logger.info(edit_user_result.message)
    return ResponseUtil.success(msg=edit_user_result.message)


@userController.put('/changeStatus', dependencies=[Depends(CheckUserInterfaceAuth('system:user:edit'))])
async def change_system_user_status(
        request: Request,
        change_user: EditUserModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    """
    修改用户状态
    :param request:
    :param change_user:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """

    await UserService.check_user_allowed_services(change_user)
    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(db, change_user.user.user_id, data_scope_sql)
    edit_user = EditUserModel(
        user_id=change_user.user_id,
        status=change_user.status,
        update_by=current_user.user.user_name,
        update_time=datetime.now(),
        type='status',
    )
    edit_user_result = await UserService.edit_user_services(db, edit_user)
    logger.info(edit_user_result.message)
    return ResponseUtil.success(msg=edit_user_result.message)


@userController.get('/profile', response_model=UserProfileModel)
async def query_detail_system_user_profile(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    获取用户配置
    :param request:
    :param db:
    :param current_user:
    :return:
    """
    profile_user_result = await UserService.user_profile_services(db, current_user.user.user_id)
    logger.info(f'获取user_id: {current_user.user.user_id}的信息成功')
    return ResponseUtil.success(model_content=profile_user_result)


@userController.get('/{user_id}', response_model=UserDetailModel, dependencies=[Depends(CheckUserInterfaceAuth('system:user:query'))])
@userController.get('/', response_model=UserDetailModel, dependencies=[Depends(CheckUserInterfaceAuth('system:user:query'))])
async def query_detail_system_user(
        request: Request,
        user_id: Optional[Union[int, Literal['']]] = '',
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    """
    通过id查询用户信息
    :param request:
    :param user_id:
    :param db:
    :param current_user:
    :param data_scope_sql:
    :return:
    """
    if user_id and not current_user.user.admin:
        await UserService.check_user_data_scope_services(db, user_id, data_scope_sql)
    detail_user_result = await UserService.user_detail_services(db, user_id)
    logger.info(f'获取user_id: {user_id}信息成功')
    return ResponseUtil.success(model_content=detail_user_result)


@userController.post('/profile/avatar')
async def change_system_user_profile_avatar(
        request: Request,
        avatarfile: bytes = File(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    修改用户头像
    :param request:
    :param avatarfile:
    :param db:
    :param current_user:
    :return:
    """
    if avatarfile:
        relative_path = (
            f'avatar/{datetime.now().strftime("%Y")}/{datetime.now().strftime("%m")}/{datetime.now().strftime("%d")}')
        dir_path = os.path.join(UploadConfig.UPLOAD_PATH, relative_path)
        try:
            os.makedirs(dir_path)
        except FileExistsError:
            pass
        avatar_name = f'avatar_{datetime.now().strftime("%Y%m%d%H%M%S")}{UploadConfig.UPLOAD_MACHINE}{UploadUtil.generate_random_number()}.png'
        avatar_path = os.path.join(dir_path, avatar_name)
        with open(avatar_path, 'wb') as f:
            f.write(avatarfile)
        edit_user = EditUserModel(
            user_id=current_user.user.user_id,
            avatar=f'{UploadConfig.UPLOAD_PREFIX}/{relative_path}/{avatar_name}',
            update_by=current_user.user.user_name,
            update_time=datetime.now(),
            type='avatar',
        )
        edit_user_result = await UserService.edit_user_services(db, edit_user)
        logger.info(edit_user_result.message)
        return ResponseUtil.success(dict_content={'imgUrl': edit_user.avatar}, msg=edit_user_result.message)
    return ResponseUtil.failure(msg='上传图片异常，请联系管理员')


@userController.put('/profile')
async def change_system_user_profile_info(
        request: Request,
        user_info: UserInfoModel,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    修改用户信息
    :param request:
    :param user_info:
    :param db:
    :param current_user:
    :return:
    """

    edit_user = EditUserModel(
        **user_info.model_dump(exclude_unset=True, exclude={'relo_ids'}),
        user_id=current_user.user.user_id,
        user_name=current_user.user.user_name,
        update_by=current_user.user.user_name,
        update_time=datetime.now(),
        role_ids=current_user.user.role_ids.split(',') if current_user.user.role_ids else [],
        role=current_user.user.role,
    )

    edit_user_result = await UserService.edit_user_services(db, edit_user)
    logger.info(edit_user_result.message)
    return ResponseUtil.success(msg=edit_user_result)


@userController.put('/profile/updatePwd')
async def reset_system_user_password(
        request: Request,
        reset_password: ResetPasswordModel = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    更新用户密码
    :param request:
    :param reset_password:
    :param db:
    :param current_user:
    :return:
    """

    reset_user = ResetUserModel(
        user_id=current_user.user.user_id,
        old_password=reset_password.old_password,
        password=reset_password.new_password,
        update_by=current_user.user.user_name,
        update_time=datetime.now(),
    )
    reset_user_result = await UserService.reset_user_services(db, reset_user)
    logger.info(reset_user_result.message)
    return ResponseUtil.success(msg=reset_user_result.message)


@userController.post('/importData', dependencies=[Depends(CheckUserInterfaceAuth('system:user:import'))])
async def batch_import_system_user():
    pass


@userController.post('/importTemplate', dependencies=[Depends(CheckUserInterfaceAuth('system:user:import'))])
async def export_system_user_template():
    pass


@userController.post('/export', dependencies=[Depends(CheckUserInterfaceAuth('system:user:export'))])
async def export_system_user_list():
    pass


@userController.get('/authRole/{user_id}',
                    response_model=UserRoleResponseModel,
                    dependencies=[Depends(CheckUserInterfaceAuth('system:user:query'))])
async def get_system_allocated_role_list(
        request: Request,
        user_id: int,
        db: AsyncSession = Depends(get_db),
):
    """
    获取已分配角色列表
    :param request:
    :param user_id:
    :param db:
    :return:
    """
    user_role_query = UserRoleQueryModel(user_id=user_id)
    user_role_allocated_query_result = await UserService.get_user_role_allocated_list_services(db, user_role_query)
    logger.info('获取成功')
    return ResponseUtil.success(model_content=user_role_allocated_query_result)


@userController.put('/authRole', response_model=UserRoleResponseModel,
                    dependencies=[Depends(CheckUserInterfaceAuth('system:user:edit'))])
async def update_system_role_user(
        request: Request,
        user_id: int = Query(),
        role_ids: str = Query(),
        db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        user_data_scope_sql: str = Depends(GetDataScope('SysUser')),
        role_data_scope_sql: str = Depends(GetDataScope('SysRole')),
):
    """
    修改用户角色
    :param request:
    :param user_id:
    :param role_ids:
    :param db:
    :param current_user:
    :param user_data_scope_sql:
    :param role_data_scope_sql:
    :return:
    """

    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(db, user_id, user_data_scope_sql)
        await RoleService.check_role_data_scope_services(db, role_ids, role_data_scope_sql)
    add_user_role_result = await UserService.add_user_role_services(db, CrudUserRoleModel(user_id=user_id, role_ids=role_ids))
    logger.info(add_user_role_result.message)

    return ResponseUtil.success(msg=add_user_role_result.message)