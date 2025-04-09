# from requests import *
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from prod_config import * 
from functions import * 
from schemas import *
from fastapi.staticfiles import StaticFiles
import jinja2
import httpx

app = FastAPI()

origins = [  # будет ли иметь смысл при работе через OpenVpn?
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1"
]

# templates = Jinja2Templates("static_files")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/vk-registration", StaticFiles(directory="src/static_files/", html=True), name="static")

# @app.get("/boris")
# async def a(request: Request):
#     return templates.TemplateResponse("boris.html", {"request": request})

@app.get("/")
async def f():
    return {"message": "welcome"}

@app.get("/vkid-proxy")
async def vkid_proxy(request: Request):
    try:
        async with httpx.AsyncClient() as client:

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json",
            }

            response = await client.get(
                "https://id.vk.com/vkid_sdk_get_config",
                params={"app_id": 53265566},
                timeout=10.0
            )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"VK ID API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/vk-callback") #Сделана без обработки ошибок
async def read_items(code: int, state: str, device_id: int):
    Params =  {"code": code, "state": state, "device_id": device_id}  # Неправильный формат параметров в endpoint'ах: В /vk-callback вы ожидаете code как int, но VK обычно отправляет его как строку.
    return Params

@app.get("/auth-error") # надо понять, как обрабатывать ошибки через http заапросы
async def raise_error():
    e = HTTPException(status_code="401", detail="Authentication error")
    return e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v_last:app", host="127.0.0.1", port=8000, reload=True)

