from fastapi import Depends
from typing import List, Union
from sub_applications.exceptions.exception import PermissionException
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService


class CheckUserInterfaceAuth:
    """
    校验当前用户是否有接口权限
    """

    def __init__(self, perm: Union[str, list], is_strict: bool = False):
        """
        校验当前用户是否有接口权限
        :param perm:
        :param is_strict:
        """
        self.perm = perm
        self.is_strict = is_strict

    def __call__(self, current_user: CurrentUserModel = Depends(LoginService.get_current_user)):
        user_auth_list = current_user.permissions
        if '*:*:*' in user_auth_list:
            return True
        if isinstance(self.perm, str):
            if self.perm in user_auth_list:
                return True
        if isinstance(self.perm, list):
            if self.is_strict:
                if all([perm_str in user_auth_list for perm_str in self.perm]):
                    return True
            else:
                if any([perm_str in user_auth_list for perm_str in self.perm]):
                    return True
        raise PermissionException(data='', message='该用户无此接口权限')


class CheckRoleInterfaceAuth:
    """
    根据角色校验当前用户是否具有相应的接口权限
    """

    def __init__(self, role_key: Union[str, List], is_strict: bool = False):
        """
        根据角色校验当前用户是否有相应接口权限
        :param role_key:
        :param is_strict:
        """
        self.role_key = role_key
        self.is_strict = is_strict

    def __call__(self, current_user: CurrentUserModel = Depends(LoginService.get_current_user)):
        user_role_list = current_user.user.role
        user_role_key_list = [role.role_key for role in user_role_list]

        if isinstance(self.role_key, str):
            if self.role_key in user_role_key_list:
                return True
        if isinstance(self.role_key, list):
            if self.is_strict:
                if all([role_key_str in user_role_key_list for role_key_str in self.role_key]):
                    return True
            else:
                if any([role_key_str in user_role_key_list for role_key_str in self.role_key]):
                    return True

        raise PermissionException(data='', message='该用户无此接口权限')