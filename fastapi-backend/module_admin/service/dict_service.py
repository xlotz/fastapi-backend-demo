import json
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.constant import CommonConstant
from config.enums import RedisInitKeyConfig
from sub_applications.exceptions.exception import ServiceException
from module_admin.dao.dict_dao import DictDataDao, DictTypeDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.dict_vo import (
    DeleteDictDataModel,
    DeleteDictTypeModel,
    DictDataModel,
    DictDataPageQueryModel,
    DictTypeModel,
    DictTypePageQueryModel,
)
from utils.common_util import export_list2excel, SqlalchemyUtil


class DictTypeService:
    """
    字典类型管理模块service层
    """

    @classmethod
    async def get_dict_type_list_services(cls, db: AsyncSession, query_obj: DictTypePageQueryModel, is_page: bool = False):
        """
        获取字典类型列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        dict_type_list = await DictTypeDao.get_dict_type_list(db, query_obj, is_page)
        return dict_type_list

    @classmethod
    async def check_dict_type_unique_services(cls, db: AsyncSession, page_obj: DictTypeModel):
        """
        校验字典类型名称是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        dict_id = -1 if page_obj.dict_id is None else page_obj.dict_id
        dict_type = await DictTypeDao.get_dict_type_detail_by_info(db, DictTypeModel(dict_type=page_obj.dict_type))
        if dict_type and dict_type.dict_id != dict_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_dict_type_services(cls, request: Request, db: AsyncSession, page_obj: DictTypeModel):
        """
        新增字典类型信息
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        is_unique = await cls.check_dict_type_unique_services(db, page_obj)
        if not is_unique:
            raise ServiceException(message=f'新增字典{page_obj.dict_name}失败，字典类型已存在')
        else:
            try:
                await DictTypeDao.add_dict_type_dao(db, page_obj)
                await db.commit()
                await request.app.state.redis.set(f'{RedisInitKeyConfig.SYS_DICT.key}:{page_obj.dict_type}', '')
                result = dict(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e
        return CrudResponseModel(**result)

    @classmethod
    async def edit_dict_type_services(cls, request: Request, db: AsyncSession, page_obj: DictTypeModel):
        """
        修改字典类型信息
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        edit_dict_type = page_obj.model_dump(exclude_unset=True)
        dict_type_info = await cls.dict_type_detail_services(db, page_obj.dict_id)
        is_unique = await cls.check_dict_type_unique_services(db, page_obj)

        if dict_type_info.dict_id:
            if not is_unique:
                raise ServiceException(message=f'修改字典{page_obj.dict_name}失败，字典类型已存在')
            else:
                try:
                    query_dict_data = DictDataPageQueryModel(dict_type=dict_type_info.dict_type)
                    dict_data_list = await DictDataDao.get_dict_data_list(db, query_dict_data, is_page=True)
                    if dict_type_info.dict_type != page_obj.dict_type:
                        for dict_data in dict_data_list:
                            edit_dict_type = DictDataModel(
                                dict_code=dict_data.dict_code,
                                dict_type=page_obj.dict_type,
                                update_by=page_obj.update_by,
                            ).model_dump(exclude_unset=True)
                            await DictDataDao.edit_dict_data_dao(db, edit_dict_type)
                    await DictDataDao.edit_dict_data_dao(db, edit_dict_type)
                    await db.commit()
                    if dict_type_info.dict_type != page_obj.dict_type:
                        dict_data = [SqlalchemyUtil.serialize_result(row) for row in dict_data_list if row]
                        await request.app.state.redis.set(
                            f'{RedisInitKeyConfig.SYS_DICT.key}:{page_obj.dict_type}',
                            json.dumps(dict_data, ensure_ascii=False, default=str)
                        )
                    return CrudResponseModel(is_success=True, message='更新成功')
                except Exception as e:
                    await db.rollback()
                    raise e
        else:
            raise ServiceException(message='字典类型不存在')

    @classmethod
    async def dict_type_detail_services(cls, db: AsyncSession, dict_id: int):
        """
        获取字典类型相信信息
        :param db:
        :param dict_id:
        :return:
        """
        dict_type = await DictTypeDao.get_dict_type_detail_by_id(db, dict_id=dict_id)
        if dict_type:
            result = DictTypeModel(**SqlalchemyUtil.serialize_result(dict_type))
        else:
            result = DictTypeModel(**dict())
        return result

    @classmethod
    async def delete_dict_type_services(cls, request: Request, db: AsyncSession, page_obj: DeleteDictTypeModel):
        """
        删除字典类型
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.dict_ids:
            dict_id_list = page_obj.dict_ids.split(',')
            try:
                delete_dict_type_list = []

                for dict_id in dict_id_list:
                    dict_info = await cls.dict_type_detail_services(db, int(dict_id))
                    # 判断是否有关联字典数据
                    if (await DictDataDao.count_dict_data_from_dict_type(db, dict_info.dict_type))>0:
                        raise ServiceException(message=f'{dict_info.dict_name}已分配，不能删除')

                    await DictTypeDao.delete_dict_type_dao(db, DictTypeModel(dict_id=dict_id))

                    delete_dict_type_list.append(f'{RedisInitKeyConfig.SYS_DICT.key}:{dict_info.dict_type}')
                await db.commit()
                # 清理缓存中的类型数据
                if delete_dict_type_list:
                    await request.app.state.redis.delete(*delete_dict_type_list)

                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e

        else:
            raise ServiceException(message='字典类型id为空')

    @staticmethod
    async def export_dict_type_list_services(dict_type_list: List):
        """
        导出字典类型信息
        :param dict_type_list:
        :return:
        """
        # 创建映射
        mapping_dict = {
            'dict_id': '字典编号',
            'dict_name': '字典名称',
            'dict_type': '字典类型',
            'status': '状态',
            'create_by': '创建者',
            'create_time': '创建时间',
            'update_by': '更新者',
            'update_time': '更新时间',
            'remark': '备注',
        }

        for item in dict_type_list:
            if item.get('status') == '0':
                item['status'] = '正常'
            else:
                item['status'] = '停用'

        new_data = [
            {mapping_dict.get('key'): value for key, value in item.items() if mapping_dict.get('key')}
            for item in dict_type_list
        ]
        binary_data = export_list2excel(new_data)
        return binary_data

    @classmethod
    async def refresh_sys_dict_services(cls, request: Request, db: AsyncSession):
        """
        刷新缓存
        :param request:
        :param db:
        :return:
        """
        await DictDataService.init_cache_sys_dict_services(db, request.app.state.redis)
        result = dict(is_success=True, message='刷新成功')
        return result


class DictDataService:
    """
    字典数据管理模块service层
    """

    @classmethod
    async def get_dict_data_list_services(cls, db: AsyncSession, query_obj: DictDataPageQueryModel, is_page: bool = False):
        """
        获取字典数据列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        dict_data_list = await DictDataDao.get_dict_data_list(db, query_obj, is_page)
        return dict_data_list

    @classmethod
    async def query_dict_data_list_for_type_services(cls, db: AsyncSession, dict_type: str):
        """
        查询字典类型下的字典数据列表信息
        :param db:
        :param dict_type:
        :return:
        """
        dict_data_list = await DictDataDao.query_dict_data_list_from_dict_type(db, dict_type)
        return dict_data_list

    @classmethod
    async def init_cache_sys_dict_services(cls, db: AsyncSession, redis):
        """
        初始化: 获取所有字典类型对应的字典数据并缓存
        :param db:
        :param redis:
        :return:
        """
        # 获取sys_dict开头的键列表
        keys = await redis.keys(f'{RedisInitKeyConfig.SYS_DICT.key}:*')
        # 判断是否存在，如存在则先做删除
        if keys:
            await redis.delete(*keys)
        # 获取字典类型，并通过字典类型获取所有正常的字典数据
        dict_type_all = await DictTypeDao.get_all_dict_type(db)
        for type_obj in [item for item in dict_type_all if item.status == '0']:
            dict_type = type_obj.dict_type
            dict_data_list = await DictDataDao.query_dict_data_list_from_dict_type(db, dict_type)
            # 序列化
            dict_data = [SqlalchemyUtil.serialize_result(row) for row in dict_data_list if row]
            # 将字典数据缓存到redis
            await redis.set(
                f'{RedisInitKeyConfig.SYS_DICT.key}:{dict_type}',
                json.dumps(dict_data, ensure_ascii=False, default=str)
            )

    @classmethod
    async def query_dict_data_list_from_cache_services(cls, redis, dict_type: str):
        """
        从缓存中获取字典数据列表信息
        :param redis:
        :param dict_type:
        :return:
        """
        result = []
        dict_data_list = await redis.get(f'{RedisInitKeyConfig.SYS_DICT.key}:{dict_type}')
        if dict_data_list:
            result = json.loads(dict_data_list)

        return SqlalchemyUtil.serialize_result(result)

    @classmethod
    async def check_dict_data_unique_services(cls, db: AsyncSession, page_obj: DictDataModel):
        """
        通过dict_code校验字典数据是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        dict_code = -1 if page_obj.dict_code is None else page_obj.dict_code
        dict_data = await DictDataDao.get_dict_data_detail_by_info(db, page_obj)
        if dict_data and dict_data.dict_code != dict_code:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_dict_data_services(cls, request: Request, db: AsyncSession, page_obj: DictDataModel):
        """
        信息字典数据
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        is_unique = await cls.check_dict_data_unique_services(db, page_obj)
        if not is_unique:
            raise ServiceException(message=f'新增字典{page_obj.dict_label}失败, {page_obj.dict_type}下已存在')
        else:
            try:
                await DictDataDao.add_dict_data_dao(db, page_obj)
                await db.commit()
                # 获取字典数据并缓存
                dict_data_list = await cls.query_dict_data_list_for_type_services(db, page_obj.dict_type)
                await request.app.state.redis.set(
                    f'{RedisInitKeyConfig.SYS_DICT.key}:{page_obj.dict_type}',
                    json.dumps(SqlalchemyUtil.serialize_result(dict_data_list), ensure_ascii=False, default=str),
                )
                return CrudResponseModel(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e

    @classmethod
    async def edit_dict_data_services(cls, request: Request, db: AsyncSession, page_obj: DictDataModel):
        """
        编辑字典数据
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        edit_data_type = page_obj.model_dump(exclude_unset=True)
        # 获取字典详情数据
        dict_data_info = await cls.dict_data_detail_services(db, page_obj.dict_code)
        if dict_data_info.dict_code:
            is_unique = await cls.check_dict_data_unique_services(db, page_obj)
            if not is_unique:
                raise ServiceException(message=f'编辑字典数据{page_obj.dict_label}失败，{page_obj.dict_type}下已存在')
            else:
                try:
                    await DictDataDao.edit_dict_data_dao(db, edit_data_type)
                    await db.commit()

                    dict_data_list = await cls.query_dict_data_list_for_type_services(db, page_obj.dict_type)
                    await request.app.state.redis.set(
                        f'{RedisInitKeyConfig.SYS_DICT.key}:{page_obj.dict_type}',
                        json.dumps(SqlalchemyUtil.serialize_result(dict_data_list), ensure_ascii=False, default=str)
                    )
                    return CrudResponseModel(is_success=True, message='修改成功')
                except Exception as e:
                    await db.rollback()
                    raise e
        else:
            raise ServiceException(message='字典数据不存在')

    @classmethod
    async def dict_data_detail_services(cls, db: AsyncSession, dict_code: int):
        """
        通过code获取字典详情数据
        :param db:
        :param dict_code:
        :return:
        """
        dict_data_detail = await DictTypeDao.get_dict_type_detail_by_id(db, dict_code)
        if dict_data_detail:
            result = DictDataModel(**SqlalchemyUtil.serialize_result(dict_data_detail))
        else:
            result = DictDataModel(**dict())
        return result

    @classmethod
    async def delete_dict_data_services(cls, request: Request, db: AsyncSession, page_obj: DeleteDictDataModel):
        """
        删除字典数据
        :param request:
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.dict_codes:
            dict_code_list = page_obj.dict_codes.split(',')
            try:
                delete_dict_type_list = []
                for dict_code in dict_code_list:
                    dict_data = await cls.dict_data_detail_services(db, int(dict_code))
                    # 删除字典数据
                    await DictDataDao.delete_dict_data_dao(db, DictDataModel(dict_code=dict_code))
                    # 用于清理缓存字典数据
                    delete_dict_type_list.append(dict_data.dict_type)
                await db.commit()

                for dict_type in list(set(delete_dict_type_list)):
                    dict_data_list = await cls.query_dict_data_list_for_type_services(db, dict_type)
                    await request.app.state.redis.set(
                        f'{RedisInitKeyConfig.SYS_DICT.key}:{dict_type}',
                        json.dumps(SqlalchemyUtil.serialize_result(dict_data_list), ensure_ascii=False, default=str)
                    )
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入字典数据id为空')

    @staticmethod
    async def export_dict_data_list_services(dict_data_list: List):
        """
        导出字典数据
        :param dict_data_list:
        :return:
        """

        # 定义一个映射
        mapping_dict = {
            'dict_code': '字典编码',
            'dict_sort': '字典标签',
            'dict_label': '字典键值',
            'dict_value': '字典排序',
            'dict_type': '字典类型',
            'css_class': '样式属性',
            'list_class': '表格回显样式',
            'is_default': '是否默认',
            'status': '状态',
            'create_by': '创建者',
            'create_time': '创建时间',
            'update_by': '更新者',
            'update_time': '更新时间',
            'remark': '备注',
        }

        for item in dict_data_list:
            if item.get('status') == '0':
                item['status'] = '正常'
            else:
                item['status'] = '停用'

            if item.get('is_default') == 'Y':
                item['is_default'] = '是'
            else:
                item['is_default'] = '否'

            new_data = [
                {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)} for item in dict_data_list
            ]
            binary_data = export_list2excel(new_data)
            return binary_data