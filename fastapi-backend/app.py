import uvicorn
from server import app, AppConfig


if __name__ == '__main__':
    uvicorn.run(
        app='app:app',
        host=AppConfig.app_host,
        port=AppConfig.app_port,
        reload=AppConfig.app_reload,
    )