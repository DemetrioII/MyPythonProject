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

@app.get("/user-base-info/{user_id}", tags=["Остальное"])
async def get_user_info(user_id: int): # handle_errors: callable = Depends(handle_vk_error)

    params = {
        "access_token": VK_SERVICE_KEY,
        "user_ids": user_id, 
        "v":"5.199"
    }
    response = get("https://api.vk.com/method/users.get", params=params).json()
    return response

@app.get("/user-friends/{user_id}", tags=["Друзья/подписчики"])
async def get_user_friends(user_id: int):

    friends_params = {
        "access_token": VK_SERVICE_KEY, 
        "user_id": user_id, 
        "v":"5.199",
    }
    response = get("https://api.vk.com/method/friends.get", params=friends_params).json()
    try:
        friends_ids = response["response"]
    except KeyError:
        try:
            error = response["error"]
            return {"error_code": error["error_code"],"error_msg": error["error_msg"]}
        except KeyError:
            return HTTPException(status_code=520, detail="Неизвестная ошибка")
    data = dict()
    for id in friends_ids["items"]:
        user_params = {
            "access_token": VK_SERVICE_KEY, 
            "user_ids": id, 
            "v":"5.199",
        }
        user_info = get("https://api.vk.com/method/users.get", params=user_params).json()
        time.sleep(0.2)
        tmp_user_info = user_info["response"][0]
        data[id] = {"first_name": tmp_user_info["first_name"], "last_name": tmp_user_info["last_name"]}

    return data


@app.get("/user-followers/{user_id}", tags=["Друзья/подписчики"])
async def get_users_followers(user_id: int):

    followers_params = {
        "access_token": VK_SERVICE_KEY, 
        "user_id": user_id, 
        "v":"5.199",
    }
    response = get("https://api.vk.com/method/users.getFollowers", params=followers_params).json()
    try:
        friends_ids = response["response"]
    except KeyError:
        try:
            error = response["error"]
            return {"error_code": error["error_code"],"error_msg": error["error_msg"]}
        except KeyError:
            return HTTPException(status_code=520, detail="Неизвестная ошибка")
    data = dict()

    for id in friends_ids["items"]:
        user_params = {
            "access_token": VK_SERVICE_KEY, 
            "user_ids": id, 
            "v":"5.199",
        }
        user_info = get("https://api.vk.com/method/users.get", params=user_params).json()
        time.sleep(0.2)
        tmp_user_info = user_info["response"][0]
        data[id] = {"first_name": tmp_user_info["first_name"], "last_name": tmp_user_info["last_name"]}

    return data

@app.get("/user-subscriptions/{user_id}", tags=["Друзья/подписчики"])
async def get_users_followers(user_id: int):

    subscriptions_params = {
        "access_token": VK_SERVICE_KEY, 
        "user_id": user_id, 
        "v":"5.199",
    }
    response = get("https://api.vk.com/method/users.getSubscriptions", params=subscriptions_params).json()
    try:
        friends_ids = response["response"]
    except KeyError:
        try:
            error = response["error"]
            return {"error_code": error["error_code"],"error_msg": error["error_msg"]}
        except KeyError:
            return HTTPException(status_code=520, detail="Неизвестная ошибка")
    data = dict()

    for id in friends_ids["items"]:
        user_params = {
            "access_token": VK_SERVICE_KEY, 
            "user_ids": id, 
            "v":"5.199",
        }
        user_info = get("https://api.vk.com/method/users.get", params=user_params).json()
        time.sleep(0.2)
        tmp_user_info = user_info["response"][0]
        data[id] = {"first_name": tmp_user_info["first_name"], "last_name": tmp_user_info["last_name"]}

    return data


@app.get("/user-wall/{user_id}", tags=["Стена"])
async def get_user_wall_info(user_id: int):
    params = {
        "access_token": VK_SERVICE_KEY,
        "domain": user_id, 
        "v":"5.199",
        "extended": 1
    }
    response = get("https://api.vk.com/method/wall.get", params=params).json()
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v2:app", host="127.0.0.1", port=8000, reload=True)
