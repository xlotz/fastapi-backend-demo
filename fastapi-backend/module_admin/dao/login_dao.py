from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.do.user_do import SysUser


async def login_by_account(db: AsyncSession, user_name):
    """
    根据用户名获取用户信息
    :param db:
    :param user_name:
    :return:
    """
    user_query = select(SysUser, SysDept).where(
        SysUser.user_name == user_name, SysDept.del_flag == '0'
    ).join(
        SysDept, and_(SysUser.dept_id == SysDept.dept_id, SysDept.status == '0', SysDept.del_flag == '0'),
        isouter=True
    ).distinct()
    user_info = (await db.execute(user_query)).first()

    return user_info