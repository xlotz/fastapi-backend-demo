from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.menu_do import SysMenu
from module_admin.entity.do.role_do import SysRole, SysRoleMenu
from module_admin.entity.do.user_do import SysUser, SysUserRole
from module_admin.entity.vo.menu_vo import MenuModel, MenuQueryModel


class MenuDao:
    """
    菜单管理模块数据库操作层
    """

    @classmethod
    async def get_menu_detail_by_id(cls, db: AsyncSession, menu_id: int):
        """
        根据菜单id 获取菜单详细信息
        :param db:
        :param menu_id:
        :return:
        """
        menu_info = (await db.execute(
            select(SysMenu).where(SysMenu.menu_id == menu_id)
        )).scalars().first()
        return menu_info

    @classmethod
    async def get_menu_detail_by_info(cls, db: AsyncSession, menu: MenuModel):
        """
        根据查询参数获取菜单详情
        :param db:
        :param menu:
        :return:
        """
        menu_info = (await db.execute(
            select(SysMenu).where(
                SysMenu.parent_id == menu.parent_id if menu.parent_id else True,
                SysMenu.menu_name == menu.menu_name if menu.menu_name else True,
                SysMenu.menu_type == menu.menu_type if menu.menu_type else True,
            )
        )).scalars().first()
        return menu_info

    @classmethod
    async def get_menu_list_for_tree(cls, db: AsyncSession, user_id: int, role_list: list):
        """
        根据角色信息获取所在菜单列表信息
        :param db:
        :param user_id:
        :param role_list:
        :return:
        """
        role_id_list = [item.role_id for item in role_list]
        if 1 in role_id_list:
            menu_query_all = (await db.execute(
                select(SysMenu).where(SysMenu.status == '0').order_by(SysMenu.order_num).distinct()
            )).scalars().all()
        else:
            menu_query_all = (await db.execute(
                select(SysMenu).select_from(SysUser).where(
                    SysUser.status == '0', SysUser.del_flag == '0', SysUser.user_id == user_id
                ).join(
                    SysUserRole,
                    SysUser.user_id == SysUserRole.user_id, isouter=True
                ).join(
                    SysRole,
                    and_(SysUserRole.role_id == SysRole.role_id, SysRole.status == '0', SysRole.del_flag == '0'),
                    isouter=True,
                ).join(
                    SysRoleMenu,
                    SysRole.role_id == SysRoleMenu.role_id, isouter=True,
                ).join(
                    SysMenu,
                    and_(SysRoleMenu.menu_id == SysMenu.menu_id, SysMenu.status == '0')
                ).order_by(SysMenu.order_num).distinct()
            )).scalars().all()
        return menu_query_all

    @classmethod
    async def get_menu_list(cls, db: AsyncSession, page_obj: MenuQueryModel, user_id: int, role_list: list):
        """
        根据参数参数获取菜单列表信息
        :param db:
        :param page_obj:
        :param user_id:
        :param role_list:
        :return:
        """
        role_id_list = [item.role_id for item in role_list]
        if 1 in role_id_list:
            menu_query_all = (await db.execute(
                select(SysMenu).where(
                    SysMenu.status == page_obj.status if page_obj.status else True,
                    SysMenu.menu_name.like(f'%{page_obj.menu_name}%') if page_obj.menu_name else True,
                ).order_by(SysMenu.order_num).distinct()
            )).scalars().all()
        else:
            menu_query_all = (await db.execute(
                select(SysMenu).select_from(SysUser).where(
                    SysUser.user_id == user_id, SysUser.status == '0', SysUser.del_flag == '0'
                ).join(
                    SysUserRole,
                    SysUser.user_id == SysUserRole.user_id, isouter=True,
                ).join(
                    SysRole,
                    and_(SysUserRole.role_id == SysRole.role_id, SysRole.status == '0', SysRole.del_flag == '0'),
                    isouter=True,
                ).join(
                    SysRoleMenu,
                    SysRole.role_id == SysRoleMenu.role_id, isouter=True,
                ).join(
                    SysMenu,
                    and_(
                        SysRoleMenu.menu_id == SysMenu.menu_id,
                        SysMenu.status == page_obj.status if page_obj.status else True,
                        SysMenu.menu_name.like(f'%{page_obj.menu_name}%') if page_obj.menu_name else True,
                    )
                ).order_by(SysMenu.order_num).distinct()
            )).scalars().all()

        return menu_query_all

    @classmethod
    async def add_menu_dao(cls, db: AsyncSession, menu: MenuModel):
        """
        添加菜单
        :param db:
        :param menu:
        :return:
        """
        db_menu = SysMenu(**menu.model_dump())
        db.add(db_menu)
        await db.flush()
        return db_menu

    @classmethod
    async def edit_menu_dao(cls, db: AsyncSession, menu: dict):
        """
        修改菜单
        :param db:
        :param menu:
        :return:
        """
        await db.execute(update(SysMenu), [menu])

    @classmethod
    async def delete_menu_dao(cls, db: AsyncSession, menu: MenuModel):
        """
        根据id删除菜单
        :param db:
        :param menu:
        :return:
        """
        await db.execute(delete(SysMenu).where(SysMenu.menu_id.in_([menu.menu_id])))

    @classmethod
    async def count_child_by_menu_id_dao(cls, db: AsyncSession, menu_id: int):
        """
        根据菜单id查询菜单关联子菜单
        :param db:
        :param menu_id:
        :return:
        """
        child_menu_count = (await db.execute(
            select(func.count('*')).select_from(SysMenu).where(SysMenu.parent_id == menu_id)
        )).scalar()
        return child_menu_count

    @classmethod
    async def count_menu_exist_role_dao(cls, db: AsyncSession, menu_id: int):
        """
        根据菜单id查询裁断关联角色的数量
        :param db:
        :param menu_id:
        :return:
        """
        role_count = (await db.execute(
            select(func.count('*')).select_from(SysRoleMenu).where(
                SysRoleMenu.menu_id == menu_id
            )
        )).scalar()
        return role_count

