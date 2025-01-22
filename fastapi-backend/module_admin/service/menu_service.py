from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from config.constant import CommonConstant, MenuConstant
from sub_applications.exceptions.exception import ServiceException, ServiceWarning
from module_admin.dao.menu_dao import MenuDao
from module_admin.dao.role_dao import RoleDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.menu_vo import DeleteMenuModel, MenuQueryModel, MenuModel
from module_admin.entity.vo.role_vo import RoleMenuQueryModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from utils.common_util import CamelCaseUtil
from utils.string_util import StringUtil


class MenuService:
    """
    裁断管理服务层
    """

    @classmethod
    async def get_menu_tree_services(cls, db: AsyncSession, current_user: Optional[CurrentUserModel] = None):
        """
        获取菜单树信息services
        :param db:
        :param current_user:
        :return:
        """
        menu_list_result = await MenuDao.get_menu_list_for_tree(
            db, current_user.user.user_id, current_user.user.role
        )
        menu_tree_result = cls.list_to_tree(menu_list_result)
        return menu_tree_result

    @classmethod
    async def get_role_menu_tree_services(cls, db: AsyncSession, role_id, current_user: Optional[CurrentUserModel] = None):
        """
        根据角色id获取菜单树信息
        :param db:
        :param role_id:
        :param current_user:
        :return:
        """
        # 获取菜单列表
        menu_list_result = await MenuDao.get_menu_list_for_tree(
            db, current_user.user.user_id, current_user.user.role
        )
        # 数据转换
        menu_tree_result = cls.list_to_tree(menu_list_result)
        # 获取角色
        role = await RoleDao.get_role_detail_by_id(db, role_id)
        # 通过角色获取关联的菜单
        role_menu_list = await RoleDao.get_role_menu_dao(db, role)

        checked_keys = [row.menu_id for row in role_menu_list]
        result = RoleMenuQueryModel(menus=menu_tree_result, checkedKeys=checked_keys)

        return result

    @classmethod
    async def get_menu_list_services(
            cls, db: AsyncSession, page_obj: MenuQueryModel, current_user: Optional[CurrentUserModel] = None
    ):
        """
        获取菜单列表
        :param db:
        :param page_obj:
        :param current_user:
        :return:
        """
        menu_list_result = await MenuDao.get_menu_list(db, page_obj, current_user.user.user_id, current_user.user.role)
        return CamelCaseUtil.transform_result(menu_list_result)

    @classmethod
    async def check_menu_name_unique_services(cls, db: AsyncSession, page_obj: MenuModel):
        """
        校验菜单名是否唯一
        :param db:
        :param page_obj:
        :return:
        """
        menu_id = -1 if page_obj.menu_id is None else page_obj.menu_id
        menu = await MenuDao.get_menu_detail_by_info(db, MenuModel(menuName=page_obj.menu_name))
        if menu and menu.menu_id != menu_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_menu_services(cls, db: AsyncSession, page_obj: MenuModel):
        """
        添加菜单
        :param db:
        :param page_obj:
        :return:
        """
        if not await cls.check_menu_name_unique_services(db, page_obj):
            raise ServiceException(message=f'新增菜单{page_obj.menu_name}失败，菜单名称已存在')
        elif page_obj.is_frame == MenuConstant.YES_FRAME and not StringUtil.is_http(page_obj.path):
            raise ServiceException(message=f'新增菜单{page_obj.menu_name}失败，地址必须以http(s)://开头')
        else:
            try:
                await MenuDao.add_menu_dao(db, page_obj)
                await db.commit()
                return CrudResponseModel(is_success=True, message='新增成功')
            except Exception as e:
                await db.rollback()
                raise e

    @classmethod
    async def edit_menu_services(cls, db: AsyncSession, page_obj: MenuModel):
        """
        编辑菜单
        :param db:
        :param page_obj:
        :return:
        """
        edit_menu = page_obj.model_dump(exclude_unset=True)
        menu_info = await cls.menu_detail_services(db, page_obj)
        if menu_info.menu_id:
            if not await cls.check_menu_name_unique_services(db, page_obj):
                raise ServiceException(message=f'修改菜单{page_obj.menu_name}失败，菜单名称已存在')
            elif page_obj.is_frame == MenuConstant.YES_FRAME and not StringUtil.is_http(page_obj.path):
                raise ServiceException(message=f'修改菜单{page_obj.menu_name}失败，地址必须以http(s)://开头')
            else:
                try:
                    await MenuDao.edit_menu_dao(db, edit_menu)
                    await db.commit()
                    return CrudResponseModel(is_success=True, message='修改成功')
                except Exception as e:
                    await db.rollback()
                    raise e
        else:
            raise ServiceException(message='菜单不存在')

    @classmethod
    async def delete_menu_services(cls,db: AsyncSession, page_obj: DeleteMenuModel):
        """
        删除菜单
        :param db:
        :param page_obj:
        :return:
        """
        if page_obj.menu_ids:
            menu_id_list = page_obj.menu_ids.split(',')
            try:
                for menu_id in menu_id_list:
                    if (await MenuDao.has_child_by_menu_id_dao(db, int(menu_id))) > 0:
                        raise ServiceWarning(message='存在子菜单,不允许删除')
                    elif (await MenuDao.check_menu_exist_role_dao(db, int(menu_id))) > 0:
                        raise ServiceWarning(message='菜单已分配,不允许删除')
                    await MenuDao.delete_menu_dao(db, MenuModel(menuId=menu_id))
                await db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await db.rollback()
                raise e
        else:
            raise ServiceException(message='传入菜单id为空')

    @classmethod
    async def menu_detail_services(cls, db: AsyncSession, menu_id):
        """
        获取菜单详细信息
        :param db:
        :param menu_id:
        :return:
        """
        menu = await MenuDao.get_menu_detail_by_id(db, menu_id)
        if menu:
            result = MenuModel(**CamelCaseUtil.transform_result(menu))
        else:
            result = MenuModel(**dict())
        return result

    @classmethod
    async def list_to_tree(cls, permission_list):
        """
        工具方法： 根据菜单列表信息生成树形嵌套数据
        :param permission_list:
        :return:
        """
        permission_list = [
            dict(id=item.menu_id, label=item.menu_name, parentId=item.parent_id) for item in permission_list
        ]

        # 将id 转成key
        mapping = dict(zip([i['id'] for i in permission_list], permission_list))

        # 树容器
        container = []
        for d in permission_list:
            # 如果找不到父级，则为根
            parent = mapping.get(d['parentId'])

            if parent is None:
                container.append(d)
            else:
                children = parent.get('children')
                if not children:
                    children = []
                children.append(d)
                parent.update({'children': children})
        return container
