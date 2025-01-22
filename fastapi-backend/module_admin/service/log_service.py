from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sub_applications.exceptions.exception import ServiceException
from module_admin.dao.log_dao import LoginLogDao, OperationLogDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.log_vo import (
    DeleteLoginLogModel, DeleteOperLogModel,
    LogininforModel, OperLogModel,
    LoginLogQueryModel, LoginLogPageQueryModel,
    OperLogQueryModel, OperLogPageQueryModel,
    UnlockUser,
)
from utils.common_util import export_list2excel


class LoginLogService:
    """
    登录日志服务层
    """

    @classmethod
    async def get_login_log_list_services(cls, db: AsyncSession, query_obj: LoginLogPageQueryModel, is_page=False):
        """
        获取登录日志
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        operation_log_list_result = await LoginLogDao.get_login_log_list(db, query_obj, is_page)
        return operation_log_list_result

    @classmethod
    async def add_login_log_services(cls, db: AsyncSession, page_obj: LogininforModel):
        """
        新增登录日志
        :param db:
        :param page_obj:
        :return:
        """
        try:
            await LoginLogDao.add_login_log_dao(db, page_obj)
            await db.commit()
            return CrudResponseModel(is_success=True, message='新增成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def delete_login_log_services(cls, db: AsyncSession, page_obj: DeleteLoginLogModel):
        """
        删除登录日志
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.info_ids:
            info_id_list = page_obj.info_ids.split(',')
            try:
                for info_id in info_id_list:
                    await LoginLogDao.delete_login_log_dao(db, LogininforModel(infoId=info_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入日志id为空')

    @classmethod
    async def clear_login_log_services(cls, db: AsyncSession):
        """
        清空登录日志
        :param db:
        :return:
        """
        try:
            await LoginLogDao.clear_login_log_dao(db)
            await db.commit()
            return CrudResponseModel(is_success=True, message='清空成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def unlock_user_services(cls, request: Request, unlock_user: UnlockUser):
        """
        解锁用户
        :param request:
        :param unlock_user:
        :return:
        """
        locked_user = await request.app.state.redis.get(f'account_lock:{unlock_user.user_name}')
        if locked_user:
            await request.app.state.redis.delete(f'account_lock:{unlock_user.user_name}')
            return CrudResponseModel(is_success=True, message="解锁成功")
        else:
            raise ServiceException(message='该用户未锁定')

    @classmethod
    async def export_login_log_list_services(login_log_list: List):
        """
        导出登录日志
        :return:
        """
        # 创建一个映射字典，将英文键映射到中文键
        mapping_dict = {
            'infoId': '访问编号',
            'userName': '用户名称',
            'ipaddr': '登录地址',
            'loginLocation': '登录地点',
            'browser': '浏览器',
            'os': '操作系统',
            'status': '登录状态',
            'msg': '操作信息',
            'loginTime': '登录日期',
        }

        data = login_log_list

        for item in data:
            if item.get('status') == '0':
                item['status'] = '成功'
            else:
                item['status'] = '失败'
        new_data = [
            {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)} for item in data
        ]
        binary_data = export_list2excel(new_data)

        return binary_data


class OperationLogService:
    """
    操作日志服务层
    """

    @classmethod
    async def get_operation_log_list_services(cls, db: AsyncSession, query_obj: OperLogPageQueryModel, is_page=False):
        """
        获取操作日志列表
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        operation_log_list_result = await OperationLogDao.get_operation_log_list(db, query_obj, is_page)
        return operation_log_list_result

    @classmethod
    async def add_operation_log_services(cls, db: AsyncSession, page_obj: OperLogModel):
        """
        添加操作日志
        :param db:
        :param page_obj:
        :return:
        """
        try:
            await OperationLogDao.add_operation_log_dao(db, page_obj)
            await db.commit()
            return CrudResponseModel(is_success=True, message='添加成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def delete_operation_log_services(cls, db: AsyncSession, page_obj: DeleteOperLogModel):
        """
        删除操作日志
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.oper_ids:
            oper_id_list = page_obj.oper_ids.split(',')
            try:
                for oper_id in oper_id_list:
                    await OperationLogDao.delete_operation_log_dao(db, OperLogModel(operId=oper_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入日志id为空')

    @classmethod
    async def clear_operation_log_services(cls, db: AsyncSession):
        """
        清空操作日志
        :param db:
        :return:
        """

        try:
            await OperationLogDao.clear_operation_log_dao(db)
            await db.commit()
            return CrudResponseModel(is_success=True, message='清除成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def export_operation_log_services(cls, request: Request, operation_log_list: List):
        """
        导出操作日志
        :param request:
        :param operation_log_list:
        :return:
        """
        # 创建一个映射字典，将英文键映射到中文键
        mapping_dict = {
            'operId': '日志编号',
            'title': '系统模块',
            'businessType': '操作类型',
            'method': '方法名称',
            'requestMethod': '请求方式',
            'operName': '操作人员',
            'deptName': '部门名称',
            'operUrl': '请求URL',
            'operIp': '操作地址',
            'operLocation': '操作地点',
            'operParam': '请求参数',
            'jsonResult': '返回参数',
            'status': '操作状态',
            'error_msg': '错误消息',
            'operTime': '操作日期',
            'costTime': '消耗时间（毫秒）',
        }

        pass
        # data = operation_log_list
        # operation_type_list = await DictDataService.query_dict_data_list_from_cache_services(
        #     request.app.state.redis, dict_type='sys_oper_type'
        # )
        # operation_type_option = [
        #     dict(label=item.get('dictLabel'), value=item.get('dictValue')) for item in operation_type_list
        # ]
        # operation_type_option_dict = {item.get('value'): item for item in operation_type_option}
        #
        # for item in data:
        #     if item.get('status') == 0:
        #         item['status'] = '成功'
        #     else:
        #         item['status'] = '失败'
        #     if str(item.get('businessType')) in operation_type_option_dict.keys():
        #         item['businessType'] = operation_type_option_dict.get(str(item.get('businessType'))).get('label')
        #
        # new_data = [
        #     {mapping_dict.get(key): value for key, value in item.items() if mapping_dict.get(key)} for item in data
        # ]
        # binary_data = export_list2excel(new_data)
        #
        # return binary_data
