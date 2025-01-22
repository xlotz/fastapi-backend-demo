from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.env import AppConfig
from sub_applications.exceptions.handle import handle_exception
from sub_applications.staticfile.handle import handle_sub_applications
from sub_applications.middlewares.handle import handle_middleware
from utils.get_db import init_create_table
from utils.get_redis import RedisUtil
from utils.log_util import logger

from module_admin.controller.login_controller import loginController
from module_admin.controller.captcha_controller import captchaController
from module_admin.controller.common_controller import commonController


# 请求生命周期事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f'{AppConfig.app_name}开始启动...')
    # 初始化建表
    await init_create_table()
    # 初始化redis连接
    app.state.redis = await RedisUtil.create_redis_pool()
    # await RedisUtil.init_sys_dict(app.state.redis)
    # await RedisUtil.init_sys_config(app.state.redis)
    logger.info(f'{AppConfig.app_name}启动成功')
    yield
    await RedisUtil.close_redis_pool(app)


# 初始化FastAPI对象
app = FastAPI(
    title=AppConfig.app_name,
    description=f'{AppConfig.app_name}API文档',
    version=AppConfig.app_version,
    lifespan=lifespan,
    debug=True,
)

# 钩子
# 加载子应用（静态文件）
handle_sub_applications(app)
# 加载中间件，包括压缩和跨域
handle_middleware(app)
# 加载全局异常插件
handle_exception(app)

# 加载路由表
controller_list = [
    {'router': loginController, 'tags': ['登录管理']},
    {'router': captchaController, 'tags': ['验证码模块']},
    {'router': commonController, 'tags': ['通用模块']},

]

for controller in controller_list:
    app.include_router(router=controller.get('router'), tags=controller.get('tags'))