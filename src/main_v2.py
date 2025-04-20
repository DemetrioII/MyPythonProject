from requests import *
from fastapi import FastAPI, HTTPException, Request
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

#не работает в связке с ручками
async def get_user_base_info(parameters):
    return get("https://api.vk.com/method/users.get", params=parameters).json()

#не работает в свзке с ручками
async def get_user_friends_info(parameters):
    return get("https://api.vk.com/method/friends.get", params=parameters).json()

@app.get("/user-base-info/{user_id}")
async def get_user_info(user_id: int):

    params = {
        "access_token": VK_SERVICE_KEY,
        "user_ids": user_id, 
        "v":"5.199"
    }

    return get("https://api.vk.com/method/users.get", params=params).json()

@app.get("/user-friends/{user_id}")
async def get_user_info(user_id: int):

    friends_params = {
        "access_token": VK_SERVICE_KEY, 
        "user_id": user_id, 
        "v":"5.199",
        # "count": 10 # временный параметр
    }

    friends_ids = get("https://api.vk.com/method/friends.get", params=friends_params).json()

    data = dict()
    for id in friends_ids["response"]["items"]:
        user_params = {
            "access_token": VK_SERVICE_KEY, 
            "user_ids": id, 
            "v":"5.199",
        }
        user_info = get("https://api.vk.com/method/users.get", params=user_params).json()
        time.sleep(0.1)

        # tmp_user_info = user_info["response"][0]
        # del tmp_user_info["id"]
        # del tmp_user_info["can_access_closed"]
        # del tmp_user_info["is_closed"]

        tmp_user_info = user_info["response"][0]
        data[id] = {"first_name": tmp_user_info["first_name"], "last_name": tmp_user_info["last_name"]}
        # data[id] = tmp_user_info

    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v2:app", host="127.0.0.1", port=8000, reload=True)

