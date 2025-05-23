from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import httpx
import json

# Настройки ВКонтакте
CLIENT_ID = load_dotenv("CLIENT_ID")
REDIRECT_URI = "https://brown-kiwis-relax.loca.lt/"
VK_API_VERSION = "5.199"
CLIENT_SECRET_KEY = load_dotenv("CLIENT_SECRET")
VK_SERVICE_KEY = "fea2d7a3fea2d7a3fea2d7a30efd8e133dffea2fea2d7a39947b135431f0ea0ac217ce9"

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

async def parse(link: str):
    try:
        name = link.split("/")[-1]
        if name[:2] == "id":
            return name[2:]
        else:
            params = {
                "access_token": VK_SERVICE_KEY,
                "user_ids": name,
                "v": "5.199",
            }
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.vk.com/method/users.get", params=params)
            data = response.json()
            # data = await handle_vk_error(data)
            user_id = data["response"][0].get("id", 0)
            return json.dumps(user_id, ensure_ascii=False)
    except:
        raise HTTPException(status_code=400, detail="Неверный формат ссылки")
