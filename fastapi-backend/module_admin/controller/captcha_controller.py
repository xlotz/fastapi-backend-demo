import uuid
from datetime import timedelta
from fastapi import APIRouter, Request
from config.enums import RedisInitKeyConfig
from module_admin.entity.vo.login_vo import CaptchaCode
from module_admin.service.captcha_service import CaptchaService
from utils.response_util import ResponseUtil
from utils.log_util import logger


captchaController = APIRouter()


@captchaController.get('/captchaImage')
async def get_captcha_image(request: Request):
    login_is_enabled = await request.app.state.redis.get(
        f'{RedisInitKeyConfig.SYS_CONFIG.key}:sys.account.captchaEnabled')
    captcha_enabled = True if login_is_enabled == 'true' else False
    register_enabled = (
        True
        if await request.app.state.redis.get(f'{RedisInitKeyConfig.SYS_CONFIG.key}:sys.account.registerUser') == 'true'
        else False
    )
    session_id = str(uuid.uuid4())
    captcha_result = await CaptchaService.create_captcha_image_service()
    image = captcha_result[0]
    computed_result = captcha_result[1]
    await request.app.state.redis.set(
        f'{RedisInitKeyConfig.CAPTCHA_CODES.key}:{session_id}', computed_result, ex=timedelta(minutes=2)
    )

    model_content = CaptchaCode(
        captchaEnabled=captcha_enabled, registerEnabled=register_enabled, img=image, uuid=session_id
    )
    logger.info(model_content)

    return ResponseUtil.success(
        model_content=CaptchaCode(
            captchaEnabled=captcha_enabled, registerEnabled=register_enabled, img=image, uuid=session_id
        )
    )


