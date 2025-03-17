from datetime import datetime, time
from sqlalchemy import and_, select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.do.dict_do import SysDictData, SysDictType
from module_admin.entity.vo.dict_vo import DictDataModel, DictDataPageQueryModel, DictTypeModel, DictTypePageQueryModel
from utils.page_util import PageUtil
from utils.time_format_util import list_format_datetime


class DictTypeDao:
    """
    字典类型管理模块数据操作层
    """

    @classmethod
    async def get_dict_type_detail_by_id(cls, db: AsyncSession, dict_id: int):
        """
        根据字典类型id获取字典类型详情
        :param db:
        :param dict_id:
        :return:
        """
        dict_type_info = (await db.execute(
            select(SysDictType).where(
                SysDictType.dict_id == dict_id
            )
        )).scalars().first()
        return dict_type_info

    @classmethod
    async def get_dict_type_detail_by_info(cls, db: AsyncSession, dict_type: DictTypeModel):
        """
        根据查询参数获取字典类型详情信息
        :param db:
        :param dict_type:
        :return:
        """
        dict_type_info = (await db.execute(
            select(SysDictType).where(
                SysDictType.dict_type == dict_type.dict_type if dict_type.dict_type else True,
                SysDictType.dict_name == dict_type.dict_name if dict_type.dict_name else True,
            )
        )).scalars().first()
        return dict_type_info

    @classmethod
    async def get_all_dict_type(cls, db: AsyncSession):
        """
        获取所有字典烈性信息
        :param db:
        :return:
        """
        dict_type_all = (await db.execute(
            select(SysDictType)
        )).scalars().all()
        return list_format_datetime(dict_type_all)

    @classmethod
    async def get_dict_type_list(cls, db: AsyncSession, query_obj: DictTypePageQueryModel, is_page: bool = False):
        """
        根据查询条件获取字典类型列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        start_time = datetime.combine(datetime.strptime(query_obj.begin_time, '%Y-%m-%d'), time(00, 00, 00))
        end_time = datetime.combine(datetime.strptime(query_obj.end_time, '%Y-%m-%d'), time(23, 59, 59))
        query = (
            select(SysDictType).where(
                SysDictType.dict_name.like(f'%{query_obj.dict_name}%') if query_obj.dict_name else True,
                SysDictType.dict_type.like(f'%{query_obj.dict_type}%') if query_obj.dict_type else True,
                SysDictType.create_time.between(start_time, end_time) if start_time and end_time else True,

            ).order_by(SysDictType.dict_id).distinct()
        )
        dict_type_list = await PageUtil.paginate(db, query, query_obj.page_num, query_obj.page_size, is_page)
        return dict_type_list

    @classmethod
    async def add_dict_type_dao(cls, db: AsyncSession, dict_type: DictTypeModel):
        """
        添加字典类型
        :param db:
        :param dict_type:
        :return:
        """
        db_dict_type = SysDictType(**dict_type.model_dump())
        db.add(db_dict_type)
        await db.flush()
        return db_dict_type

    @classmethod
    async def edit_dict_type_dao(cls, db: AsyncSession, dict_type: dict):
        """
        修改字典类型信息
        :param db:
        :param dict_type:
        :return:
        """
        await db.execute(update(SysDictType), [dict_type])

    @classmethod
    async def delete_dict_type_dao(cls, db: AsyncSession, dict_type: DictTypeModel):
        """
        删除字典类型信息
        :param db:
        :param dict_type:
        :return:
        """
        await db.execute(delete(SysDictType).where(SysDictType.dict_id.in_([dict_type.dict_id])))


class DictDataDao:
    """
    字典数据管理模块数据库操作层
    """
    @classmethod
    async def get_dict_data_detail_by_id(cls, db: AsyncSession, dict_code: int):
        """
        根据字典数据id获取字典数据详情
        :param db:
        :param dict_code:
        :return:
        """
        dict_data_info = (await db.execute(
            select(SysDictData).where(SysDictData.dict_code == dict_code)
        )).scalars().first()
        return dict_data_info

    @classmethod
    async def get_dict_data_detail_by_info(cls, db: AsyncSession, dict_data: DictDataModel):
        """
        根据查询参数获取字典数据详情信息
        :param db:
        :param dict_data:
        :return:
        """
        dict_data_info = (await db.execute(
            select(SysDictData).where(
                SysDictData.dict_type == dict_data.dict_type,
                SysDictData.dict_label == dict_data.dict_label,
                SysDictData.dict_value == dict_data.dict_value,
            )
        )).scalars().first()
        return dict_data_info

    @classmethod
    async def get_dict_data_list(cls, db: AsyncSession, query_obj: DictDataPageQueryModel, is_page: bool = False):
        """
        根据查询参数获取字典数据列表
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        query = (
            select(SysDictData).where(
                SysDictData.dict_type == query_obj.dict_type if query_obj.dict_type else True,
                SysDictData.dict_label.like(f'%{query_obj.dict_label}%') if query_obj.dict_label else True,
                SysDictData.status == query_obj.status if query_obj.status else True,

            ).order_by(SysDictData.dict_code).distinct()
        )
        dict_data_list = await PageUtil.paginate(db, query, query_obj.page_num, query_obj.page_size, is_page)
        return dict_data_list

    @classmethod
    async def query_dict_data_list_from_dict_type(cls, db: AsyncSession, dict_type: str):
        """
        根据字典类型查询字典数据列表信息
        :param db:
        :param dict_type:
        :return:
        """
        """
        等价sql:
        SELECT DISTINCT sys_dict_data.*
        FROM sys_dict_type
        LEFT JOIN sys_dict_data
            ON sys_dict_type.dict_type = sys_dict_data.dict_type
            AND sys_dict_data.status = '0'
        WHERE sys_dict_type.status = '0'
        ORDER BY sys_dict_data.dict_sort;
        
        使用 isouter=True（LEFT JOIN）确保即使 SysDictData 表中没有匹配的记录，SysDictType 表的记录也会被保留。
        如果不需要保留未匹配的记录，可以改为 INNER JOIN（isouter=False）。
        """
        dict_data_list = (await db.execute(
            select(SysDictData).select_from(SysDictType).where(
                SysDictType.dict_type == dict_type if dict_type else True,
                SysDictType.status == '0'
            ).join(
                SysDictData,
                and_(SysDictType.dict_type == SysDictData.dict_type, SysDictData.status == '0'),
                isouter=True,
            ).order_by(SysDictData.dict_sort).distinct()
        )).scalars().all()
        return dict_data_list

    @classmethod
    async def add_dict_data_dao(cls, db: AsyncSession, dict_data: DictDataModel):
        """
        添加字典数据数据操作
        :param db:
        :param dict_data:
        :return:
        """
        db_dict_data = SysDictData(**dict_data.model_dump())
        db.add(db_dict_data)
        await db.flush()
        return db_dict_data

    @classmethod
    async def edit_dict_data_dao(cls, db: AsyncSession, dict_data: dict):
        """
        修改字典数据
        :param db:
        :param dict_data:
        :return:
        """
        await db.execute(update(SysDictData), [dict_data])

    @classmethod
    async def delete_dict_data_dao(cls, db: AsyncSession, dict_data: DictDataModel):
        """
        删除字典数据
        :param db:
        :param dict_data:
        :return:
        """
        await db.execute(delete(SysDictData).where(SysDictData.dict_code.in_([dict_data.dict_code])))

    @classmethod
    async def count_dict_data_from_dict_type(cls, db: AsyncSession, dict_type: str):
        """
        根据字典类型统计字典数据
        :param db:
        :param dict_type:
        :return:
        """
        dict_data_count = (await db.execute(
            select(func.count('*')).select_from(SysDictData).where(
                SysDictData.dict_type == dict_type
            )
        )).scalar()
        return dict_data_count