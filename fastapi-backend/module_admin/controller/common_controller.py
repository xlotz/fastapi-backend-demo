from fastapi import APIRouter, BackgroundTasks, Request, UploadFile, Depends, File, Query
from module_admin.service.common_service import CommonService
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.response_util import ResponseUtil


commonController = APIRouter(prefix='/common', dependencies=[Depends(LoginService.get_current_user)])


@commonController.post('/upload')
async def common_upload(request: Request, file: UploadFile = File(...)):
    """
    上传控制器
    :param request:
    :param file:
    :return:
    """
    upload_result = await CommonService.upload_service(request, file)
    logger.info('上传成功')

    return ResponseUtil.success(model_content=upload_result.result)


@commonController.get('/download')
async def common_download(
        request: Request, background_tasks: BackgroundTasks,
        file_name: str = Query(alias='fileName'),
        delete: bool = Query(),
):
    """
    下载控制器
    :param request:
    :param background_tasks:
    :param file_name:
    :param delete:
    :return:
    """

    download_result = await CommonService.download_services(background_tasks, file_name, delete)
    logger.info(download_result.message)

    return ResponseUtil.streaming(data=download_result.result)


@commonController.get('/download/resource')
async def common_download_resource(request: Request, resource=Query()):
    """
    下载
    :param request:
    :param resource:
    :return:
    """
    download_resource_result = await CommonService.download_resource_services(resource)
    logger.info(download_resource_result.message)
    return ResponseUtil.success(data=download_resource_result.result)


