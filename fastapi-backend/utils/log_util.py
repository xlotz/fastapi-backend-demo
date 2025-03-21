import os
import time
from loguru import logger
from config.env import LogConfig

# log_path = os.path.join(os.getcwd(), 'logs')
log_path = LogConfig.LOG_PATH
if not os.path.exists(log_path):
    os.mkdir(log_path)

log_path_error = os.path.join(log_path, f'{time.strftime("%Y-%m-%d")}_error.log')

logger.add(log_path_error, rotation='50MB', encoding='utf-8', enqueue=True, compression='zip')