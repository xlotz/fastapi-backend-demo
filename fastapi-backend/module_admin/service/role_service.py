from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.constant import CommonConstant
from sub_applications.exceptions.exception import ServiceException
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.user_vo import UserInfoModel, UserRolePageQueryModel
from module_admin.entity.vo.role_vo import (
    RoleModel, RolePageQueryModel, AddRoleModel, DeleteRoleModel,
    RoleDeptModel, RoleDeptQueryModel, RoleMenuModel, RoleMenuQueryModel
)
from module_admin.dao.role_dao import RoleDao
from module_admin.dao.user_dao import UserDao
from utils.common_util import export_list2excel, SqlalchemyUtil
from utils.page_util import PageResponseModel


class RoleService:
    """
    角色管理模块服务层
    """

    @classmethod
    async def get_role_select_option_services(cls, db: AsyncSession):
        """
        获取角色列表信息不分页
        :param db:
        :return:
        """
        role_list = await RoleDao.get_role_select_option_dao(db)
        return SqlalchemyUtil.serialize_result(role_list)

    @classmethod
    async def get_role_dept_tree_services(cls, db: AsyncSession, role_id: int):
        """
        根据角色id获取部门树信息
        :param db:
        :param role_id:
        :return:
        """
        role = await cls.get_role_detail_services(db, role_id)
        role_dept_list = await RoleDao.get_role_dept_dao(db, role)
        checked_keys = [row.dept_id for row in role_dept_list]
        result = RoleDeptQueryModel(checked_keys=checked_keys)
        return result

    @classmethod
    async def get_role_list_services(
            cls, db: AsyncSession, query_obj: RolePageQueryModel, data_scope_sql: str, is_page: bool = False
    ):
        """
        获取角色列表信息
        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        role_list = await RoleDao.get_role_list(db, query_obj, data_scope_sql, is_page)
        return role_list

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
    async def check_role_data_scope_services(cls, db: AsyncSession, role_ids: str, data_scope_sql: str):
        """
        校验角色是否有数据权限
        :param db:
        :param role_ids:
        :param data_scope_sql:
        :return:
        """
        role_id_list = role_ids.split(',') if role_ids else []
        if role_id_list:
            for role_id in role_id_list:
                roles = await RoleDao.get_role_list(
                    db, RolePageQueryModel(role_id=int(role_id)), data_scope_sql, is_page=False)
                if roles:
                    continue
                else:
                    raise ServiceException(message='没有权限操作数据')

    @classmethod
    async def check_role_name_unique_services(cls, db: AsyncSession, page_obj: RoleModel):
        """
        校验角色名是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        role_id = -1 if page_obj.role_id is None else page_obj.role_id
        role = await RoleDao.get_role_by_info(db, RoleModel(role_name=page_obj.role_name))
        if role and role.role_id != role_id:
            return CommonConstant.NOT_UNIQUE
        else:
            return CommonConstant.UNIQUE

    @classmethod
    async def check_role_key_unique_services(cls, db: AsyncSession, page_obj: RoleModel):
        """
        校验role_key是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        role_id = -1 if page_obj.role_id is None else page_obj.role_id
        role = await RoleDao.get_role_by_info(db, RoleModel(role_key=page_obj.role_key))
        if role and role.role_id != role_id:
            return CommonConstant.NOT_UNIQUE
        else:
            return CommonConstant.UNIQUE

    @classmethod
    async def add_role_services(cls, db: AsyncSession, page_obj: AddRoleModel):
        """
        添加角色
        :param db:
        :param page_obj:
        :return:
        """
        add_role = RoleModel(**page_obj.model_dump())

        is_unique_name = await cls.check_role_name_unique_services(db, page_obj)
        is_unique_key = await cls.check_role_key_unique_services(db, page_obj)
        if not is_unique_name:
            raise ServiceException(message=f'新增角色{page_obj.role_name}失败，role_name已存在')
        elif not is_unique_key:
            raise ServiceException(message=f'新增角色{page_obj.role_name}失败，role_key已存在')
        else:
            try:
                add_result = await RoleDao.add_role_dao(db, add_role)
                role_id = add_result.role_id
                if page_obj.menu_ids:
                    for menu_id in page_obj.menu_ids:
                        await RoleDao.add_role_menu_dao(db, RoleMenuModel(role_id=role_id, menu_id=menu_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e

    @classmethod
    async def edit_role_services(cls, db: AsyncSession, page_obj: AddRoleModel):
        """
        编辑角色
        :param db:
        :param page_obj:
        :return:
        """
        edit_role = page_obj.model_dump(exclude_unset=True, exclude={'admin'})
        if page_obj.type != 'status':
            del edit_role['menu_ids']
        if page_obj.type == 'status':
            del edit_role['type']

        role_info = await cls.get_role_detail_services(db, edit_role.get('role_id'))

        if role_info:
            if page_obj.type != 'status':
                if not await cls.check_role_name_unique_services(db, page_obj):
                    raise ServiceException(message=f'修改角色{page_obj.role_name}失败，role_name已存在')
                elif not await cls.check_role_key_unique_services(db, page_obj):
                    raise ServiceException(message=f'修改角色{page_obj.role_name}失败，role_key已存在')
            try:
                await RoleDao.edit_role_dao(db, edit_role)
                if page_obj.type != 'status':
                    # 删除角色菜单关联
                    await RoleDao.delete_role_menu_dao(db, RoleMenuModel(role_id=page_obj.role_id))
                    # 添加角色菜单关联
                    if page_obj.menu_ids:
                        for menu_id in page_obj.menu_ids:
                            await RoleDao.add_role_dao(db, RoleMenuModel(role_id=page_obj.role_id, menu_id=menu_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='修改成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='角色不存在')

    @classmethod
    async def role_datascope_services(cls, db: AsyncSession, page_obj: AddRoleModel):
        """
        分配角色数据权限
        :param db:
        :param page_obj:
        :return:
        """
        edit_role = page_obj.model_dump(exclude_unset=True, exclude={'admin': 'dept_ids'})
        role_info = await cls.get_role_detail_services(db, page_obj.role_id)

        if role_info.role_id:
            try:
                await RoleDao.edit_role_dao(db, edit_role)
                await RoleDao.delete_role_dept_dao(db, RoleDeptModel(role_id=page_obj.role_id))

                if page_obj.dept_ids and page_obj.data_scope == '2':
                    for dept_id in page_obj.dept_ids:
                        await RoleDao.add_role_dept_dao(db, RoleDeptModel(role_id=page_obj.role_id, dept_id=dept_id))

                await db.commit()
                return CrudResponseModel(is_success=True, message='分配成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='角色不存在')

    @classmethod
    async def delete_role_services(cls, db: AsyncSession, page_obj: DeleteRoleModel):
        """
        删除角色
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.role_ids:
            role_id_list = page_obj.role_ids.split(',')
            try:
                for role_id in role_id_list:
                    role = await cls.get_role_detail_services(db, int(role_id))
                    # 统计角色分配用户
                    if (await RoleDao.count_user_role_dao(db, int(role_id))) >0:
                        raise ServiceException(message=f'角色{role.role_name}已分配，不能删除')
                    role_id_dict = dict(role_id=role_id, update_by=page_obj.update_by, update_time=page_obj.update_time)
                    # 删除角色菜单关联信息
                    await RoleDao.delete_role_menu_dao(db, RoleMenuModel(**role_id_dict))
                    # 删除角色部门关联信息
                    await RoleDao.delete_role_dept_dao(db, RoleDeptModel(**role_id_dict))
                    # 删除角色信息
                    await RoleDao.delete_role_dao(db, RoleModel(**role_id_dict))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入role_id为空')

    @classmethod
    async def get_role_detail_services(cls, db: AsyncSession, role_id: int):
        """
        根据角色id获取角色详情
        :param db:
        :param role_id:
        :return:
        """
        role = await RoleDao.get_role_detail_by_id(db, role_id=role_id)
        if role:
            result = RoleModel(**SqlalchemyUtil.serialize_result(role))
        else:
            result = RoleModel(**dict())
        return result

    @classmethod
    async def get_role_user_allocated_list_services(
            cls, db: AsyncSession, page_obj: UserRolePageQueryModel, data_scope_sql: str, is_page: bool = False
    ):
        """
        根据角色id获取已分配用户列表
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        # 通过角色id 获取用户列表
        query_user_list = await UserDao.get_user_role_allocated_list_by_role_id(db, page_obj, data_scope_sql, is_page)

        allocated_list = PageResponseModel(**{
            **query_user_list.model_dump(),
            'rows': [UserInfoModel(**row) for row in query_user_list.rows]
            }
        )
        return allocated_list

    @classmethod
    async def get_role_user_unallocated_list_services(
            cls, db: AsyncSession, page_obj: UserRolePageQueryModel, data_scope_sql: str, is_page: bool = False
    ):
        """
        根据角色id获取未分配用户列表
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        query_user_list = await UserDao.get_user_role_unallocated_list_by_role_id(db, page_obj, data_scope_sql, is_page)
        unallocated_list = PageResponseModel(**{
            **query_user_list.model_dump(),
            'rows': [UserInfoModel(**row) for row in query_user_list.rows]
        })
        return unallocated_list

    @staticmethod
    async def export_role_list_services(role_list: List):
        """
        导出角色列表信息
        :param role_list:
        :return:
        """

        # 新建映射
        mapping_dict = {
            'role_id': '角色编号',
            'role_name': '角色名称',
            'role_key': '权限字符',
            'role_sort': '显示顺序',
            'status': '状态',
            'create_by': '创建者',
            'create_time': '创建时间',
            'update_by': '更新者',
            'update_time': '更新时间',
            'remark': '备注',
        }

        for item in role_list:
            if item.get('status') == '0':
                item['status'] = '正常'
            else:
                item['status'] = '停用'

        new_data = [
            {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)}
            for item in role_list
        ]
        binary_data = export_list2excel(new_data)
        return binary_data
