from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
import requests
from dotenv import load_dotenv

# Настройки ВКонтакте
CLIENT_ID = load_dotenv("CLIENT_ID")
REDIRECT_URI = "https://brown-kiwis-relax.loca.lt/"
VK_API_VERSION = "5.131"
CLIENT_SECRET_KEY = load_dotenv("CLIENT_SECRET")

app = FastAPI()


async def handle_vk_error(response):
    try:
        response = response["response"]
        return response
    except KeyError:
        error = response["error"]
        raise HTTPException(status_code=error["error_code"],
                            detail={"error_msg": error["error_msg"]})
    except Exception:
        raise HTTPException(status_code=520, detail="Неизвестная ошибка")