from dotenv import load_dotenv
import os
# from pydantic import BaseModel
# from pydantic_settings import BaseSettings, SettingsConfigDict

# class Settings(BaseSettings):
#     VK_APP_ID: int

#     model_config = SettingsConfigDict(env_file=".env")

load_dotenv()  # Загружает переменные из .env файла

VK_APP_ID = os.getenv("VK_APP_ID")
VK_SERVICE_KEY = "fea2d7a3fea2d7a3fea2d7a30efd8e133dffea2fea2d7a39947b135431f0ea0ac217ce9"
VK_API_VERSION = "5.199"
VK_REDIRECTION_URI = "http://localhost/vk-callback"


# print(BASE_DOMEN)
