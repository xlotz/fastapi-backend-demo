from sqlalchemy import bindparam, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.util import immutabledict
from typing import List
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.do.role_do import SysRoleDept
from module_admin.entity.do.user_do import SysUser
from module_admin.entity.vo.dept_vo import DeptModel


class DeptDao:
    """
    部门管理模块数据层操作
    """

    @classmethod
    async def get_dept_by_id(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id获取在用部门信息
        :param db:
        :param dept_id:
        :return:
        """

        dept_info = (await db.execute(select(SysDept).where(SysDept.dept_id == dept_id))).scalars().first()

        return dept_info

    @classmethod
    async def get_dept_detail_by_id(cls, db: AsyncSession, dept_id: int):
        """
        根据部门id 获取部门详情
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
        根据参数获取部门信息
        :param db:
        :param dept:
        :return:
        """
        dept_info = (await db.execute(
            select(SysDept).where(
                SysDept.parent_id == dept.parent_id if dept.parent_id else True,
                SysDept.dept_name == dept.dept_name if dept.dept_name else True,
            )
        )
        ).scalars().first()
        return dept_info

    @classmethod
    async def get_dept_info_for_edit_option(cls, db: AsyncSession, dept: DeptModel, data_scope_sql: str):
        """
        获取部门 编辑对应的再用部门列表信息
        :param db:
        :param dept:
        :param data_scope_sql:
        :return:
        """
        dept_query = select(SysDept).where(
            SysDept.dept_id != dept.dept_id,
            ~SysDept.dept_id.in_(
                select(SysDept.dept_id).where(func.find_in_set(dept.dept_id, SysDept.ancestors))
            ),
            SysDept.del_flag == '0', SysDept.status == '0', eval(data_scope_sql),
        ).order_by(SysDept.order_num).distinct()

        dept_result = (await db.execute(dept_query)).scalars().first()

        return dept_result

    @classmethod
    async def get_children_dept_list_dao(cls, db: AsyncSession, dept_id):
        """
        获取子部门
        :param db:
        :param dept_id:
        :return:
        """
        dept_result = (await db.execute(
            select(SysDept).where(func.find_in_set(dept_id, SysDept.ancestors))
        )).scalars().all()
        return dept_result

    @classmethod
    async def get_dept_list_for_tree(cls, db: AsyncSession, dept: DeptModel, data_scope_sql):
        """
        获取所有再用部门信息
        :param db:
        :param dept:
        :param data_scope_sql:
        :return:
        """
        dept_result = (await db.execute(
            select(SysDept).where(
                SysDept.status == '0', SysDept.del_flag == '0',
                SysDept.dept_name.like(f'%{dept.dept_name}%') if dept.dept_name else True,
                eval(data_scope_sql),
            ).order_by(SysDept.order_num).distinct()
        )).scalars().all()

        return dept_result

    @classmethod
    async def get_dept_list_by_info(cls, db: AsyncSession, page_obj: DeptModel, data_scope_sql):
        """
        根据参数获取部门列表信息
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :return:
        """
        dept_query = select(SysDept).where(
            SysDept.del_flag == '0',
            SysDept.dept_id == page_obj.dept_id if page_obj.dept_id is not None else True,
            SysDept.status == page_obj.status if page_obj.status else True,
            SysDept.dept_name.like(f'%{page_obj.dept_name}%') if page_obj.dept_name else True,
            eval(data_scope_sql),
        ).order_by(SysDept.order_num).discinct()

        dept_result = (await db.execute(dept_query)).scalars().all()
        return dept_result

    @classmethod
    async def add_dept_dao(cls, db: AsyncSession, dept: DeptModel):
        """
        添加菜单
        :param db:
        :param dept:
        :return:
        """
        db_dept = SysDept(**dept.model_dump())
        db.add(db_dept)
        await db.flush()
        return db_dept

    @classmethod
    async def edit_dept_dao(cls, db: AsyncSession, dept: dict):
        """
        编辑部门
        :param db:
        :param dept:
        :return:
        """

        await db.execute(update(SysDept), [dept])

    @classmethod
    async def edit_dept_children_dao(cls, db: AsyncSession, update_dept: List):
        """
        编辑子部门
        :param db:
        :param update_dept:
        :return:
        """
        dept_query = update(SysDept).where(
            SysDept.dept_id == bindparam('dept_id')
        ).values({
            'dept_id': bindparam('dept_id'),
            'ancestors': bindparam('ancestors'),
        })

        await db.execute(dept_query, update_dept, execution_options=({'synchronize_session': None}))

    @classmethod
    async def update_dept_status_normal_dao(cls, db: AsyncSession, dept_id_list: List):
        """
        批量更新状态为正常
        :param db:
        :param dept_id_list:
        :return:
        """
        await db.execute(update(SysDept).where(SysDept.dept_id.in_(dept_id_list)).values(status='0'))

    @classmethod
    async def delete_dept_dao(cls, db: AsyncSession, dept: DeptModel):
        """
        删除部门
        :param db:
        :param dept:
        :return:
        """

        await db.execute(
            update(SysDept).where(SysDept.dept_id == dept.dept_id)
            .values(del_flag='2', update_by=dept.update_by, update_time=dept.update_time)
        )

    @classmethod
    async def count_normal_children_dept_dao(cls, db: AsyncSession, dept_id):
        """
        根据id统计所有正常状态的子部门数量
        :param db:
        :param dept_id:
        :return:
        """
        normal_dept_children_dept_count = select(func.count('*'))\
            .select_from(SysDept).where(
            SysDept.status == '0', SysDept.del_flag == '0', func.find_in_set(dept_id, SysDept.ancestors)
        )
        dept_count = (await db.execute(normal_dept_children_dept_count)).scalar()
        return dept_count

    @classmethod
    async def count_children_dept_dao(cls, db: AsyncSession, dept_id):
        """
        根据id 统计所有状态的子部门数量
        :param db:
        :param dept_id:
        :return:
        """
        dept_children_dept_count = select(func.count('*')) \
            .select_from(SysDept).where(
            SysDept.del_flag == '0', func.find_in_set(dept_id, SysDept.ancestors)
        )
        dept_count = (await db.execute(dept_children_dept_count)).scalar()
        return dept_count

    @classmethod
    async def count_dept_user_dao(cls, db: AsyncSession, dept_id):
        """
        根据ID统计部门下所有的用户
        :param db:
        :param dept_id:
        :return:
        """
        dept_user_query = select(func.count('*')).select_from(SysUser).where(
            SysUser.dept_id == dept_id, SysUser.del_flag == '0'
        )
        user_count = (await db.execute(dept_user_query)).scalar()
        return user_count