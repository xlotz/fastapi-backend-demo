from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal
from config.constant import CommonConstant
from sub_applications.exceptions.exception import ServiceException
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.role_vo import (
    AddRoleModel, DeleteRoleModel,
    RoleDeptModel, RoleDeptQueryModel,
    RoleMenuModel, RoleMenuQueryModel,
    RoleModel, RolePageQueryModel,
)
from module_admin.entity.vo.user_vo import UserInfoModel, UserRolePageQueryModel
from module_admin.dao.role_dao import RoleDao
from module_admin.dao.user_dao import UserDao
from utils.common_util import CamelCaseUtil, export_list2excel
from utils.page_util import PageResponseModel


class RoleService:
    """
    角色服务层
    """

    @classmethod
    async def get_role_select_option_services(cls, db: AsyncSession):
        """
        获取角色列表，不分页
        :param db:
        :return:
        """
        role_list_result = await RoleDao.get_role_select_option_dao(db)
        return CamelCaseUtil.transform_result(role_list_result)

    @classmethod
    async def get_role_dept_tree_services(cls, db: AsyncSession, role_id):
        """
        根据角色id获取部门树
        :param db:
        :param role_id:
        :return:
        """
        role = await cls.role_detail_services(db, role_id)
        role_dept_list = await RoleDao.get_role_dept_dao(db, role)
        checked_keys = [row.dept_id for row in role_dept_list]
        result = RoleDeptQueryModel(checkedKeys=checked_keys)

        return result

    @classmethod
    async def get_role_list_services(cls, db: AsyncSession, query_obj: RolePageQueryModel, data_scope_sql, is_page=False):
        """
        获取角色列表信息
        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        role_list_result = await RoleDao.get_role_list(db, query_obj,data_scope_sql, is_page)
        return role_list_result

    @classmethod
    async def check_role_allowed_services(cls, check_role: RoleModel):
        """
        校验角色是否允许操作
        :param check_role:
        :return:
        """
        if check_role.admin:
            raise ServiceException(message='不允许操作超级管理员角色')
        else:
            return CrudResponseModel(is_success=True, message='校验通过')

    @classmethod
    async def check_role_data_scope_services(cls, db: AsyncSession, role_ids, data_scope_sql):
        """
        校验绝世是否有数据权限
        :param db:
        :param role_ids:
        :param data_scope_sql:
        :return:
        """
        role_id_list = role_ids.split(',')
        if role_id_list:
            for role_id in role_id_list:
                roles = await RoleDao.get_role_list(
                    db, RolePageQueryModel(roleId=int(role_id)), data_scope_sql, is_page=False
                )
                if roles:
                    continue
                else:
                    raise ServiceException(message='没有权限访问角色数据')

    @classmethod
    async def check_role_name_unique_services(cls, db: AsyncSession, page_obj: RoleModel):
        """
        判断角色名是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        role_id = -1 if page_obj.role_id is None else page_obj.role_id
        role = await RoleDao.get_role_by_info(db, RoleModel(roleName=page_obj.role_name))
        if role and role.role_id != role_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def check_role_key_unique_services(cls, db: AsyncSession, page_obj: RoleModel):
        """
        判断角色权限是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        role_id = -1 if page_obj.role_id is None else page_obj.role_id
        role = await RoleDao.get_role_by_info(db, RoleModel(roleKey=page_obj.role_key))
        if role and role.role_id != role_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_role_services(cls, db: AsyncSession, page_obj: AddRoleModel):
        """
        添加角色
        :param db:
        :param page_obj:
        :return:
        """
        add_role = RoleModel(**page_obj.model_dump(by_alias=True))
        # 校验角色
        if not await cls.check_role_name_unique_services(db, page_obj):
            raise ServiceException(message=f'新增角色{db.role_name}失败，角色名称已存在')
        elif not await cls.check_role_key_unique_services(db, page_obj):
            raise ServiceException(message=f'新增角色{page_obj.role_name}失败，角色权限已存在')
        else:
            try:
                add_result = await RoleDao.add_role_dao(db, add_role)
                role_id = add_result.role_id
                if page_obj.menu_ids:
                    for menu in page_obj.menu_ids:
                        await RoleDao.add_role_menu_dao(db, RoleMenuModel(roleId=role_id, menuId=menu))
                await db.commit()
                return CrudResponseModel(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e

    @classmethod
    async def edit_role_services(cls, db: AsyncSession, page_obj: AddRoleModel):
        """
        修改角色
        :param db:
        :param page_obj:
        :return:
        """
        edit_role = page_obj.model_dump(exclude_unset=True, exclude={'admin'})
        if page_obj.type != 'status':
            del edit_role['menu_ids']
        if page_obj.type == 'status':
            del edit_role['type']

        role_info = await cls.role_detail_services(db, edit_role.get('role_id'))

        if role_info:
            if page_obj.type != 'status':
                if not await cls.check_role_name_unique_services(db, page_obj):
                    raise ServiceException(message=f'修改角色{page_obj.role_name}失败，角色名称已存在')
                elif not await cls.check_role_key_unique_services(db, page_obj):
                    raise ServiceException(message=f'修改角色{page_obj.role_name}失败，角色权限已存在')
            try:
                await RoleDao.edit_role_dao(db, edit_role)
                if page_obj.type != 'status':
                    await RoleDao.delete_role_menu_dao(db, RoleMenuModel(roleId=page_obj.role_id))
                    if page_obj.menu_ids:
                        for menu in page_obj.menu_ids:
                            await RoleDao.add_role_menu_dao(db, RoleMenuModel(roleId=page_obj.role_id, menuId=menu))
                await db.commit()
                return CrudResponseModel(is_success=True, message='更新成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='角色不存在')

    @classmethod
    async def delete_role_services(cls, db: AsyncSession, page_obj: DeleteRoleModel):
        """
        删除角色信息
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.role_ids:
            role_id_list = page_obj.role_ids.split(',')
            try:
                for role_id in role_id_list:
                    role = await cls.role_detail_services(db, int(role_id))
                    if (await RoleDao.count_user_role_dao(db, int(role_id)))>0:
                        raise ServiceException(message=f'角色{role.role_name}已分配，不能删除')
                    role_id_dict = dict(roleId=role_id, updateBy=page_obj.update_by, updateTime=page_obj.update_time)
                    await RoleDao.delete_role_menu_dao(db, RoleMenuModel(**role_id_dict))
                    await RoleDao.delete_role_dept_dao(db, RoleDeptModel(**role_id_dict))
                    await RoleDao.delete_role_dao(db, RoleModel(**role_id_dict))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入角色id为空')

    @classmethod
    async def role_datascope_services(cls, db: AsyncSession, page_obj: AddRoleModel):
        """
        分配角色数据权限
        :param db:
        :param page_obj:
        :return:
        """
        edit_role = page_obj.model_dump(exclude_unset=True, exclude={'admin', 'dept_ids'})
        role_info = await cls.role_detail_services(db, page_obj.role_id)
        if role_info.role_id:
            try:
                await RoleDao.edit_role_dao(db, edit_role)
                await RoleDao.delete_role_dept_dao(db, RoleDeptModel(roleId=page_obj.role_id))
                if page_obj.dept_ids and page_obj.data_scope == '2':
                    for dept in page_obj.dept_ids:
                        await RoleDao.add_role_dept_dao(db, RoleDeptModel(roleId=page_obj.role_id, deptId=dept))
                await db.commit()
                return CrudResponseModel(is_success=True, message='分配成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='角色不存在')

    @classmethod
    async def role_detail_services(cls, db: AsyncSession, role_id):
        """
        通过id获取角色详情
        :param db:
        :param role_id:
        :return:
        """
        role = await RoleDao.get_role_detail_by_id(db, role_id)
        if role:
            result = RoleModel(**CamelCaseUtil.transform_result(role))
        else:
            result = RoleModel(**dict())
        return result

    @staticmethod
    async def export_role_list_services(role_list):
        """
        导出角色列表
        :param role_list:
        :return:
        """
        # 创建一个映射字典，将英文键映射到中文键
        mapping_dict = {
            'roleId': '角色编号',
            'roleName': '角色名称',
            'roleKey': '权限字符',
            'roleSort': '显示顺序',
            'status': '状态',
            'createBy': '创建者',
            'createTime': '创建时间',
            'updateBy': '更新者',
            'updateTime': '更新时间',
            'remark': '备注',
        }

        data = role_list

        for item in data:
            if item.get('status') == '0':
                item['status'] = '正常'
            else:
                item['status'] = '停用'
        new_data = [
            {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)} for item in data
        ]
        binary_data = export_list2excel(new_data)

        return binary_data

    @classmethod
    async def get_role_user_allocated_list_services(
            cls, db: AsyncSession, page_obj: UserRolePageQueryModel, data_scope_sql, is_page=False
    ):
        """
        根据角色id 获取已分配的用户列表
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        query_user_list = await UserDao.get_user_role_allocated_list_by_role_id(db, page_obj, data_scope_sql, is_page)
        allocated_list = PageResponseModel(
            **{
                **query_user_list.model_dump(by_alias=True),
                'rows': [UserInfoModel(**row) for row in query_user_list.rows]
            }
        )
        return allocated_list

    @classmethod
    async def get_role_user_unallocated_list_services(
            cls, db: AsyncSession, page_obj: UserRolePageQueryModel, data_scope_sql, is_page=False
    ):
        """
        根据角色id获取未被分配的用户列表
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        query_user_list = await UserDao.get_user_role_unallocated_list_by_role_id(db, page_obj, data_scope_sql, is_page)
        unallocated_list = PageResponseModel(
            **{
                **query_user_list.model_dump(by_alias=True),
                'rows': [UserInfoModel(**row) for row in query_user_list.rows]
            }
        )
        return unallocated_list