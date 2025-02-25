from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config.env import UploadConfig
from config.env import SwaggerConfig


def mount_staticfiles(app: FastAPI):
    """
    挂载静态文件
    """
    app.mount(f'{UploadConfig.UPLOAD_PREFIX}', StaticFiles(directory=f'{UploadConfig.UPLOAD_PATH}'), name='profile')


# def mount_static_js_css(app: FastAPI):
#     """
#     挂载静态js、css文件,解决fastapi调用cdn静态文件失败问题
#     :param app:
#     :return:
#     """
#     app.mount('/static', StaticFiles(directory=f'{SwaggerConfig.Swagger_PATH}'), name='swagger')