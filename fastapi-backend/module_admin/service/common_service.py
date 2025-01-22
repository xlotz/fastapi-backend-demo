import os
from datetime import datetime
from fastapi import BackgroundTasks, Request, UploadFile
from config.env import UploadConfig
from sub_applications.exceptions.exception import ServiceException
from module_admin.entity.vo.common_vo import CrudResponseModel, UploadResponseModel
from utils.upload_util import UploadUtil


class CommonService:
    """
    通用模块服务层
    """

    @classmethod
    async def upload_service(cls, request: Request, file: UploadFile):
        """
        通用上传service
        :param request:
        :param file:
        :return:
        """
        if not UploadUtil.check_file_extension(file):
            raise ServiceException(message='文件类型不合法')
        else:
            relative_path = f'upload/{datetime.now().strftime("%Y")}/{datetime.now().strftime("%m")}/' \
                            f'{datetime.now().strftime("%d")}'
            dir_path = os.path.join(UploadConfig.UPLOAD_PATH, relative_path)
            try:
                os.makedirs(dir_path)
            except FileExistsError:
                pass

            filename = f'{file.filename.rsplit(".", 1)[0]}_{datetime.now().strftime("%Y%m%d%H%M%S")}' \
                       f'{UploadConfig.UPLOAD_MACHINE}{UploadUtil.generate_random_number()}.{file.filename.rsplit(".")[-1]}'
            filepath = os.path.join(dir_path, filename)
            with open(filepath, 'wb') as f:
                # 流式写出大文件，基础10MB
                for chunk in iter(lambda: file.file.read(1024*1024*10), b''):
                    f.write(chunk)

            return CrudResponseModel(
                is_success=True,
                result=UploadResponseModel(fileNmae=f'{UploadConfig.UPLOAD_PREFIX}/{relative_path}/{filename}',
                                           newFileName=filename, originalFilename=file.filename,
                                           url=f'{request.base_url}{UploadConfig.UPLOAD_PREFIX[1:]}/{relative_path}/{filename}',
                ),
                message='上传成功',
            )

    @classmethod
    async def download_services(cls, background_tasks: BackgroundTasks, file_name, delete):
        """
        下载 下载目录文件
        :param background_tasks:
        :param file_name:
        :param delete:
        :return:
        """
        filepath = os.path.join(UploadConfig.DOWNLOAD_PATH, file_name)
        if '..' in file_name:
            raise ServiceException(message='文件名称不合法')
        elif not UploadUtil.check_file_exists(filepath):
            raise ServiceException(message='文件不存在')
        else:
            if delete:
                background_tasks.add_task(UploadUtil.delete_file, filepath)
            return CrudResponseModel(is_success=True, result=UploadUtil.generate_file(filepath), message='下载成功')

    @classmethod
    async def download_resource_services(cls, resource):
        """
        下载 上传目录文件
        :param resource:
        :return:
        """
        filepath = os.path.join(resource.replace(UploadConfig.UPLOAD_PREFIX, UploadConfig.UPLOAD_PATH))
        filename = resource.rsplit('/', 1)[-1]
        if (
                '..' in filename
                or not UploadUtil.check_file_timestamp(filename)
                or not UploadUtil.check_file_machine(filename)
                or not UploadUtil.check_file_random_code(filename)
        ):
            raise ServiceException(message='文件名称不合法')
        elif not UploadUtil.check_file_exists(filepath):
            raise ServiceException(message='文件不存在')
        else:
            return CrudResponseModel(is_success=True, result=UploadUtil.generate_file(filepath), message='下载成功')
