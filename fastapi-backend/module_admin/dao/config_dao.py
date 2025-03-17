from datetime import datetime, time
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.config_do import SysConfig
from module_admin.entity.vo.config_vo import ConfigModel, ConfigPageQueryModel
from utils.page_util import PageUtil


class ConfigDao:
    """
    参数配置管理模块数据库操作层
    """

    @classmethod
    async def get_config_detail_by_id(cls, db: AsyncSession, config_id: int):
        """
        根据配置id获取配置详情
        :param db:
        :param config_id:
        :return:
        """
        config_info = (await db.execute(
            select(SysConfig).where(SysConfig.config_id == config_id)
        )).scalars().first()
        return config_info

    @classmethod
    async def get_config_detail_by_info(cls, db: AsyncSession, config: ConfigModel):
        """
        根据查询参数获取参数配置详情
        :param db:
        :param config:
        :return:
        """
        config_info = (await db.execute(
            select(SysConfig).where(
                SysConfig.config_key == config.config_key if config.config_key else True,
                SysConfig.config_value == config.config_value if config.config_value else True,
            )
        )).scalars().first()

        return config_info

    @classmethod
    async def get_config_list(cls, db: AsyncSession, query_obj: ConfigPageQueryModel, is_page: bool = True):
        """
        根据查询参数获取配置列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        start_time = datetime.combine(datetime.strptime(query_obj.begin_time, '%Y-%m-%d'), time(00, 00, 00))
        end_time = datetime.combine(datetime.strptime(query_obj.end_time, '%Y-%m-%d'), time(23, 59, 59))
        query = (
            select(SysConfig).where(
                SysConfig.config_name.like(f'%{query_obj.config_name}%') if query_obj.config_name else True,
                SysConfig.config_key.like(f'%{query_obj.config_key}%') if query_obj.config_key else True,
                SysConfig.config_type == query_obj.config_type if query_obj.config_type else True,
                SysConfig.create_time.between(start_time, end_time) if query_obj.begin_time and query_obj.end_time else True,
            ).order_by(SysConfig.config_id).distinct()
        )
        config_list = await PageUtil.paginate(db, query, query_obj.page_num, query_obj.page_size, is_page)
        return config_list

    @classmethod
    async def add_config_dao(cls, db: AsyncSession, config: ConfigModel):
        """
        添加参数配置数据库操作
        :param db:
        :param config:
        :return:
        """
        db_config = SysConfig(**config.model_dump())
        db.add(db_config)
        await db.flush()
        return db_config

    @classmethod
    async def edit_config_dao(cls, db: AsyncSession, config: dict):
        """
        修改参数配置数据库操作
        :param db:
        :param config:
        :return:
        """
        await db.execute(update(SysConfig), [config])

    @classmethod
    async def delete_config_dao(cls, db: AsyncSession, config: ConfigModel):
        """
        删除参数配置数据库操作
        :param db:
        :param config:
        :return:
        """
        await db.execute(delete(SysConfig).where(SysConfig.config_id.in_([config.config_id])))