from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.constant import CommonConstant
from config.enums import RedisInitKeyConfig
from sub_applications.exceptions.exception import ServiceException
from module_admin.dao.config_dao import ConfigDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.config_vo import ConfigModel, ConfigPageQueryModel, DeleteConfigModel
from utils.common_util import export_list2excel, SqlalchemyUtil


class ConfigService:
    """
    参数配置管理模块服务层
    """

    @classmethod
    async def get_config_list_services(cls, db: AsyncSession, query_obj: ConfigPageQueryModel, is_page: bool = False):
        """
        获取参数配置列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        config_list_info = await ConfigDao.get_config_list(db, query_obj, is_page)
        return config_list_info

    @classmethod
    async def init_cache_sys_config_services(cls, db: AsyncSession, redis):
        """
        应用初始化时，获取所有参数配置对应的信息并缓存到redis
        :param db:
        :param redis:
        :return:
        """
        # 获取sys_config开头的key列表
        keys = await redis.keys(f'{RedisInitKeyConfig.SYS_CONFIG.key}:*')
        # 如果当前已存在则删除匹配的键
        if keys:
            await redis.delete(**keys)

        config_all = await ConfigDao.get_config_list(db, ConfigPageQueryModel(**dict()), is_page=True)
        for obj in config_all:
            await redis.set(
                f"{RedisInitKeyConfig.SYS_CONFIG.key}:{obj.get('config_key')}",
                obj.get('config_value'),
            )

    @classmethod
    async def query_config_list_from_cache_services(cls, redis, config_key: str):
        """
        从缓存中获取参数key对应的value
        :param redis:
        :param config_key:
        :return:
        """
        result = await redis.get(f'{RedisInitKeyConfig.SYS_CONFIG.key}:{config_key}')
        return result

    @classmethod
    async def check_config_key_unique_services(cls, db: AsyncSession, page_obj: ConfigModel):
        """
        检查参数配置key是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        config_id = -1 if page_obj.config_key is None else page_obj.config_id
        config = await ConfigDao.get_config_detail_by_info(db, ConfigModel(config_key=page_obj.config_key))
        if config and config.config_id != config_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_config_services(cls, request: Request, db: AsyncSession, page_obj: ConfigModel):
        """
        添加参数配置
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        is_unique = await cls.check_config_key_unique_services(db, page_obj)
        if not is_unique:
            raise ServiceException(message=f'新增参数{page_obj.config_name}失败, key以存在')
        else:
            try:
                await ConfigDao.add_config_dao(db, page_obj)
                await db.commit()
                await request.app.state.redis.set(
                    f'{RedisInitKeyConfig.SYS_CONFIG.key}:{page_obj.config_key}', page_obj.config_value
                )
                return CrudResponseModel(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e

    @classmethod
    async def edit_config_services(cls, request: Request, db: AsyncSession, page_obj: ConfigModel):
        """
        修改参数配置
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        edit_config = page_obj.model_config(exclude_unset=True)
        config_info = await cls.config_detail_services(db, page_obj.config_id)

        if config_info.config_id:
            is_unique = await cls.check_config_key_unique_services(db, page_obj)
            if not is_unique:
                raise ServiceException(message=f'修改参数{page_obj.config_name}失败，key已存在')
            else:
                try:
                    await ConfigDao.edit_config_dao(db, edit_config)
                    await db.commit()
                    if config_info.config_key != page_obj.config_key:
                        await request.app.state.redis.delete(
                            f'{RedisInitKeyConfig.SYS_CONFIG.key}:{config_info.config_key}'
                        )
                    await request.app.state.redis.set(
                        f'{RedisInitKeyConfig.SYS_CONFIG.key}:{page_obj.config_key}', page_obj.config_value
                    )
                    return CrudResponseModel(is_success=True, message='更新成功')
                except Exception as e:
                    await db.rollback()
                    raise e
        else:
            raise ServiceException(message='参数配置不存在')

    @classmethod
    async def delete_config_services(cls, request: Request, db: AsyncSession, page_obj: DeleteConfigModel):
        """
        删除参数配置
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.config_ids:
            config_id_list = page_obj.config_ids.split(',')
            try:
                delete_config_key_list = []
                for config_id in config_id_list:
                    config_info = await cls.config_detail_services(db, int(config_id))

                    if config_info.config_type == CommonConstant.YES:
                        raise ServiceException(message=f'内置参数{config_info.config_key}不能删除')
                    else:
                        await ConfigDao.delete_config_dao(db, ConfigModel(config_id=int(config_id)))
                        delete_config_key_list.append(f'{RedisInitKeyConfig.SYS_CONFIG.key}:{config_info.config_key}')
                await db.commit()
                if delete_config_key_list:
                    await request.app.state.redis.delete(*delete_config_key_list)
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入参数配置id为空')

    @classmethod
    async def config_detail_services(cls, db: AsyncSession, config_id: int):
        """
        通过id获取参数详细配置
        :param db:
        :param config_id:
        :return:
        """
        config = await ConfigDao.get_config_detail_by_id(db, config_id=config_id)
        if config:
            result = ConfigModel(**SqlalchemyUtil.serialize_result(config))
        else:
            result = ConfigModel(**dict())
        return result

    @staticmethod
    async def export_config_list_services(config_list: List):
        """
        导出参数配置列表
        :param config_list:
        :return:
        """
        # 创建映射字典，将英文改为中文
        mapping_dict = {
            'config_id': '参数主键',
            'config_name': '参数名称',
            'config_key': '参数键名',
            'config_value': '参数键值',
            'config_type': '系统内置',
            'create_by': '创建者',
            'create_time': '创建时间',
            'update_by': '更新者',
            'update_time': '更新时间',
            'remark': '备注',
        }

        for item in config_list:
            if item.get('config_type') == 'Y':
                item['config_type'] = '是'
            else:
                item['config_type'] = '否'

        new_data = [
            {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)} for item in config_list
        ]
        binary_data = export_list2excel(new_data)
        return binary_data

    @classmethod
    async def refresh_sys_config_services(cls, request: Request, db: AsyncSession):
        """
        刷新字典缓存信息
        :param request:
        :param db:
        :return:
        """
        await cls.init_cache_sys_config_services(db, request.app.state.redis)
        return CrudResponseModel(is_success=True, message='刷新成功')

