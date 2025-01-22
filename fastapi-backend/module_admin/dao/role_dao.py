from datetime import datetime, time
from sqlalchemy import select, update, delete, and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.do.menu_do import SysMenu
from module_admin.entity.do.role_do import SysRole, SysRoleMenu, SysRoleDept
from module_admin.entity.do.user_do import SysUser, SysUserRole
from module_admin.entity.vo.role_vo import RoleModel, RoleDeptModel, RoleMenuModel, RolePageQueryModel
from utils.page_util import PageUtil


class RoleDao:
    """
    角色管理模块数据库操作层
    """

    @classmethod
    async def get_role_by_name(cls, db: AsyncSession, role_name):
        """
        根据角色名获取角色信息
        :param db:
        :param role_name:
        :return:
        """
        query_role_result = (await db.execute(
            select(SysRole).where(SysRole.status == '0', SysRole.del_flag == '0', SysRole.role_name == role_name)
        )).scalars().first()
        return query_role_result

    @classmethod
    async def get_role_by_id(cls, db: AsyncSession, role_id):
        """
        通过id获取角色信息
        :param db:
        :param role_id:
        :return:
        """
        query_role_result = (await db.execute(
            select(SysRole).where(SysRole.status == '0', SysRole.del_flag == '0', SysRole.role_id == role_id)
        )).scalars().first()
        return query_role_result

    @classmethod
    async def get_role_by_info(cls, db: AsyncSession, role: RoleModel):
        """
        根据参数获取角色信息
        :param db:
        :param role:
        :return:
        """
        query_role_result = (await db.execute(
            select(SysRole)
            .where(
                SysRole.del_flag == '0',
                SysRole.role_name == role.role_name if role.role_name else True,
                SysRole.role_key == role.role_key if role.role_key else True,
            ).order_by(desc(SysRole.create_time)).distinct()
        )).scalars().first()
        return query_role_result

    @classmethod
    async def get_role_detail_by_id(cls, db: AsyncSession, role_id):
        """
        根据id获取在用角色信息
        :param db:
        :param role_id:
        :return:
        """
        role_info = (await db.execute(
            select(SysRole).where(SysRole.del_flag == '0', SysRole.status == '0', SysRole.role_id == role_id).distinct()
        )).scalars().first()
        return role_info

    @classmethod
    async def get_role_select_option_dao(cls, db: AsyncSession):
        """
        获取编辑页面对应的再用角色列表
        :param db:
        :return:
        """
        role_info = (await db.execute(
            select(SysRole).where(SysRole.role_id != 1, SysRole.status == '0', SysRole.del_flag == '0')
        )).scalars().all()
        return role_info

    @classmethod
    async def get_role_list(cls, db: AsyncSession, query_obj: RolePageQueryModel, data_scope_sql, is_page=False):
        """
        根据参数获取角色列表，分页
        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        query = select(SysRole)\
            .join(SysUserRole, SysUserRole.role_id == SysRole.role_id, isouter=True)\
            .join(SysUser, SysUser.user_id == SysUserRole.user_id, isouter=True)\
            .join(SysDept, SysDept.dept_id == SysUser.dept_id, isouter=True)\
            .where(
                SysRole.del_flag == '0',
                SysRole.role_id == query_obj.role_id if query_obj.role_id is not None else True,
                SysRole.role_name.like(f'%{query_obj.role_name}%') if query_obj.role_name else True,
                SysRole.role_key.like(f'%{query_obj.role_key}%') if query_obj.role_key else True,
                SysRole.status == query_obj.status if query_obj.status else True,
                SysRole.create_time.between(
                    datetime.combine(datetime.strptime(query_obj.begin_time, '%Y-%m-%d'), time(00, 00, 00)),
                    datetime.combine(datetime.strptime(query_obj.end_time, '%Y-%m-%d'), time(23, 59, 59)),
                ) if query_obj.begin_time and query_obj.end_time else True,
                eval(data_scope_sql),
                )\
            .order_by(SysRole.role_sort).distinct()
        role_list = await PageUtil.paginate(db, query, query_obj.page_num, query_obj.page_size, is_page)
        return role_list

    @classmethod
    async def add_role_dao(cls, db: AsyncSession, role: RoleModel):
        """
        新增角色
        :param db:
        :param role:
        :return:
        """
        db_role = SysRole(**role.model_dump(exclude={'admin'}))
        db.add(db_role)
        await db.flush()
        return db_role

    @classmethod
    async def edit_role_dao(cls, db: AsyncSession, role: dict):
        """
        修改角色
        :param db:
        :param role:
        :return:
        """
        await db.execute(update(SysRole), [role])

    @classmethod
    async def delete_role_dao(cls, db: AsyncSession, role: RoleModel):
        """
        删除角色
        :param db:
        :param role:
        :return:
        """
        await db.execute(
            update(SysRole)
            .where(SysRole.role_id == role.role_id)
            .values(del_flag='2', update_by=role.update_by, update_time=datetime.now())
        )

    @classmethod
    async def get_role_menu_dao(cls, db: AsyncSession, role: RoleModel):
        """
        根据角色id获取角色菜单关联信息
        :param db:
        :param role:
        :return:
        """
        role_menu_all_sql = select(SysMenu)\
            .join(SysRoleMenu, SysRoleMenu.menu_id == SysMenu.menu_id)\
            .where(
            SysRoleMenu.role_id == role.role_id,
            ~SysMenu.menu_id.in_(
                select(SysMenu.parent_id).select_from(SysMenu)
                .join(SysRoleMenu, and_(
                    SysRoleMenu.menu_id == SysMenu.menu_id, SysRoleMenu.role_id == role.role_id
                ))
            ) if role.menu_check_strictly else True,
        ).order_by(SysMenu.parent_id, SysMenu.order_num)

        role_menu_all = (await db.execute(role_menu_all_sql)).scalars().all()
        return role_menu_all

    @classmethod
    async def add_role_menu_dao(cls, db: AsyncSession, role_menu: RoleMenuModel):
        """
        添加角色菜单关联信息
        :param db:
        :param role_menu:
        :return:
        """
        db_role_menu = SysRoleMenu(**role_menu.model_dump())
        db.add(db_role_menu)
        await db.flush()

    @classmethod
    async def delete_role_menu_dao(cls, db: AsyncSession, role_menu: RoleMenuModel):
        """
        根据id删除角色菜单关联信息
        :param db:
        :param role_menu:
        :return:
        """
        await db.execute(delete(SysRoleMenu).where(SysRoleMenu.menu_id.in_([role_menu.menu_id])))

    @classmethod
    async def get_role_dept_dao(cls, db: AsyncSession, role: RoleModel):
        """
        根据id获取角色和部门的关联信息
        :param db:
        :param role:
        :return:
        """
        db_role_dept_sql = select(SysDept)\
            .join(SysRoleDept, SysRoleDept.dept_id == SysDept.dept_id)\
            .where(
                SysRoleDept.role_id == role.role_id,
                ~SysDept.dept_id.in_(
                    select(SysDept.parent_id).select_from(SysDept)
                    .join(SysRoleDept, and_(
                        SysRoleDept.dept_id == SysDept.dept_id, SysRoleDept.role_id == role.role_id
                    ))
                ) if role.dept_check_strictly else True,
        ).order_by(SysDept.parent_id, SysDept.order_num)
        print(db_role_dept_sql)

        db_role_dept = (await db.execute(db_role_dept_sql)).scalars().all()
        return db_role_dept

    @classmethod
    async def add_role_dept_dao(cls, db: AsyncSession, role_dept: RoleDeptModel):
        """
        添加角色和部门关联信息
        :param db:
        :param role_dept:
        :return:
        """
        db_role_dept = SysRoleDept(**role_dept.model_dump())
        db.add(db_role_dept)
        await db.flush()

    @classmethod
    async def delete_role_dept_dao(cls, db: AsyncSession, role_dept: RoleDeptModel):
        """
        根据角色id删除角色与部门的关联关系
        :param db:
        :param role_dept:
        :return:
        """
        await db.execute(delete(SysRoleDept).where(SysRoleDept.role_id.in_([role_dept.role_id])))

    @classmethod
    async def count_user_role_dao(cls, db: AsyncSession, role_id):
        """
        根据角色id统计角色关联用户数量
        :param db:
        :param role_id:
        :return:
        """
        user_count = (await db.execute(
            select(func.count('*')).select_from(SysUserRole)
            .where(SysUserRole.role_id == role_id))
        ).scalar()

        return user_count