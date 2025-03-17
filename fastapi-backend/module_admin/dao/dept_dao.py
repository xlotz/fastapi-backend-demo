from sqlalchemy import bindparam, func, or_, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.util import immutabledict
from typing import List
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.do.role_do import SysRoleDept
from module_admin.entity.do.user_do import SysUser
from module_admin.entity.vo.dept_vo import DeptModel


class DeptDao:
    """
    部门管理模块数据库操作层
    """

    @classmethod
    async def get_dept_by_id(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id获取部门信息
        :param db:
        :param dept_id:
        :return:
        """
        dept_info = (await db.execute(
            select(SysDept).where(
                SysDept.dept_id == dept_id
            )
        )).scalars().first()
        return dept_info

    @classmethod
    async def get_dept_detail_by_id(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id获取部门详情信息
        :param db:
        :param dept_id:
        :return:
        """
        dept_info = (await db.execute(
            select(SysDept).where(SysDept.dept_id == dept_id, SysDept.del_flag == '0')
        )).scalars().first()
        return dept_info

    @classmethod
    async def get_dept_detail_by_info(cls, db: AsyncSession, dept: DeptModel):
        """
        根据参数获取部门详情信息
        :param db:
        :param dept:
        :return:
        """
        dept_info = (await db.execute(
            select(SysDept).where(
                SysDept.parent_id == dept.parent_id if dept.parent_id else True,
                SysDept.dept_name == dept.dept_name if dept.dept_name else True,
            )
        )).scalars().first()
        return dept_info

    @classmethod
    async def get_dept_info_for_edit_option(cls, db: AsyncSession, dept_info: DeptModel, data_scope_sql: str):
        """
        获取编辑对应的再用部门列表信息
        :param db:
        :param dept_info:
        :param data_scope_sql:
        :return:
        """

        """
        eval(data_scope_sql) // 动态sql, 将字符串解析为python表达式并执行。
        建议使用 data_scope_condition=text(data_scope_sql)
        """

        dept_result = (await db.execute(
            select(SysDept).where(
                SysDept.dept_id != dept_info.dept_id,
                ~SysDept.dept_id.in_(
                    select(SysDept.dept_id).where(func.find_in_set(dept_info.dept_id, SysDept.ancestors))
                ),
                SysDept.del_flag == '0',
                SysDept.status == '0',
                eval(data_scope_sql),
            ).order_by(SysDept.order_num).distinct()
        )).scalars().all()
        return dept_result

    @classmethod
    async def get_children_dept_dao(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id获取当前部门的子部门信息
        :param db:
        :param dept_id:
        :return:
        """
        dept_result = (await db.execute(
            select(SysDept).where(
                func.find_in_set(dept_id, SysDept.ancestors)
            )
        )).scalars().all()
        return dept_result

    @classmethod
    async def get_dept_list_for_tree(cls, db: AsyncSession, dept_info: DeptModel, data_scope_sql: str):
        """
        获取所有再用部门列表信息
        :param db:
        :param dept_info:
        :param data_scope_sql:
        :return:
        """

        """
        
        eval(data_scope_sql) // 动态sql, 将字符串解析为python表达式并执行。
        建议使用 data_scope_condition=text(data_scope_sql)
        """

        dept_result = (await db.execute(
            select(SysDept).where(
                SysDept.status == '0', SysDept.del_flag == '0',
                SysDept.dept_name.like(f'%{dept_info.dept_name}%') if dept_info.dept_name else True,
                eval(data_scope_sql),
            ).order_by(SysDept.order_num).distinct()
        )).scalars().all()
        return dept_result

    @classmethod
    async def get_dept_list(cls, db: AsyncSession, page_obj: DeptModel, data_scope_sql: str):
        """
        根据查询参数获取部门列表信息
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :return:
        """
        """
        eval(data_scope_sql) // 动态sql, 将字符串解析为python表达式并执行。
        建议使用 data_scope_condition=text(data_scope_sql)
        """

        dept_result = (await db.execute(
            select(SysDept).where(
                SysDept.del_flag == '0',
                SysDept.dept_id == page_obj.dept_id if page_obj.dept_id else True,
                SysDept.status == page_obj.status if page_obj.status else True,
                SysDept.dept_name.like(f'%{page_obj.dept_name}%') if page_obj.dept_name else True,
                eval(data_scope_sql),
            ).order_by(SysDept.dept_name).distinct()
        )).scalars().all()
        return dept_result

    @classmethod
    async def add_dept_dao(cls, db: AsyncSession, dept: DeptModel):
        """
        添加部门数据库操作
        :param db:
        :param dept:
        :return:
        """
        dept_info = SysDept(**dept.model_dump())
        db.add(dept_info)
        await db.flush()
        return dept_info

    @classmethod
    async def edit_dept_dao(cls, db: AsyncSession, dept: dict):
        """
        修改部门数据库操作
        :param db:
        :param dept:
        :return:
        """
        await db.execute(update(SysDept), [dept])

    @classmethod
    async def update_dept_children_dao(cls, db: AsyncSession, update_dept: List):
        """
        更新子部门信息
        :param db:
        :param update_dept:
        :return:
        """

        """
        bindparam('dept_id') 是 SQLAlchemy 的绑定参数语法，表示在执行时会动态传入一个名为 'dept_id' 的参数值。
        execution_options ，用于指定执行 SQL 时的一些行为。
        immutabledict({'synchronize_session': None}) 是一个不可变字典。
        synchronize_session 的作用是控制 SQLAlchemy 如何同步会话中的对象状态：
        None：表示不进行会话同步，即更新操作不会自动更新会话中的对象状态。这在某些场景下可以提高性能，但需要手动处理会话中的对象状态。
        其他值（如 'fetch' 或 'evaluate'）会自动同步会话中的对象状态。
        """
        await db.execute(
            update(SysDept).where(
                SysDept.dept_id == bindparam('dept_id')
            ).values(
                {
                    'dept_id': bindparam('dept_id'),
                    'ancestors': bindparam('ancestors'),
                }
            ), update_dept,
            execution_options=immutabledict({'synchronize_session': None})
        )

    @classmethod
    async def update_dept_status_normal_dao(cls, db: AsyncSession, dept_id_list: List):
        """
        批量更新部门状态为正常
        :param db:
        :param dept_id_list:
        :return:
        """
        await db.execute(
            update(SysDept).where(
                SysDept.dept_id.in_(dept_id_list)
            ).values(status='0')
        )

    @classmethod
    async def delete_dept_dao(cls, db: AsyncSession, dept: DeptModel):
        """
        删除部门数据库操作
        :param db:
        :param dept:
        :return:
        """
        await db.execute(
            update(SysDept)
            .where(
                SysDept.dept_id == dept.dept_id)
            .values(del_flag='2', update_by=dept.update_by, update_time=dept.update_time)
        )

    @classmethod
    async def count_normal_children_dept_dao(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id统计所有正常状态的子部门数量
        :param db:
        :param dept_id:
        :return:
        """
        normal_children_dept_count = (await db.execute(
            select(func.count('*')).select_from(SysDept).where(
                SysDept.status == '0', SysDept.del_flag == '0', func.find_in_set(dept_id, SysDept.ancestors)
            )
        )).scalar()
        return normal_children_dept_count


    @classmethod
    async def count_children_dept_dao(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id统计所有子部门数量
        :param db:
        :param dept_id:
        :return:
        """
        children_dept_count = (await db.execute(
            select(func.count('*')).select_from(SysDept).where(
                SysDept.del_flag == '0', SysDept.parent_id == dept_id
            ).limit(1)
        )).scalar()
        return children_dept_count

    @classmethod
    async def count_dept_user_dao(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id查询部门下的用户数量
        :param db:
        :param dept_id:
        :return:
        """
        dept_user_count = (await db.execute(
            select(func.count('*')).select_from(SysUser).where(
                SysUser.dept_id == dept_id, SysUser.del_flag == '0'
            )
        )).scalar()
        return dept_user_count
