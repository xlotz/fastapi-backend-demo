import re
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel
from typing import List, Optional, Union
from sub_applications.exceptions.exception import ModelValidatorException
from module_admin.entity.vo.menu_vo import MenuModel


class UserLogin(BaseModel):
    """
    用户登录模型
    """
    model_config = ConfigDict(alias_generator=to_camel)

    user_name: str = Field(description='用户名')
    password: str = Field(description='密码')
    code: Optional[str] = Field(default=None, description='验证码')
    uuid: Optional[str] = Field(default=None, description='识别码')
    login_info: Optional[dict] = Field(default=None, description='登录信息，无需传递')
    captcha_enabled: Optional[bool] = Field(default=None, description='是否开启验证码, 无需传递')


class Token(BaseModel):
    """
    token
    """
    access_token: str = Field(description='token信息')
    token_type: str = Field(description='token类型')


class CaptchaCode(BaseModel):
    """
    验证码模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    captcha_enabled: bool = Field(description='是否开启验证码')
    register_enabled: bool = Field(description='是否启用注册')
    img: str = Field(description='验证码图片')
    uuid: str = Field(description='识别码')


class MenuTreeModel(MenuModel):
    """
    菜单树模型
    """
    children: Optional[Union[List['MenuTreeModel'], None]] = Field(default=None, description='子菜单')


class MetaModel(BaseModel):
    """
    元数据模型
    """
    model_config = ConfigDict(alias_generator=to_camel)

    title: Optional[str] = Field(default=None, description='设置路由在侧边栏和面包屑中展示的名字')
    icon: Optional[str] = Field(default=None, description='设置路由和图标')
    no_cache: Optional[bool] = Field(default=None, description='设置为true, 则不会被<keep-alive>缓存')
    link: Optional[str] = Field(default=None, description='内部链接地址http(s)://开头')


class RouterModel(BaseModel):
    """
    路由模型
    """
    model_config = ConfigDict(alias_generator=to_camel)

    name: Optional[str] = Field(default=None, description='路由名称')
    path: Optional[str] = Field(default=None, description='路由地址')
    hidden: Optional[bool] = Field(default=None, description='是否隐藏路由, 为true时，不会在侧边栏出现')
    redirect: Optional[str] = Field(default=None, description='重定向，为noRedirect时，不会在导航中被点击')
    component: Optional[str] = Field(default=None, description='组件地址')
    query: Optional[str] = Field(default=None, description='路由参数,如{"id": 1}')
    always_show: Optional[str] = Field(default=None, description='当子路由声明的路由>1时，自动变成嵌套模式')
    meta: Optional[MetaModel] = Field(default=None, description='其他元素')
    children: Optional[Union[List['RouterModel'], None]] = Field(default=None, description='子路由')