from fastapi import FastAPI
from sub_applications.staticfile.staticfiles import mount_staticfiles
# from sub_applications.staticfile.staticfiles import mount_static_js_css


def handle_sub_applications(app: FastAPI):
    """
    全局处理子应用挂载
    """
    # 挂载静态文件
    mount_staticfiles(app)
    # mount_static_js_css(app)
