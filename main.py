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
from functions import *
from functions import *


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
