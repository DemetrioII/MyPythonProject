from requests import *
from fastapi import FastAPI, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from prod_config import * 
from functions import * 
from schemas import *
from fastapi.staticfiles import StaticFiles
import jinja2
import httpx
import time
import json

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

async def handle_vk_error(response): # Обработчик ошибок (либо он работает корректно, либо неверно интегрирован)
    try:
        response = response["response"]
        return response
    except KeyError:
        try:
            error = response["error"]
            raise HTTPException(status_code=400, detail={"error_code": error["error_code"],"error_msg": error["error_msg"]})
        except KeyError:
            raise HTTPException(status_code=520, detail="Неизвестная ошибка")

#не работает в связке с ручками
# async def get_user_base_info(parameters):
#     return get("https://api.vk.com/method/users.get", params=parameters).json()

#не работает в свзке с ручками
# async def get_user_friends_info(parameters):
#     return get("https://api.vk.com/method/friends.get", params=parameters).json()

@app.get("/",  tags=["Остальное"])
async def greeting():
    return {"data": "welcome"} 



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v2:app", host="127.0.0.1", port=8000, reload=True)
