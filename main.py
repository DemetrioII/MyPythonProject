import base64
import datetime
import json
import asyncio
import httpx
from requests import *

import matplotlib.pyplot as plt
import networkx as nx

from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import CDN
from fastapi import FastAPI, Request, Form, UploadFile, File, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import datetime
from typing import Optional
from jose import JWTError, jwt
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from DataBase import Database
from passlib.context import CryptContext
import os
from hashlib import sha256
import time
from User import *
from src.schemas import *
from fastapi.middleware.cors import CORSMiddleware
from VK_helpers import *

from VK_helpers import *

VK_APP_ID = "53265566"
BASE_DOMEN = "http://localhost"

VK_SERVICE_KEY = "fea2d7a3fea2d7a3fea2d7a30efd8e133dffea2fea2d7a39947b135431f0ea0ac217ce9"
VK_API_VERSION = "5.199"

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

tasks = []

db = Database()


@app.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/refresh-token", response_model=Token)
async def refresh_token(old_token: str = Depends(oauth2_scheme)):
    try:
        # Проверяем старый токен
        payload = jwt.decode(old_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=400, detail="Invalid token")

        # Создаем новый токен
        new_token = create_access_token(data={"sub": username})
        return {"access_token": new_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# ---- Работа с аккаунтами в приложении
@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"},
                            )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.name}, expires_delta=access_token_expires
    )
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # Только сервер может читать эту куку
        samesite="lax"  # или strict, зависит от твоей архитектуры
    )
    return response


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "name": current_user.name, "photo": db.find_by_name(current_user.name)[3]}
    )

@app.post("/delete_user")
async def delete_user(request: Request, current_user: User = Depends(get_current_active_user)):
    db.delete_by_name(current_user.name)

    response = RedirectResponse(url="/register", status_code=302)
    response.delete_cookie(key="access_token")  # Точное имя куки
    return response

@app.get("/register", response_class=HTMLResponse)
async def get_register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_user(
        username: str = Form(...),
        password: str = Form(...),
        image: UploadFile = File(...)
):
    existing_user = get_user(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already registered")

    avatar = await image.read()

    hashed_password = get_password_hash(password)
    db.create_person(username, hashed_password, avatar, False)
    return {"message": "User created successfully"}

# ---- Взаимодействие с VK API

@app.get("/full-profile", tags=["Агрегированный профиль"])
async def get_full_profile(link: str):
    user_id = int(await parse(link))
    url = "https://api.vk.com/method/"
    token = VK_SERVICE_KEY
    version = "5.199"
    async with httpx.AsyncClient() as client:
        base_info = client.get(f"{url}users.get", params={
            "access_token": token,
            "user_ids": user_id,
            "v": version,
            "fields": "bdate, sex, city, relation, last_seen"
        })

        groups = client.get(f"{url}groups.get", params={
            "access_token": token,
            "user_id": user_id,
            "v": version,
            "extended": 1,
            "fields": "activity, age_limits"
        })

        wall = client.get(f"{url}wall.get", params={
            "access_token": token,
            "domain": user_id,
            "v": version
        })

        friends = client.get(f"{url}friends.get", params={
            "access_token": token,
            "user_id": user_id,
            "v": version,
            "fields": "sex,city"
        })

        followers = client.get(f"{url}users.getFollowers", params={
            "access_token": token,
            "user_id": user_id,
            "v": version,
            "fields": "sex,city"
        })

        responses = await asyncio.gather(base_info, groups, wall, friends, followers)

        data = {
            "base_info": responses[0].json().get("response", {}),
            "groups": responses[1].json().get("response", {}),
            "wall": responses[2].json().get("response", {}),
            "friends": responses[3].json().get("response", {}),
            "followers": responses[4].json().get("response", {})
        }

        for info, answer in data.items():
            if info == "base_info":
                data[info] = answer[0]
            if info == "groups":
                fields_to_keep = {'is_closed', 'deactivated', 'activity', 'age_limits', 'ban_info', 'is_favorite'}
                value_to_age = {1: 0, 2: 16, 3: 18}
                for item in data[info]['items']:
                    keys = list(item.keys())
                    for key in keys:
                        if key not in fields_to_keep:
                            del item[key]
                        if key == "age_limits":
                            item[key] = value_to_age.get(item[key], item[key])
            if info == "wall":
                if "reaction_sets" in answer:
                    del data[info]["reaction_sets"]

                fields_to_keep = {'marked_as_ads', 'date', 'from_id', 'id', 'reactions', 'owner_id', 'views'}
                for item in data[info]['items']:
                    keys = list(item.keys())
                    for key in keys:
                        if key not in fields_to_keep:
                            del item[key]
                        if key == "views":
                            item[key] = item["views"].get("count")
                        if key == "reactions":
                            item[key] = item["reactions"].get("count")

            if info == "friends":
                fields_to_keep = {'id', 'deactivated', 'sex', 'first_name', 'last_name', 'can_access_closed',
                                  'is_closed', 'city'}
                for item in data[info]['items']:
                    keys = list(item.keys())
                    for key in keys:
                        if key not in fields_to_keep:
                            del item[key]
            try:
                if info == "followers":
                    fields_to_keep = {'id', 'deactivated', 'sex', 'first_name', 'last_name', 'can_access_closed',
                                      'is_closed', 'city'}
                    for item in data[info]['items']:
                        keys = list(item.keys())
                        for key in keys:
                            if key not in fields_to_keep:
                                del item[key]
            except Exception:
                raise HTTPException(status_code=400)
        return json.dumps(data)

def get_friend_graph(user_id: int):
    G = nx.DiGraph()
    friends_params = {
        "access_token": VK_SERVICE_KEY,
        "user_id": user_id,
        "v": "5.199",
        # "count": 10 # временный параметр
    }
    friends_ids = get("https://api.vk.com/method/friends.get", params=friends_params).json()["response"]["items"]
    nodes = friends_ids
    G.add_nodes_from(nodes)
    edges = [(user_id, i) for i in nodes]
    G.add_edges_from(edges)

    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='lightblue', arrowsize=20, node_size=700, font_size=15)
    # plt.title("Визуализация ориентированного графа")
    plt.show()

# db.close()
