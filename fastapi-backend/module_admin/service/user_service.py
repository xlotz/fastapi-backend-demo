import io
import pandas as pd
from datetime import datetime
from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Union
from config.constant import CommonConstant
from sub_applications.exceptions.exception import ServiceException
from module_admin.dao.user_dao import UserDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.user_vo import (
    UserModel, UserInfoModel, UserDetailModel, UserPageQueryModel, UserProfileModel,
    AddUserModel, EditUserModel, DeleteUserModel, ResetUserModel,
    CrudUserRoleModel, CurrentUserModel,
    SelectedRoleModel, UserRoleModel, UserRoleQueryModel, UserRoleResponseModel
)
from module_admin.service.config_service import ConfigService
from module_admin.service.dept_service import DeptService
from module_admin.service.role_service import RoleService
from utils.common_util import export_list2excel, get_excel_template, SqlalchemyUtil
from utils.page_util import PageResponseModel
from utils.pwd_util import PwdUtil


class UserService:
    """
    用户管理系统服务层
    """

    @classmethod
    async def get_user_list_services(
            cls, db: AsyncSession, query_obj: UserPageQueryModel, data_scope_sql: str, is_page: bool = False
    ):
        """
        获取用户列表信息
        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        query_result = await UserDao.get_user_list(db, query_obj, data_scope_sql, is_page)
        if is_page:
            user_list_result = PageResponseModel(**{
                **query_obj.model_dump(),
                'rows': [{**row[0], 'dept': row[1]} for row in query_result]
            })
        else:
            user_list_result = []
            if query_result:
                user_list_result = [{**row[0], 'dept': row[1]} for row in query_result]
        return user_list_result

    @classmethod
    async def check_user_allowed_services(cls, check_user: UserModel):
        """
        校验用户是否允许操作
        :param check_user:
        :return:
        """
        if check_user.admin:
            raise ServiceException(message='不允许操作超级管理用户')
        else:
            return CrudResponseModel(is_success=True, message='校验通过')

    @classmethod
    async def check_user_data_scope_services(cls, db: AsyncSession, user_id: int, data_scope_sql: str):
        """
        校验用户数据权限
        :param db:
        :param user_id:
        :param data_scope_sql:
        :return:
        """
        users = await UserDao.get_user_list(db, UserPageQueryModel(user_id=user_id), data_scope_sql, is_page=False)
        if users:
            return CrudResponseModel(is_success=True, message='校验通过')
        else:
            raise ServiceException(message='没有权限访问用户数据')

    @classmethod
    async def check_user_name_unique_services(cls, db: AsyncSession, page_obj: UserModel):
        """
        校验用户名是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        user_id = -1 if page_obj.user_id is None else page_obj.user_id
        user = await UserDao.get_user_by_info(db, UserModel(user_name=page_obj.user_name))
        if user and user.user_id != user_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def check_phonenumber_unique_services(cls, db: AsyncSession, page_obj: UserModel):
        """
        校验手机号是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        user_id = -1 if page_obj.user_id is None else page_obj.user_id
        user = await UserDao.get_user_by_info(db, UserModel(phonenumber=page_obj.phonenumber))

        if user and user.user_id != user_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def check_email_unique_services(cls, db: AsyncSession, page_obj: UserModel):
        """
        校验邮箱是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        user_id = -1 if page_obj.user_id is None else page_obj.user_id
        user = await UserDao.get_user_by_info(db, UserModel(email=page_obj.email))

        if user and user.user_id != user_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_user_services(cls, db: AsyncSession, page_obj: AddUserModel):
        """
        添加用户
        :param db:
        :param page_obj:
        :return:
        """
        add_user = UserModel(**page_obj.model_dump())
        if not await cls.check_user_name_unique_services(db, page_obj):
            raise ServiceException(message=f'新增用户{page_obj.user_name}失败，登录账户已存在')
        elif page_obj.phonenumber and not await cls.check_phonenumber_unique_services(db, page_obj):
            raise ServiceException(message=f'新增用户{page_obj.user_name}失败，手机号已存在')
        elif page_obj.email and not await cls.check_email_unique_services(db, page_obj):
            raise ServiceException(message=f'新增用户{page_obj.user_name}失败，email已存在')
        else:
            try:
                add_result = await UserDao.add_user_dao(db, add_user)
                user_id = add_result.user_id
                if page_obj.role_ids:
                    for role_id in page_obj.role_ids:
                        await UserDao.add_user_role_dao(db, UserRoleModel(user_id=user_id, role_id=role_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e

    @classmethod
    async def edit_user_services(cls, db: AsyncSession, page_obj: EditUserModel):
        """
        修改用户
        :param db:
        :param page_obj:
        :return:
        """
        edit_user = page_obj.model_dump(exclude_unset=True, exclude={'admin'})

        if page_obj.type != 'status' and page_obj.type != 'avatar' and page_obj.type != 'pwd':
            del edit_user['role_ids']
            del edit_user['role']

        if page_obj.type == 'status' and page_obj.type == 'avatar' and page_obj.type == 'pwd':
            del edit_user['type']

        user_info = await cls.get_user_detail_services(db, edit_user.get('user_id'))

        if user_info.data and user_info.data.user_id:
            if page_obj.type != 'status' and page_obj.type != 'avatar' and page_obj.type != 'pwd':
                if not await cls.check_user_name_unique_services(db, page_obj):
                    raise ServiceException(message=f'修改用户{page_obj.user_name}失败，登录账户已存在')
                elif not await cls.check_phonenumber_unique_services(db, page_obj):
                    raise ServiceException(message=f'修改用户{page_obj.user_name}失败，手机号已存在')
                elif not await cls.check_email_unique_services(db, page_obj):
                    raise ServiceException(message=f'修改用户{page_obj.user_name}失败，email已存在')
            try:
                await UserDao.edit_user_dao(db, edit_user)
                if page_obj.type != 'status' and page_obj.type != 'avatar' and page_obj.type != 'pwd':
                    await UserDao.delete_user_role_dao(db, UserRoleModel(user_id=page_obj.user_id))

                    if page_obj.role_ids:
                        for role_id in page_obj.role_ids:
                            await UserDao.add_user_role_dao(db, UserRoleModel(user_id=page_obj.user_id, role_id=role_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='修改成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='用户不存在')

    @classmethod
    async def delete_user_services(cls, db: AsyncSession, page_obj: DeleteUserModel):
        """
        删除用户
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.user_ids:
            user_id_list = page_obj.user_ids.split(',')
            try:
                for user_id in user_id_list:
                    user_id_dict = dict(user_id=user_id, update_by=page_obj.update_by, update_time=page_obj.update_time)
                    await UserDao.delete_user_role_dao(db, UserRoleModel(**user_id_dict))
                    await UserDao.delete_user_dao(db, UserModel(**user_id_dict))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='用户id为空')

    @classmethod
    async def get_user_detail_services(cls, db: AsyncSession, user_id: Union[int, str]):
        """
        获取用户详情信息
        :param db:
        :param user_id:
        :return:
        """
        roles = await RoleService.get_role_select_option_services(db)
        if user_id != '':
            query_user = await UserDao.get_user_detail_by_id(db, user_id=user_id)
            role_ids = ','.join([str(row.role_id) for row in query_user.get('user_role_info')])
            role_ids_list = [row.role_id for row in query_user.get('user_role_info')]

            return UserDetailModel(
                data=UserInfoModel(
                    **SqlalchemyUtil.serialize_result(query_user.get('user_basic_info')),
                    role_ids=role_ids,
                    dept=SqlalchemyUtil.serialize_result(query_user.get('user_dept_info')),
                    role=SqlalchemyUtil.serialize_result(query_user.get('user_role_info')),
                ),
                role_ids=role_ids_list,
                roles=roles,
            )
        return UserDetailModel(roles=roles)

    @classmethod
    async def get_user_profile_services(cls, db: AsyncSession, user_id: int):
        """
        获取用户个人详细信息
        :param db:
        :param user_id:
        :return:
        """
        query_user = await UserDao.get_user_detail_by_id(db, user_id=user_id)
        role_ids = ','.join([str(row.role_id) for row in query_user.get('user_role_info')])
        role_group = ','.join([row.role_name for row in query_user.get('user_role_info')])

        return UserProfileModel(
            data=UserInfoModel(
                **SqlalchemyUtil.serialize_result(query_user.get('user_basic_info')),
                role_ids=role_ids,
                dept=SqlalchemyUtil.serialize_result(query_user.get('user_dept_info')),
                role=SqlalchemyUtil.serialize_result(query_user.get('user_role_info')),
            ),
            role_group=role_group,
        )

    @classmethod
    async def reset_user_services(cls, db: AsyncSession, page_obj: ResetUserModel):
        """
        修改用户密码
        :param db:
        :param page_obj:
        :return:
        """
        reset_user = page_obj.model_dump(exclude_unset=True, exclude={'admin'})
        if page_obj.old_password:
            user = (await UserDao.get_user_detail_by_id(db, user_id=page_obj.user_id)).get('user_basic_info')

            if not PwdUtil.verify_password(page_obj.old_password, user.password):
                raise ServiceException(message='修改密码失败，原密码错误')
            elif PwdUtil.verify_password(page_obj.password, user.password):
                raise ServiceException(message='新密码不能与旧密码相同')
            else:
                del reset_user['old_password']
        # if page_obj.sms_code and page_obj.session_id:
        #     del reset_user['sms_code']
        #     del reset_user['session_id']
        try:
            reset_user['password'] = PwdUtil.get_password_hash(page_obj.password)
            await UserDao.edit_user_dao(db, reset_user)
            await db.commit()
            return CrudResponseModel(is_success=True, message='重置成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def batch_import_user_services(
            cls, request: Request, db: AsyncSession, file: UploadFile, update_support: bool,
            current_user: CurrentUserModel, user_data_scope_sql: str, dept_data_scope_sql: str
    ):
        """
        批量导入用户
        :param request:
        :param db:
        :param file: 导入文件对象
        :param update_support: 用户存在时是否更新
        :param current_user: 当前用户对象
        :param user_data_scope_sql: 用户数据权限sql
        :param dept_data_scope_sql: 部门数据权限sql
        :return:
        """
        header_dict = {
            '部门编号': 'dept_id',
            '登录名称': 'user_name',
            '用户名称': 'nick_name',
            '用户邮箱': 'email',
            '手机号码': 'phonenumber',
            '用户性别': 'sex',
            '帐号状态': 'status',
        }

        contents = await file.read()

        df = pd.read_excel(io.BytesIO(contents))
        await file.close()

        df.rename(columns=header_dict, inplace=True)
        add_error_result = []
        count = 0

        try:
            for i, row in df.iterrows():
                count += count
                if row['sex'] == '男':
                    row['sex'] = '0'
                if row['sex'] == '女':
                    row['sex'] = '1'
                if row['sex'] == '未知':
                    row['sex'] = '2'
                if row['status'] == '正常':
                    row['status'] = '0'
                if row['status'] == '停用':
                    row['status'] = '1'

                add_user = UserModel(
                    dept_id=row['dept_id'],
                    user_name=row['user_name'],
                    password=PwdUtil.get_password_hash(
                        await ConfigService.query_config_list_from_cache_services(
                            request.app.state.redis, 'sys.user.initPassword')
                        ),
                    nick_name=row['nick_name'],
                    email=row['email'],
                    phonenumber=str(row['phonenumber']),
                    sex=row['sex'],
                    status=row['status'],
                    create_by=current_user.user.user_name,
                    create_time=datetime.now(),
                    update_by=current_user.user.user_name,
                    update_time=datetime.now(),
                )

                user_info = await UserDao.get_user_by_info(db, UserModel(user_name=row['user_name']))
                if user_info:
                    if update_support:
                        edit_user_model = UserModel(
                            user_id=user_info.user_id,
                            dept_id=row['dept_id'],
                            user_name=row['user_name'],
                            nick_name=row['nick_name'],
                            email=row['email'],
                            phonenumber=str(row['phonenumber']),
                            sex=row['sex'],
                            status=row['status'],
                            update_by=current_user.user.user_name,
                            update_time=datetime.now(),
                        )
                        edit_user_model.validate_fields()
                        # 校验用户是否允许修改
                        await cls.check_user_allowed_services(edit_user_model)
                        # 校验用户是否有操作数据权限
                        if not current_user.user.admin:
                            await cls.check_user_data_scope_services(db, edit_user_model.user_id, user_data_scope_sql)
                            await DeptService.check_dept_data_scope_services(db, edit_user_model.dept_id, dept_data_scope_sql)

                        edit_user = edit_user_model.model_dump(exclude_unset=True)
                        await UserDao.edit_user_dao(db, edit_user)
                    else:
                        add_error_result.append(f"{count}.用户账户{row['user_name']}已存在")
                else:
                    add_user.validate_fields()
                    if not current_user.user.admin:
                        await DeptService.check_dept_data_scope_services(db, add_user.dept_id, dept_data_scope_sql)
                    await UserDao.add_user_dao(db, add_user)
            await db.commit()
            return CrudResponseModel(is_success=True, message='\n'.join(add_error_result))
        except Exception as e:
            await db.rollback()
            raise e

    @staticmethod
    async def get_user_import_template_services():
        """
        获取用户导入模版
        :return:
        """
        header_list = ['部门编码', '登录名称', '用户名称', '用户邮箱', '手机号码', '用户性别', '账户状态']
        selector_header_list = ['用户性别', '账户状态']
        option_list = [{'用户性别': ['男', '女', '未知']}, {'账户状态': ['正常', '停用']}]
        binary_data = get_excel_template(
            header_list=header_list, selector_header_list=selector_header_list, option_list=option_list
        )
        return binary_data

    @staticmethod
    async def export_user_list_services(user_list: List):
        """
        导出用户信息
        :param user_list:
        :return:
        """
        # 映射
        mapping_dict = {
            'user_id': '用户编号',
            'user_name': '用户名称',
            'nick_name': '用户昵称',
            'dept_name': '部门',
            'email': '邮箱地址',
            'phonenumber': '手机号码',
            'sex': '性别',
            'status': '状态',
            'create_by': '创建者',
            'create_time': '创建时间',
            'update_by': '更新者',
            'update_time': '更新时间',
            'remark': '备注',
        }

        for item in user_list:
            if item.get('status') == '0':
                item['status'] = '正常'
            else:
                item['status'] = '异常'

            if item.get('sex') == '0':
                item['sex'] = '男'
            elif item.get('sex') == '1':
                item['sex'] = '女'
            else:
                item['sex'] = '未知'

        new_data = [
            {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)} for item in user_list
        ]
        binary_data = export_list2excel(new_data)
        return binary_data

    @classmethod
    async def get_user_role_allocated_list_services(cls, db: AsyncSession, page_obj: UserRoleQueryModel):
        """
        根据用户id获取已分配角色列表
        :param db:
        :param page_obj:
        :return:
        """
        query_user = await UserDao.get_user_detail_by_id(db, page_obj.user_id)
        role_ids = ','.join([str(row.role_id) for row in query_user.get('user_role_info')])

        user = UserInfoModel(
            **SqlalchemyUtil.serialize_result(query_user.get('user_basic_info')),
            role_ids=role_ids,
            dept=SqlalchemyUtil.serialize_result(query_user.get('user_dept_info')),
            role=SqlalchemyUtil.serialize_result(query_user.get('user_role_info')),
        )
        query_role_list = [
            SelectedRoleModel(**row) for row in await RoleService.get_role_select_option_services(db)
        ]
        for model_a in query_role_list:
            for model_b in user.role:
                if model_a.role_id == model_b.role_id:
                    model_a.flag = True
        result = UserRoleResponseModel(roles=query_role_list, user=user)
        return result

    @classmethod
    async def add_user_role_services(cls, db: AsyncSession, page_obj: CrudUserRoleModel):
        """
        添加用户关联角色信息
        :param db:
        :param page_obj:
        :return:
        """
        # 存在用户ID和角色ID
        if page_obj.user_id and page_obj.role_ids:
            role_id_list = page_obj.role_ids.split(',')
            try:
                await UserDao.delete_user_role_by_user_and_role_dao(db, UserRoleModel(user_id=page_obj.user_id))
                for role_id in role_id_list:
                    await UserDao.add_user_role_dao(db, UserRoleModel(user_id=page_obj.user_id, role_id=role_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='分配成功')
            except Exception as e:
                await db.rollback()
                raise e
        # 存在用户ID, 角色ID不存在
        elif page_obj.user_id and not page_obj.role_ids:
            try:
                await UserDao.delete_user_role_by_user_and_role_dao(db, UserRoleModel(user_id=page_obj.user_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='分配成功')
            except Exception as e:
                await db.rollback()
                raise e
        elif page_obj.user_ids and page_obj.role_id:
            user_id_list = page_obj.user_ids.split(',')
            try:
                for user_id in user_id_list:
                    user_role = await cls.delete_user_role_services(db, UserRoleModel(user_id=user_id, role_id=page_obj.role_id))

                    if user_role:
                        continue
                    else:
                        await UserDao.add_user_role_dao(db, UserRoleModel(user_id=user_id, role_id=page_obj.role_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='不满足新增条件')

    @classmethod
    async def delete_user_role_services(cls, db: AsyncSession, page_obj: CrudUserRoleModel):
        """
        删除用户关联角色信息
        :param db:
        :param page_obj:
        :return:
        """
        if (page_obj.user_id and page_obj.role_id) or (page_obj.user_ids and page_obj.role_id):
            if page_obj.user_id and page_obj.role_id:
                try:
                    await UserDao.delete_user_role_by_user_and_role_dao(
                        db, UserRoleModel(user_id=page_obj.user_id, role_id=page_obj.role_id)
                    )
                    await db.commit()
                    return CrudResponseModel(is_success=True, message='删除成功')
                except Exception as e:
                    await db.rollback()
                    raise e
            elif page_obj.user_ids and page_obj.role_id:
                user_id_list = page_obj.user_ids.split(',')
                try:
                    for user_id in user_id_list:
                        await UserDao.delete_user_role_by_user_and_role_dao(
                            db, UserRoleModel(user_id=user_id, role_id=page_obj.role_id)
                        )
                    await db.commit()
                    return CrudResponseModel(is_success=True, message='删除成功')
                except Exception as e:
                    await db.rollback()
                    raise e
            else:
                raise ServiceException(message='不满足删除条件')
        else:
            raise ServiceException(message='用户角色关联信息为空')

    @classmethod
    async def detail_user_role_services(cls, db: AsyncSession, page_obj: UserRoleModel):
        """
        获取用户角色关联详情信息
        :param db:
        :param page_obj:
        :return:
        """
        user_role = await UserDao.get_user_role_detail(db, page_obj)
        return user_role
