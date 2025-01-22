from datetime import datetime, time
from sqlalchemy import select, update, delete, desc, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.do.menu_do import SysMenu
from module_admin.entity.do.role_do import SysRole, SysRoleDept, SysRoleMenu
from module_admin.entity.do.user_do import SysUser, SysUserRole
from module_admin.entity.vo.user_vo import (
    UserModel, UserPageQueryModel,
    UserRoleModel, UserRoleQueryModel, UserRolePageQueryModel
)
from utils.page_util import PageUtil
from utils.log_util import logger


class UserDao:
    """
    用户管理模块数据操作层
    """

    @classmethod
    async def get_user_by_name(cls, db: AsyncSession, user_name):
        """
        根据用户名获取用户信息
        :param db:
        :param user_name:
        :return:
        """
        user_info = (await db.execute(
            select(SysUser)
            .where(SysUser.status == '0', SysUser.del_flag == '0', SysUser.user_name == user_name)
            .order_by(desc(SysUser.create_time)).distinct()
        )).scalars().first()
        return user_info

    @classmethod
    async def get_user_by_info(cls, db: AsyncSession, user: UserModel):
        """
        根据参数获取用户信息
        :param db:
        :param user:
        :return:
        """
        user_info = (await db.execute(
            select(SysUser)
            .where(SysUser.del_flag == '0',
                   SysUser.user_name == user.user_name if user.user_name else True,
                   SysUser.phonenumber == user.phonenumber if user.phonenumber else True,
                   SysUser.email == user.email if user.email else True,
            ).order_by(desc(SysUser.create_time)).distinct()
        )).scalars().first()
        return user_info

    @classmethod
    async def get_user_by_id(cls, db: AsyncSession, user_id):
        """
        根据用户id获取用户信息
        :param db:
        :param user_id:
        :return:
        """
        user_basic_info = (await db.execute(
            select(SysUser)
            .where(SysUser.status == '0', SysUser.del_flag == '0', SysUser.user_id == user_id)
            .distinct()
        )).scalars().first()

        user_dept_info = (await db.execute(
            select(SysDept)
            .select_from(SysUser)
            .where(SysUser.status == '0', SysUser.del_flag == '0', SysUser.user_id == user_id)
            .join(
                SysDept,
                and_(SysDept.status == '0', SysDept.del_flag == '0', SysDept.dept_id == SysUser.dept_id))
            .distinct()
        )).scalars().first()

        user_role_info = (await db.execute(
            select(SysRole).select_from(SysUser)
            .where(SysUser.status == '0', SysUser.del_flag == '0', SysUser.user_id == user_id)
            .join(SysUserRole, SysUser.user_id == SysUserRole.user_id, isouter=True)
            .join(
                SysRole,
                and_(SysRole.status == '0', SysRole.del_flag == '0', SysUserRole.role_id == SysRole.role_id)
            ).distinct()
        )).scalars().all()

        role_id_list = [item.role_id for item in user_role_info]

        if 1 in role_id_list:
            user_menu_sql = select(SysMenu).where(SysMenu.status == '0').distinct()
        else:
            user_menu_sql = select(SysMenu).select_from(SysUser) \
                .where(SysUser.status == '0', SysUser.del_flag == '0', SysUser.user_id == user_id) \
                .join(SysUserRole, SysUser.user_id == SysUserRole.user_id, isouter=True) \
                .join(SysRole, and_(
                    SysUserRole.role_id == SysRole.role_id, SysRole.status == '0', SysRole.del_flag == '0'
                ), isouter=True,)\
                .join(SysRoleMenu, SysRole.role_id == SysRoleMenu.role_id, isouter=True) \
                .join(SysMenu, and_(SysRoleMenu.menu_id == SysMenu.menu_id, SysMenu.status == '0')) \
                .order_by(SysMenu.order_num).distinct()

        user_menu_info = (await db.execute(user_menu_sql)).scalars().all()

        user_info = dict(
            user_basic_info=user_basic_info,
            user_dept_info=user_dept_info,
            user_role_info=user_role_info,
            user_menu_info=user_menu_info,
        )

        return user_info

    @classmethod
    async def get_user_detail_by_id(cls, db: AsyncSession, user_id):
        """
        根据用户id获取用户详细信息，包含用户状态为禁用
        :param db:
        :param user_id:
        :return:
        """
        query_user_basic_info = (await db.execute(
            select(SysUser).where(SysUser.del_flag == '0', SysUser.user_id == user_id).distinct())
        ).scalars().first()

        query_user_dept_info = (await db.execute(
                    select(SysDept)
                    .select_from(SysUser)
                    .where(SysUser.del_flag == '0', SysUser.user_id == user_id)
                    .join(
                        SysDept,
                        and_(SysUser.dept_id == SysDept.dept_id, SysDept.status == '0', SysDept.del_flag == '0'),
                    )
                    .distinct()
                )
            ).scalars().first()

        query_user_role_info = (await db.execute(
                    select(SysRole)
                    .select_from(SysUser)
                    .where(SysUser.del_flag == '0', SysUser.user_id == user_id)
                    .join(SysUserRole, SysUser.user_id == SysUserRole.user_id, isouter=True)
                    .join(
                        SysRole,
                        and_(SysUserRole.role_id == SysRole.role_id, SysRole.status == '0', SysRole.del_flag == '0'),
                    ).distinct()
                )
            ).scalars().all()

        query_user_menu_info = (await db.execute(
                    select(SysMenu)
                    .select_from(SysUser)
                    .where(SysUser.del_flag == '0', SysUser.user_id == user_id)
                    .join(SysUserRole, SysUser.user_id == SysUserRole.user_id, isouter=True)
                    .join(
                        SysRole,
                        and_(SysUserRole.role_id == SysRole.role_id, SysRole.status == '0', SysRole.del_flag == '0'),
                        isouter=True,
                    )
                    .join(SysRoleMenu, SysRole.role_id == SysRoleMenu.role_id, isouter=True)
                    .join(SysMenu, and_(SysRoleMenu.menu_id == SysMenu.menu_id, SysMenu.status == '0'))
                    .distinct()
                )
            ).scalars().all()

        results = dict(
            user_basic_info=query_user_basic_info,
            user_dept_info=query_user_dept_info,
            user_role_info=query_user_role_info,
            user_menu_info=query_user_menu_info,
        )

        return results

    @classmethod
    async def get_user_list(cls, db: AsyncSession, query_obj: UserPageQueryModel, data_scope_sql, is_page=True):
        """
        根据参数获取用户列表信息
        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        query = select(SysUser, SysDept)\
            .where(SysUser.del_flag == '0', or_(
                SysUser.dept_id == query_obj.dept_id,
                SysDept.dept_id.in_(
                    select(SysDept.dept_id).where(func.find_in_set(query_obj.dept_id, SysDept.ancestors))
                    ),
                ) if query_obj.dept_id else True,
               SysUser.user_id == query_obj.user_id if query_obj.user_id is not None else True,
               SysUser.user_name.like(f'%{query_obj.user_name}%') if query_obj.user_name else True,
               SysUser.nick_name.like(f'%{query_obj.nick_name}%') if query_obj.nick_name else True,
               SysUser.email.like(f'%{query_obj.email}%') if query_obj.email else True,
               SysUser.phonenumber.like(f'%{query_obj.phonenumber}%') if query_obj.phonenumber else True,
               SysUser.status == query_obj.status if query_obj.status else True,
               SysUser.sex == query_obj.sex if query_obj.sex else True,
               SysUser.create_time.between(
                   datetime.combine(datetime.strptime(query_obj.begin_time, '%Y-%m-%d'), time(00, 00, 00)),
                   datetime.combine(datetime.strptime(query_obj.end_time, '%Y-%m-%d'), time(23, 59, 59)),
               ) if query_obj.begin_time and query_obj.end_time else True,
               eval(data_scope_sql),
            ).join(
                SysDept, and_(SysUser.dept_id == SysDept.dept_id, SysDept.status == '0', SysDept.del_flag == '0'),
                isouter=True,)\
            .join(
                SysDept, and_(SysUser.dept_id == SysDept.dept_id, SysDept.status == '0', SysDept.del_flag == '0'),
                isouter=True,)\
            .order_by(SysUser.user_name).distinct()

        user_list = await PageUtil.paginate(db, query, query_obj.page_num, query_obj.page_size, is_page)
        return user_list

    @classmethod
    async def add_user_dao(cls, db: AsyncSession, user: UserModel):
        """
        新增用户
        :param db:
        :param user:
        :return:
        """
        db_user = SysUser(**user.model_dump(exclude={'adminn'}))
        db.add(db_user)
        await db.flush()
        return db_user

    @classmethod
    async def edit_user_dao(cls, db: AsyncSession, user: dict):
        """
        修改用户
        :param db:
        :param user:
        :return:
        """
        await db.execute(update(SysUser), [user])

    @classmethod
    async def delete_user_dao(cls, db: AsyncSession, user: UserModel):
        """
        删除用户
        :param db:
        :param user:
        :return:
        """
        await db.execute(
            update(SysUser).where(SysUser.user_id == user.user_id)
            .values(del_flag='2', update_by=user.update_by, update_time=datetime.now())
        )

    @classmethod
    async def get_user_role_allocated_list_by_user_id(cls, db: AsyncSession, query_obj: UserRoleQueryModel):
        """
        根据用户id获取已分配的角色列表信息
        :param db:
        :param query_obj:
        :return:
        """
        allocated_role_sql = select(SysRole)\
            .where(
                SysRole.del_flag == '0', SysRole.role_id != 1,
                SysRole.role_name == query_obj.role_name if query_obj.role_name else True,
                SysRole.role_key == query_obj.role_key if query_obj.role_key else True,
                SysRole.role_id.in_(
                    select(SysUserRole.role_id).where(SysUserRole.user_id == query_obj.user_id)
                ),
            ).distinct()

        allocated_role_result = (await db.execute(allocated_role_sql)).scalars().all()
        return allocated_role_result

    @classmethod
    async def get_user_role_allocated_list_by_role_id(
            cls, db: AsyncSession, query_obj: UserRolePageQueryModel, data_scope_sql, is_page=False,
    ):
        """
        通过角色id获取已分配的用户列表信息
        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        allocated_user_sql = select(SysUser)\
            .join(SysDept, SysDept.dept_id == SysUser.dept_id, isouter=True)\
            .join(SysUserRole, SysUserRole.user_id == SysUser.user_id, isouter=True)\
            .join(SysRole, SysRole.role_id == SysUserRole.role_id, isouter=True)\
            .where(
                SysUser.del_flag == '0',
                SysUser.user_name == query_obj.user_name if query_obj.user_name else True,
                SysUser.phonenumber == query_obj.phonenumber if query_obj.phonenumber else True,
                SysRole.role_id == query_obj.role_id,
                eval(data_scope_sql),
            ).distinct()

        allocated_user_result = (await PageUtil.paginate(
            db, allocated_user_sql, query_obj.page_num, query_obj.page_size, is_page)
        )
        return allocated_user_result

    @classmethod
    async def get_user_role_unallocated_list_by_role_id(
            cls, db: AsyncSession, query_obj: UserRolePageQueryModel, data_scope_sql, is_page=False,
    ):
        """

        :param db:
        :param query_obj:
        :param data_scope_sql:
        :param is_page:
        :return:
        """
        unallocated_user_sql = select(SysUser) \
            .join(SysDept, SysDept.dept_id == SysUser.dept_id, isouter=True) \
            .join(SysUserRole, SysUserRole.user_id == SysUser.user_id, isouter=True) \
            .join(SysRole, SysRole.role_id == SysUserRole.role_id, isouter=True) \
            .where(
                SysUser.del_flag == '0',
                SysUser.user_name == query_obj.user_name if query_obj.user_name else True,
                SysUser.phonenumber == query_obj.phonenumber if query_obj.phonenumber else True,
                or_(SysRole.role_id != query_obj.role_id, SysRole.role_id.is_(None)),
                ~SysUser.user_id.in_(
                    select(SysUser.user_id).select_from(SysUser)
                    .join(SysUserRole,
                          and_(SysUserRole.user_id == SysUser.user_id, SysUserRole.role_id == query_obj.role_id))
                ),
                eval(data_scope_sql),
            ).distinct()

        unallocated_user_result = (await PageUtil.paginate(
            db, unallocated_user_sql, query_obj.page_num, query_obj.page_size, is_page)
        )
        return unallocated_user_result

    @classmethod
    async def add_user_role_dao(cls, db: AsyncSession, user_role: UserRoleModel):
        """
        添加用户和角色关联信息
        :param db:
        :param user_role:
        :return:
        """
        db_user_role = SysUserRole(**user_role.model_dump())
        db.add(db_user_role)
        await db.flush()

    @classmethod
    async def delete_user_role_dao(cls, db: AsyncSession, user_role: UserRoleModel):
        """
        删除用户和角色关联信息
        :param db:
        :param user_role:
        :return:
        """
        await db.execute(delete(SysUserRole).where(SysUserRole.user_id.in_([user_role.user_id])))

    @classmethod
    async def delete_user_role_by_user_and_role_dao(cls, db: AsyncSession, user_role: UserRoleModel):
        """
        根据用户id和角色id删除用户和角色关联信息
        :param db:
        :param user_role:
        :return:
        """
        await db.execute(delete(SysUserRole).where(
            SysUserRole.user_id == user_role.user_id if user_role.user_id else True,
            SysUserRole.role_id == user_role.role_id if user_role.role_id else True,
        ))

    @classmethod
    async def get_user_role_detail(cls, db: AsyncSession, user_role: UserRoleModel):
        """
        根据用户角色关联获取用户角色关联信息
        :param db:
        :param user_role:
        :return:
        """
        user_role_info = (await db.execute(
            select(SysUserRole)
            .where(
                SysUserRole.user_id == user_role.user_id, SysUserRole.role_id == user_role.role_id
            ).distinct()
        )).scalars().first()
        return user_role_info

    @classmethod
    async def get_user_dept_info(cls, db: AsyncSession, dept_id):
        """
        获取部门id获取部门信息
        :param db:
        :param dept_id:
        :return:
        """
        dept_basic_info = (await db.execute(
            select(SysDept).where(SysDept.dept_id == dept_id, SysDept.status == '0', SysDept.del_flag == '0')
        ))
        return dept_basic_info