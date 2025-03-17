from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.do.user_do import SysUser


async def login_by_account(db: AsyncSession, user_name: str):
    """
    根据用户名查询用户信息
    :param db:
    :param user_name:
    :return:
    """

    """
    等价SQL:
    SELECT DISTINCT sys_user.*, sys_dept.*
    FROM sys_user
    LEFT JOIN sys_dept
        ON sys_user.dept_id = sys_dept.dept_id
        AND sys_dept.status = '0'
        AND sys_dept.del_flag = '0'
    WHERE sys_user.user_name = 'example_user'
      AND sys_user.del_flag = '0';
    """
    user_info = (await db.execute(
        select(SysUser, SysDept).where(
            SysUser.user_name == user_name, SysUser.del_flag == '0'
        ).join(
            SysDept,
            and_(SysUser.dept_id == SysDept.dept_id, SysDept.status == '0', SysDept.del_flag == '0'),
            isouter=True,
        ).distinct()
    )).first()
    return user_info