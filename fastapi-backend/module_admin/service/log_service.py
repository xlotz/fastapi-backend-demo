from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sub_applications.exceptions.exception import ServiceException
from module_admin.dao.log_dao import LoginLogDao, OperationLogDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.log_vo import (
    LogininforModel, LoginLogPageQueryModel,
    DeleteLoginLogModel, DeleteOperLogModel,
    OperLogModel, OperLogPageQueryModel,
    UnlockUser,
)
from module_admin.service.dict_service import DictDataService
from utils.common_util import export_list2excel


class OperationLogService:
    """
    操作日志管理模块服务层
    """

    @classmethod
    async def get_operation_log_list(cls, db: AsyncSession, query_obj: OperLogPageQueryModel, is_page: bool = False):
        """
        获取操作日志列表信息
        :param db:
        :param query_obj:
        :param is_page:
        :return:
        """
        operation_log_list = await OperationLogDao.get_operation_log_list(db, query_obj, is_page)
        return operation_log_list

    @classmethod
    async def add_operation_log_services(cls, db: AsyncSession, page_obj: OperLogModel):
        """
        新增操作日志
        :param db:
        :param page_obj:
        :return:
        """
        try:
            await OperationLogDao.add_operation_log_dao(db, page_obj)
            await db.commit()
            return CrudResponseModel(is_success=True, message='新增成功')
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
                    await OperationLogDao.delete_operation_log_dao(db, OperLogModel(oper_id=oper_id))
                    await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入操作日志id为空')

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
            return CrudResponseModel(is_success=True, message='清空成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def export_operation_log_list_services(cls, request: Request, oper_log_list: List):
        """
        导出操作日志
        :param request:
        :param oper_log_list:
        :return:
        """
        # 创建映射
        mapping_dict = {
            'oper_id': '日志编号',
            'title': '系统模块',
            'business_type': '操作类型',
            'method': '方法名称',
            'request_method': '请求方式',
            'oper_name': '操作人员',
            'dept_name': '部门名称',
            'oper_url': '请求URL',
            'oper_ip': '操作地址',
            'oper_location': '操作地点',
            'oper_param': '请求参数',
            'json_result': '返回参数',
            'status': '操作状态',
            'error_msg': '错误消息',
            'oper_time': '操作日期',
            'cost_time': '消耗时间（毫秒）',
        }

        oper_type_list = await DictDataService.query_dict_data_list_from_cache_services(
            request.app.state.redis, dict_type='sys_oper_type'
        )
        operation_type_option = [
            dict(label=item.get('dict_label'), value=item.get('dict_value')) for item in oper_type_list
        ]
        oper_type_option_dict = {item.get('value'): item for item in operation_type_option}

        for item in oper_log_list:
            if item.get('status') == 0:
                item['status'] = '成功'
            else:
                item['status'] = '失败'
            if str(item.get('business_type')) in oper_type_option_dict.keys():
                item['business_type'] = oper_type_option_dict.get(str(item.get('business_type'))).get('label')

        new_data = [
            {mapping_dict.get(key): value
             for key, value in item.items() if mapping_dict.get(key)} for item in oper_log_list
        ]
        binary_data = export_list2excel(new_data)

        return binary_data


class LoginLogService:
    """
    登录日志挂你模块服务层
    """

    @classmethod
    async def get_login_log_list(cls, db: AsyncSession, login_obj: LoginLogPageQueryModel, is_page: bool = False):
        """
        获取登录日志列表
        :param db:
        :param login_obj:
        :param is_page:
        :return:
        """
        login_log_list = await LoginLogDao.get_login_log_list(db, login_obj, is_page)
        return login_log_list

    @classmethod
    async def add_login_log_services(cls, db: AsyncSession, login_obj: LogininforModel):
        """
        添加登录日志
        :param db:
        :param login_obj:
        :return:
        """
        try:
            await LoginLogDao.add_login_log_dao(db, login_obj)
            await db.commit()
            return CrudResponseModel(is_success=True, message='添加成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def delete_login_log_services(cls, db: AsyncSession, login_obj: DeleteLoginLogModel):
        """
        删除登录日志
        :param db:
        :param login_obj:
        :return:
        """
        if login_obj.info_ids:
            info_id_list = login_obj.info_ids.split(',')
            try:
                for info_id in info_id_list:
                    await LoginLogDao.delete_login_log_dao(db, LogininforModel(info_id=info_id))
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
    async def unlock_user_services(cls, request: Request, db: AsyncSession, unlock_user: UnlockUser):
        """
        解锁用户
        :param request:
        :param db:
        :param unlock_user:
        :return:
        """
        # 获取被锁用户
        locked_user = await request.app.state.redis.get(f'account_lock:{unlock_user.user_name}')
        if locked_user:
            await request.app.state.redis.delete(f'account_local:{unlock_user.user_name}')
            return CrudResponseModel(is_success=True, message='解锁成功')
        else:
            raise ServiceException(message='该用户未锁定')

    @staticmethod
    async def export_login_log_list_services(login_log_list: List):
        """
        导出登录日志
        :param login_log_list:
        :return:
        """
        # 新建映射
        mapping_dict = {
            'info_id': '访问编号',
            'user_name': '用户名称',
            'ipaddr': '登录地址',
            'login_location': '登录地点',
            'browser': '浏览器',
            'os': '操作系统',
            'status': '登录状态',
            'msg': '操作信息',
            'login_time': '登录日期',
        }

        for item in login_log_list:
            if item.get('status') == '0':
                item['status'] = '成功'
            else:
                item['status'] = '失败'
        new_data = [
            {mapping_dict.get(key): value
             for key, value in item.items() if mapping_dict.get(key)} for item in login_log_list
        ]
        binary_data = export_list2excel(new_data)

        return binary_data
