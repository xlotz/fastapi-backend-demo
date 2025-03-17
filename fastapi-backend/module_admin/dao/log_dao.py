from datetime import datetime, time
from sqlalchemy import asc, delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.log_do import SysLogininfor, SysOperLog
from module_admin.entity.vo.log_vo import LogininforModel, LoginLogPageQueryModel, OperLogModel, OperLogPageQueryModel
from utils.common_util import SnakeCaseUtil
from utils.page_util import PageUtil


class OperationLogDao:
    """
    操作日志管理模块数据库操作层
    """

    @classmethod
    async def get_operation_log_list(cls, db: AsyncSession, query_obj: OperLogPageQueryModel, is_page: bool = False):
        """
        根据查询参数获取操作日志列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        if query_obj.is_asc == 'ascending':
            order_by_column = asc(getattr(SysOperLog, SnakeCaseUtil.camel_to_snake(query_obj.order_by_column), None))
        elif query_obj.is_asc == 'descending':
            order_by_column = desc(getattr(SysOperLog, SnakeCaseUtil.camel_to_snake(query_obj.order_by_column), None))
        else:
            order_by_column = desc(SysOperLog.oper_time)

        start_time = datetime.combine(datetime.strptime(query_obj.begin_time, '%Y-%m-%d'), time(00, 00, 00))
        end_time = datetime.combine(datetime.strptime(query_obj.end_time, '%Y-%m-%d'), time(23, 59, 59))

        query = (
            select(SysOperLog).where(
                SysOperLog.title.like(f'%{query_obj.title}%') if query_obj.title else True,
                SysOperLog.oper_name.like(f'%{query_obj.oper_name}%') if query_obj.oper_name else True,
                SysOperLog.business_type == query_obj.business_type if query_obj.business_type else True,
                SysOperLog.status == query_obj.status if query_obj.status else True,
                SysOperLog.oper_time.between(start_time, end_time)
                if query_obj.begin_time and query_obj.end_time else True,
            ).order_by(order_by_column).distinct()
        )
        oper_log_list = await PageUtil.paginate(db, query, query_obj.page_num, query_obj.page_size, is_page)
        return oper_log_list

    @classmethod
    async def add_operation_log_dao(cls, db: AsyncSession, oper_log: OperLogModel):
        """
        添加操作日志
        :param db:
        :param oper_log:
        :return:
        """
        db_oper_log = SysOperLog(**oper_log.model_dump())
        db.add(db_oper_log)
        await db.flush()
        return db_oper_log

    @classmethod
    async def delete_operation_log_dao(cls, db: AsyncSession, oper_log: OperLogModel):
        """
        删除操作日志
        :param db:
        :param oper_log:
        :return:
        """
        await db.execute(delete(SysOperLog).where(SysOperLog.oper_id.in_([oper_log.oper_id])))

    @classmethod
    async def clear_operation_log_dao(cls, db: AsyncSession):
        """
        清空操作日志
        :param db:
        :return:
        """
        await db.execute(delete(SysOperLog))


class LoginLogDao:
    """
    登录日志管理模块数据库操作层
    """
    @classmethod
    async def get_login_log_list(cls, db: AsyncSession, query_obj: LoginLogPageQueryModel, is_page: bool = False):
        """
        根据查询参数获取登录日志列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """

        if query_obj.is_asc == 'ascending':
            order_by_column = asc(
                getattr(SysLogininfor, SnakeCaseUtil.camel_to_snake(query_obj.order_by_column), None)
            )
        elif query_obj.is_asc == 'descending':
            order_by_column = desc(
                getattr(SysLogininfor, SnakeCaseUtil.camel_to_snake(query_obj.order_by_column), None)
            )
        else:
            order_by_column = desc(SysLogininfor.login_time)

        start_time = datetime.combine(datetime.strptime(query_obj.begin_time, '%Y-%m-%d'), time(00, 00, 00))
        end_time = datetime.combine(datetime.strptime(query_obj.begin_time, '%Y-%m-%d'), time(23, 59, 59))

        query = (
            select(SysLogininfor).where(
                SysLogininfor.ipaddr.like(f'%{query_obj.ipaddr}%') if query_obj.ipaddr else True,
                SysLogininfor.user_name.like(f'%{query_obj.user_name}%') if query_obj.user_name else True,
                SysLogininfor.status == query_obj.status if query_obj.status else True,
                SysLogininfor.login_time.between(start_time, end_time)
                if query_obj.begin_time and query_obj.end_time else True,
            ).order_by(order_by_column).distinct()
        )
        login_log_list = await PageUtil.paginate(db, query, query_obj.page_num, query_obj.page_size, is_page)
        return login_log_list

    @classmethod
    async def add_login_log_dao(cls, db: AsyncSession, login_log: LogininforModel):
        """
        添加登录日志
        :param db:
        :param login_log:
        :return:
        """
        db_login_log = SysLogininfor(**login_log.model_dump())
        db.add(db_login_log)
        await db.flush()
        return db_login_log

    @classmethod
    async def delete_login_log_dao(cls, db: AsyncSession, login_log: LogininforModel):
        """
        删除登录日志
        :param db:
        :param login_log:
        :return:
        """
        await db.execute(delete(SysLogininfor).where(SysLogininfor.info_id.in_([login_log.info_id])))

    @classmethod
    async def clear_login_log_dao(cls, db: AsyncSession):
        """
        清空登录日志
        :param db:
        :return:
        """
        await db.execute(delete(SysLogininfor))
