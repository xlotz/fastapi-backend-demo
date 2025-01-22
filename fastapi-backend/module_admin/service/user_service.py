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
    AddUserModel, DeleteUserModel, EditUserModel,
    CrudUserRoleModel, CurrentUserModel,
    ResetUserModel, SelectedRoleModel,
    UserInfoModel, UserDetailModel, UserModel, UserPageQueryModel,
    UserProfileModel, UserRoleModel, UserRoleQueryModel, UserRolePageQueryModel,
    UserRoleResponseModel
)
from module_admin.service.dept_service import DeptService
from module_admin.service.role_service import RoleService
from utils.common_util import CamelCaseUtil, export_list2excel, get_excel_template
from utils.page_util import PageResponseModel
from utils.pwd_util import PwdUtil


class UserService:
    """
    用户管理模块服务层
    """

    @classmethod
    async def get_user_list_services(cls, db: AsyncSession, query_obj: UserPageQueryModel, data_scope_sql, is_page=True):
        """

        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        query_result = await UserDao.get_user_list(db, query_obj, data_scope_sql, is_page)
        if is_page:
            user_list_result = PageResponseModel(
                **{
                    **query_result.model_dump(by_alias=True),
                    'rows': [{**row[0], 'dept': row[1]} for row in query_result.rows]
                }
            )
        else:
            user_list_result = []
            if query_result:
                user_list_result = [{**row[0], 'dept': row[1]} for row in query_result.rows]

        return user_list_result

    @classmethod
    async def check_user_allowed_services(cls, check_user: UserModel):
        """
        检查用户是否允许操作
        :param check_user:
        :return:
        """
        if check_user.admin:
            raise ServiceException(message='不允许操作超级管理员用户')
        else:
            return CrudResponseModel(is_success=True, message='校验通过')

    @classmethod
    async def check_user_data_scope_services(cls, db: AsyncSession, user_id, data_scope_sql):
        """
        校验用户数据权限
        :param db:
        :param user_id:
        :param data_scope_sql:
        :return:
        """
        users = await UserDao.get_user_list(db, UserPageQueryModel(userId=user_id), data_scope_sql, is_page=False)
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
        user = await UserDao.get_user_by_info(db, UserModel(userName=page_obj.user_name))
        if user and user.user_id != user_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def check_phonenumber_unique_services(cls, db: AsyncSession, page_obj: UserModel):
        """
        校验用户手机是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        user_id = -1 if page_obj.user_id is None else page_obj.user_id
        user = await UserDao.get_user_by_info(db, UserModel(phoneNumber=page_obj.phonenumber))
        if user and user.user_id != user_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def check_email_unique_services(cls, db: AsyncSession, page_obj: UserModel):
        """
        校验email是否唯一
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
        add_user = UserModel(**page_obj.model_dump(by_alias=True))
        if not await cls.check_user_name_unique_services(db, page_obj):
            raise ServiceException(message=f'新增用户{page_obj.user_name}失败，登录账号已存在')
        elif page_obj.phonenumber and not await cls.check_phonenumber_unique_services(db, page_obj):
            raise ServiceException(message=f'新增用户{page_obj.user_name}失败，手机号码已存在')
        elif page_obj.email and not await cls.check_email_unique_services(db, page_obj):
            raise ServiceException(message=f'新增用户{page_obj.user_name}失败，邮箱账号已存在')
        else:
            try:
                add_result = await UserDao.add_user_dao(db, add_user)
                user_id = add_result.user_id
                if page_obj.role_ids:
                    for role in page_obj.role_ids:
                        await UserDao.add_user_role_dao(db, UserRoleModel(userId=user_id, roleId=role))

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

        if page_obj.type == 'status' or page_obj.type == 'avatar' or page_obj.type == 'pwd':
            del edit_user['type']

        user_info = await cls.user_detail_services(db, edit_user.get('user_id'))

        if user_info.data and user_info.data.user_id:
            if page_obj.type != 'status' and page_obj.type != 'avatar' and page_obj.type != 'pwd':
                if not (await cls.check_user_name_unique_services(db, page_obj)):
                    raise ServiceException(message=f'修改用户{page_obj.user_name}失败, 登录账户已存在')
                elif page_obj.phonenumber and not (await cls.check_phonenumber_unique_services(db, page_obj)):
                    raise ServiceException(message=f'修改用户{page_obj.user_name}失败，手机号码已存在')
                elif page_obj.email and not (await cls.check_email_unique_services(db, page_obj)):
                    raise ServiceException(message=f'修改用户{page_obj.user_name}失败，email已存在')
            try:
                await UserDao.edit_user_dao(db, edit_user)
                if page_obj.type != 'status' and page_obj.type != 'avatar' and page_obj.type != 'pwd':
                    await UserDao.delete_user_role_dao(db, UserRoleModel(userId=page_obj.user_id))
                    if page_obj.role_ids:
                        for role in page_obj.role_ids:
                            await UserDao.add_user_dao(db, UserRoleModel(userId=page_obj.user_id, roleId=role))
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
        删除用户信息
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.user_ids:
            user_id_list = page_obj.user_ids.split(',')
            try:
                for user_id in user_id_list:
                    user_id_dict = dict(userId=user_id, updateBy=page_obj.update_by, updateTime=page_obj.update_time)
                    await UserDao.delete_user_role_dao(db, UserRoleModel(**user_id_dict))
                    await UserDao.delete_user_dao(db, UserModel(**user_id_dict))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入用户id为空')

    @classmethod
    async def user_detail_services(cls, db: AsyncSession, user_id: Union[int, str]):
        """
        获取用户详情
        :param db:
        :param user_id:
        :return:
        """
        roles = await RoleService.get_role_select_option_services(db)
        if user_id != '':
            query_user = await UserDao.get_user_detail_by_id(db, user_id)
            role_ids = ','.join([str(row.role_id) for row in query_user.get('user_role_info')])
            role_ids_list = [row.role_id for row in query_user.get('user_role_info')]

            return UserDetailModel(
                data=UserInfoModel(
                    **CamelCaseUtil.transform_result(query_user.get('user_basic_info')),
                    roleIds=role_ids,
                    dept=CamelCaseUtil.transform_result(query_user.get('user_dept_info')),
                    role=CamelCaseUtil.transform_result(query_user.get('user_role_info')),
                ),
                roleIds=role_ids_list,
                roles=roles,
            )
        return UserDetailModel(roles=roles)

    @classmethod
    async def user_profile_services(cls, db: AsyncSession, user_id: Union[int, str]):
        """
        获取用户详情
        :param db:
        :param user_id:
        :return:
        """
        roles = await RoleService.get_role_select_option_services(db)
        if user_id != '':
            query_user = await UserDao.get_user_detail_by_id(db, user_id)
            role_ids = ','.join([str(row.role_id) for row in query_user.get('user_role_info')])
            role_ids_list = [row.role_id for row in query_user.get('user_role_info')]

            return UserDetailModel(
                data=UserInfoModel(
                    **CamelCaseUtil.transform_result(query_user.get('user_basic_info')),
                    roleIds=role_ids,
                    dept=CamelCaseUtil.transform_result(query_user.get('user_dept_info')),
                    role=CamelCaseUtil.transform_result(query_user.get('user_role_info')),
                ),
                roleIds=role_ids_list,
                roles=roles,
            )
        return UserDetailModel(roles=roles)

    @classmethod
    async def reset_user_services(cls, db: AsyncSession, page_obj: ResetUserModel):
        """
        重置用户密码
        :param db:
        :param page_obj:
        :return:
        """
        reset_user = page_obj.model_dump(exclude_unset=True, exclude={'admin'})
        if page_obj.old_password:
            user = (await UserDao.get_user_detail_by_id(db, page_obj.user_id)).get('user_basic_info')

            if not PwdUtil.verify_password(page_obj.old_password, user.password):
                raise ServiceException(message='修改密码失败，旧密码错误')
            elif PwdUtil.verify_password(page_obj.password, user.password):
                raise ServiceException(message='新密码不能与旧密码相同')
            else:
                del reset_user['old_password']

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
            cls, request: Request, db: AsyncSession, file: UploadFile, update_support,
            current_user: CurrentUserModel,
            user_data_scope_sql, dept_data_scope_sql,
    ):
        """
        批量导入用户
        :param request:
        :param db:
        :param file:
        :param current_user:
        :param user_data_scope_sql:
        :param dept_data_scope_sql:
        :return:
        """

        pass
        # header_dict = {
        #     '部门编号': 'dept_id',
        #     '登录名称': 'user_name',
        #     '用户名称': 'nick_name',
        #     '用户邮箱': 'email',
        #     '手机号码': 'phonenumber',
        #     '用户性别': 'sex',
        #     '帐号状态': 'status',
        # }
        #
        # contents = await file.read()
        # df = pd.read_excel(io.BytesIO(contents))
        # await file.close()
        # df.rename(columns=header_dict, inplace=True)
        # add_error_result = []
        # count = 0
        # try:
        #     for index, row in df.iterrows():
        #         count += 1
        #         if row['sex'] == '男':
        #             row['sex'] = '0'
        #         if row['sex'] == '女':
        #             row['sex'] = '1'
        #         if row['sex'] == '未知':
        #             row['sex'] = '2'
        #         if row['status'] == '正常':
        #             row['status'] = '0'
        #         if row['status'] == '停用':
        #             row['status'] = '1'
        #         add_user = UserModel(
        #             deptId=row['dept_id'],
        #             userName=row['user_name'],
        #             password=PwdUtil.get_password_hash(
        #                 await ConfigService.query_config_list_from_cache_services(
        #                     request.app.state.redis, 'sys.user.initPassword'
        #                 )
        #             ),
        #             nickName=row['nick_name'],
        #             email=row['email'],
        #             phonenumber=str(row['phonenumber']),
        #             sex=row['sex'],
        #             status=row['status'],
        #             createBy=current_user.user.user_name,
        #             createTime=datetime.now(),
        #             updateBy=current_user.user.user_name,
        #             updateTime=datetime.now(),
        #         )
        #         user_info = await UserDao.get_user_by_info(db, UserModel(userName=row['user_name']))
        #         if user_info:
        #             if update_support:
        #                 edit_user_model = UserModel(
        #                     userId=user_info.user_id,
        #                     deptId=row['dept_id'],
        #                     userName=row['user_name'],
        #                     nickName=row['nick_name'],
        #                     email=row['email'],
        #                     phonenumber=str(row['phonenumber']),
        #                     sex=row['sex'],
        #                     status=row['status'],
        #                     updateBy=current_user.user.user_name,
        #                     updateTime=datetime.now(),
        #                 )
        #                 edit_user_model.validate_fields()
        #                 await cls.check_user_allowed_services(edit_user_model)
        #                 if not current_user.user.admin:
        #                     await cls.check_user_data_scope_services(
        #                         db, edit_user_model.user_id, user_data_scope_sql
        #                     )
        #                     await DeptService.check_dept_data_scope_services(
        #                         db, edit_user_model.dept_id, dept_data_scope_sql
        #                     )
        #                 edit_user = edit_user_model.model_dump(exclude_unset=True)
        #                 await UserDao.edit_user_dao(db, edit_user)
        #             else:
        #                 add_error_result.append(f"{count}.用户账号{row['user_name']}已存在")
        #         else:
        #             add_user.validate_fields()
        #             if not current_user.user.admin:
        #                 await DeptService.check_dept_data_scope_services(
        #                     db, add_user.dept_id, dept_data_scope_sql
        #                 )
        #             await UserDao.add_user_dao(db, add_user)
        #     await db.commit()
        #     return CrudResponseModel(is_success=True, message='\n'.join(add_error_result))
        # except Exception as e:
        #     await db.rollback()
        #     raise e

    @staticmethod
    async def get_user_import_template_services():
        """
        获取用户导入模版
        :return:
        """
        header_list = ['部门编号', '登录名称', '用户名称', '用户邮箱', '手机号码', '用户性别', '帐号状态']
        selector_header_list = ['用户性别', '帐号状态']
        option_list = [{'用户性别': ['男', '女', '未知']}, {'帐号状态': ['正常', '停用']}]
        binary_data = get_excel_template(
            header_list=header_list, selector_header_list=selector_header_list, option_list=option_list
        )

        return binary_data

    @staticmethod
    async def export_user_list_services(user_list):
        """
        到处用户信息
        :param user_list:
        :return:
        """
        # 创建一个映射字典，将英文键映射到中文键
        mapping_dict = {
            'userId': '用户编号',
            'userName': '用户名称',
            'nickName': '用户昵称',
            'deptName': '部门',
            'email': '邮箱地址',
            'phonenumber': '手机号码',
            'sex': '性别',
            'status': '状态',
            'createBy': '创建者',
            'createTime': '创建时间',
            'updateBy': '更新者',
            'updateTime': '更新时间',
            'remark': '备注',
        }

        data = user_list

        for item in data:
            if item.get('status') == '0':
                item['status'] = '正常'
            else:
                item['status'] = '停用'
            if item.get('sex') == '0':
                item['sex'] = '男'
            elif item.get('sex') == '1':
                item['sex'] = '女'
            else:
                item['sex'] = '未知'
        new_data = [
            {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)} for item in data
        ]
        binary_data = export_list2excel(new_data)

        return binary_data

    @classmethod
    async def get_user_role_allocated_list_services(cls, db: AsyncSession, page_obj: UserRoleQueryModel):
        """
        根据用户id获取已分配的角色列表
        :param db:
        :param page_obj:
        :return:
        """
        query_user = await UserDao.get_user_detail_by_id(db, page_obj.user_id)
        role_ids = ','.join([str(row.role_id) for row in query_user.get('user_role_info')])
        user = UserInfoModel(
            **CamelCaseUtil.transform_result(query_user.get('user_basic_info')),
            roleIds=role_ids,
            dept=CamelCaseUtil.transform_result(query_user.get('user_dept_info')),
            role=CamelCaseUtil.transform_result(query_user.get('user_role_info')),
        )
        query_role_list = [
            SelectedRoleModel(**row) for row in (await RoleService.get_role_select_option_services(db))
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
        添加用户角色关联
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.user_id and page_obj.role_ids:
            role_id_list = page_obj.role_ids.split(',')
            try:
                await UserDao.delete_user_role_by_user_and_role_dao(db, UserRoleModel(userId=page_obj.user_id))
                for role_id in role_id_list:
                    await UserDao.add_user_role_dao(db, UserRoleModel(userId=page_obj.user_id, roleId=role_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='分配成功')
            except Exception as e:
                await db.rollback()
                raise e
        elif page_obj.user_id and not page_obj.role_ids:
            try:
                await UserDao.delete_user_role_by_user_and_role_dao(db, UserRoleModel(userId=page_obj.user_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='分配成功')
            except Exception as e:
                await db.rollback()
                raise e
        elif page_obj.user_ids and page_obj.role_id:
            user_id_list = page_obj.user_ids.split(',')
            try:
                for user_id in user_id_list:
                    user_role = await cls.detail_user_role_services(
                        db, UserRoleModel(userId=user_id, roleId=page_obj.role_id)
                    )
                    if user_role:
                        continue
                    else:
                        await UserDao.add_user_role_dao(db, UserRoleModel(userId=user_id, roleId=page_obj.role_id))
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
                    await UserDao.delete_user_role_by_user_and_role_dao(db, UserRoleModel(userId=page_obj.user_id,
                                                                                          roleId=page_obj.role_id))
                    await db.commit()
                    return CrudResponseModel(is_success=True, message='删除成功')
                except Exception as e:
                    await db.commit()
                    raise e
            elif page_obj.user_ids and page_obj.role_id:
                user_id_list = page_obj.user_ids.split(',')
                try:
                    for user_id in user_id_list:
                        await UserDao.delete_user_role_by_user_and_role_dao(db, UserRoleModel(userId=user_id,
                                                                                              roleId=page_obj.role_id))
                    await db.commit()
                    return CrudResponseModel(is_success=True, message='删除成功')
                except Exception as e:
                    await db.rollback()
                    raise e
            else:
                raise ServiceException(message='不能满足删除条件')
        else:
            raise ServiceException(message='传入用户角色关联信息为空')

    @classmethod
    async def detail_user_role_services(cls, db: AsyncSession, page_obj: UserRoleModel):
        """
        获取用户关联角色详细信息
        :param db:
        :param page_obj:
        :return:
        """

        user_role = await UserDao.get_user_role_detail(db, page_obj)
        return user_role