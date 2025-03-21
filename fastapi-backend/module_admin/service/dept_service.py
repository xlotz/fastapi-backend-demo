from sqlalchemy.ext.asyncio import AsyncSession
from config.constant import CommonConstant
from sub_applications.exceptions.exception import ServiceException, ServiceWarning
from module_admin.dao.dept_dao import DeptDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.dept_vo import DeptModel, DeleteDeptModel
from utils.common_util import SqlalchemyUtil


class DeptService:
    """
    部门管理模块服务层
    """

    @classmethod
    async def get_dept_tree_services(cls, db: AsyncSession, page_obj: DeptModel, data_scope_sql: str):
        """
        获取部门树信息
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :return:
        """
        dept_list_result = await DeptDao.get_dept_list_for_tree(db, page_obj, data_scope_sql)
        dept_tree_result = cls.list_to_tree(dept_list_result)
        return dept_tree_result

    @classmethod
    async def get_dept_for_edit_option_services(cls, db: AsyncSession, page_obj: DeptModel, data_scope_sql: str):
        """
        获取部门编辑树信息
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :return:
        """
        dept_list_result = await DeptDao.get_dept_info_for_edit_option(db, page_obj, data_scope_sql)
        return SqlalchemyUtil.serialize_result(dept_list_result)

    @classmethod
    async def get_dept_list_services(cls, db: AsyncSession, page_obj: DeptModel, data_scope_sql: str):
        """
        获取部门列表信息
        :param db:
        :param page_obj:
        :param data_scope_sql:
        :return:
        """
        dept_list_result = await DeptDao.get_dept_list(db, page_obj, data_scope_sql)
        return SqlalchemyUtil.serialize_result(dept_list_result)

    @classmethod
    async def check_dept_data_scope_services(cls, db: AsyncSession, dept_id: int, data_scope_sql: str):
        """
        校验部门是否有数据权限
        :param db:
        :param dept_id:
        :param data_scope_sql:
        :return:
        """
        depts = await DeptDao.get_dept_list(db, DeptModel(dept_id=dept_id), data_scope_sql)
        if depts:
            return CrudResponseModel(is_success=True, message='校验通过')
        else:
            raise ServiceException(message='没有权限访问部门数据')

    @classmethod
    async def check_dept_name_unique_services(cls, db: AsyncSession, page_obj: DeptModel):
        """
        校验部门名称是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        dept_id = -1 if page_obj.dept_id is None else page_obj.dept_id
        dept = await DeptDao.get_dept_detail_by_info(
            db, DeptModel(dept_name=page_obj.dept_name, parent_id=page_obj.parent_id))

        if dept and dept.dept_id != dept_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_dept_services(cls, db: AsyncSession, page_obj: DeptModel):
        """
        添加部门信息
        :param db:
        :param page_obj:
        :return:
        """
        is_unique = await cls.check_dept_name_unique_services(db, page_obj)
        if not is_unique:
            raise ServiceException(message=f'新增部门{page_obj.dept_name}失败，部门名称已存在')

        parent_info = await DeptDao.get_dept_detail_by_id(db, page_obj.parent_id)

        if parent_info.status != CommonConstant.DEPT_NORMAL:
            raise ServiceException(message=f'部门{parent_info.dept_name}停用, 不允许修改')

        page_obj.ancestors = f'{parent_info.ancestors},{page_obj.parent_id}'

        try:
            await DeptDao.add_dept_dao(db, page_obj)
            await db.commit()
            return CrudResponseModel(is_success=True, message='新增成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def edit_dept_services(cls, db: AsyncSession, page_obj: DeptModel):
        """
        修改部门信息
        :param db:
        :param page_obj:
        :return:
        """
        is_unique = await cls.check_dept_name_unique_services(db, page_obj)
        count_child = await DeptDao.count_normal_children_dept_dao(db, page_obj.dept_id)
        if not is_unique:
            raise ServiceException(message=f'修改部门{page_obj.dept_name}失败，部门已存在')
        elif page_obj.dept_id == page_obj.parent_id:
            raise ServiceException(message=f'修改{page_obj.dept_name}失败，上级部门不能为自己')
        elif page_obj.status == CommonConstant.DEPT_DISABLE and count_child >0:
            raise ServiceException(message=f'修改{page_obj.dept_name}失败, 包含未停用的子部门')

        new_parent_dept = await DeptDao.get_dept_by_id(db, page_obj.parent_id)
        old_dept = await DeptDao.get_dept_by_id(db, page_obj.dept_id)

        try:
            if new_parent_dept and old_dept:
                new_ancestors = f'{new_parent_dept.ancestors},{new_parent_dept.dept_id}'
                old_ancestors = old_dept.ancestors
                page_obj.ancestors = new_ancestors

                await cls.update_dept_children(db, page_obj.dept_id, new_ancestors, old_ancestors)
            edit_dept = page_obj.model_dump(exclude_unset=True)
            await DeptDao.edit_dept_dao(db, edit_dept)

            if page_obj.status == CommonConstant.DEPT_NORMAL and page_obj.ancestors and page_obj.ancestors != 0:
                await cls.update_parent_dept_status_normal(db, page_obj)

            await db.commit()
            return CrudResponseModel(is_success=True, message='更新成功')
        except Exception as e:
            await db.rollback()
            raise e

    @classmethod
    async def delete_dept_services(cls, db: AsyncSession, page_obj: DeleteDeptModel):
        """
        删除部门信息
        :param db:
        :param page_obj:
        :return:
        """

        if page_obj.dept_ids:
            dept_id_list = page_obj.dept_ids.split(',')

            try:
                for dept_id in dept_id_list:
                    if (await DeptDao.count_children_dept_dao(db, int(dept_id))) >0:
                        raise ServiceException(message='存在下级部门, 不允许删除')
                    elif (await DeptDao.count_dept_user_dao(db, int(dept_id))) >0:
                        raise ServiceException(message='部门存在用户, 不允许删除')

                    await DeptDao.delete_dept_dao(db, DeptModel(dept_id=dept_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入部门id为空')

    @classmethod
    async def dept_detail_services(cls, db: AsyncSession, dept_id: int):
        """
        获取部门详情
        :param db:
        :param dept_id:
        :return:
        """
        dept = await DeptDao.get_dept_detail_by_id(db, dept_id=dept_id)
        if dept:
            result = DeptModel(**SqlalchemyUtil.serialize_result(dept))
        else:
            result = DeptModel(**dict())

        return result

    @classmethod
    async def list_to_tree(cls, permission_list: list):
        """
        工具方法: 根据部门列表信息生成树形嵌套数据
        :param permission_list:
        :return:
        """
        permission_list = [
            dict(key=str(item.dept_id), title=item.dept_name, value=str(item.dept_id), parent_id=str(item.parent_id))
            for item in permission_list
        ]

        # 转换id为key的字典
        mapping: dict = dict(zip(i['key'] for i in permission_list), permission_list)

        # 树容器
        container: list = []

        for d in permission_list:
            # 如果找不到父级项，则该节点为根
            parent: dict = mapping.get(d['parent_id'])
            if parent is None:
                container.append(d)
            else:
                children: list = parent.get('children')
                if not children:
                    children = []
                children.append(d)
                parent.update({'children': children})
        return container

    @classmethod
    async def replace_first(cls, original_str: str, old_str: str, new_str: str):
        """
        工具方法： 替换字符串
        :param original_str:
        :param old_str:
        :param new_str:
        :return:
        """
        if original_str.startswith(old_str):
            return original_str.replace(old_str, new_str, 1)
        else:
            return original_str

    @classmethod
    async def update_parent_dept_status_normal(cls, db: AsyncSession, dept: DeptModel):
        """
        更新父部门状态为正常
        :param db:
        :param dept:
        :return:
        """
        dept_id_list = dept.ancestors.split(',')
        await DeptDao.update_dept_status_normal_dao(db, list(map(int, dept_id_list)))

    @classmethod
    async def update_dept_children(cls, db: AsyncSession, dept_id: int, new_ancestors: str, old_ancestors: str):
        """
        更新子部门信息
        :param db:
        :param dept_id:
        :param new_ancestors:
        :param old_ancestors:
        :return:
        """
        children = await DeptDao.get_children_dept_dao(db, dept_id)
        update_child = []
        for child in children:
            child_ancestors = await cls.replace_first(child.ancestors, old_ancestors, new_ancestors)
            update_child.append({'dept_id': child.dept_id, 'ancestors': child_ancestors})

        if children:
            await DeptDao.update_dept_children_dao(db, update_child)
