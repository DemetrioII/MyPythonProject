import base64
import datetime

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

from VK_ID import *

VK_APP_ID = "53265566"
VK_APP_SERVICE = "fea2d7a3fea2d7a3fea2d7a30efd8e133dffea2fea2d7a39947b135431f0ea0ac217ce9"
BASE_DOMEN = "http://localhost"

VK_APP_ID = os.getenv("VK_APP_ID")
VK_SERVICE_KEY = "fea2d7a3fea2d7a3fea2d7a30efd8e133dffea2fea2d7a39947b135431f0ea0ac217ce9"
VK_API_VERSION = "5.199"
VK_REDIRECTION_URI = "http://localhost/vk-callback"

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

tasks = []

db = Database()


@app.get("/", response_class=HTMLResponse)
async def index():
    """Главная страница с кнопкой авторизации"""
    html = """
    <h1>Авторизация через ВКонтакте</h1>
    <a href="{link}" class="btn btn-primary">
      Авторизоваться через ВКонтакте
    </a>
    """.format(link=f"https://oauth.vk.com/authorize?client_id={CLIENT_ID}&scope=email&redirect_uri={REDIRECT_URI}&response_type=code")
    return HTMLResponse(content=html)


@app.get("/auth/vk/callback", response_class=HTMLResponse)
async def vk_callback(code: str):
    """Обработчик Callback URL после авторизации"""
    # Меняем authorization_code на access_token
    response = requests.post(
        "https://oauth.vk.com/access_token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": "XgNXMD3PY0QvjLEMBfYB",  # Ваш секретный ключ
            "redirect_uri": REDIRECT_URI,
            "code": code
        }
    )
    token_data = response.json()
    access_token = token_data["access_token"]
    vk_user_id = token_data["user_id"]  # VK_ID пользователя

    # Формируем итоговую страницу с результатом
    result_html = f"<h1>Ваш VK_ID: {vk_user_id}</h1>"
    return HTMLResponse(content=result_html)


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


@app.post("/user-wall/{user_id}")
async def get_user_wall(user_id: int):
    response = RedirectResponse(url=f"/user-wall/{user_id}", status_code=302)
    return response


def group_by_date(data) -> dict:
    posts_grouped_by_date = dict()

    for post in data['response']['items']:
        timestamp = post['date']
        dt_object = datetime.fromtimestamp(timestamp)

        date_string = dt_object.strftime("%d.%m.%Y")
        if date_string not in posts_grouped_by_date.keys():
            posts_grouped_by_date[date_string] = [post]
        else:
            posts_grouped_by_date[date_string].append(post)

    return posts_grouped_by_date


@app.get("/user-wall/{user_id}", tags=["Стена"], response_class=HTMLResponse)
async def get_user_wall_info(user_id: int):
    params = {
        "access_token": VK_SERVICE_KEY,
        "domain": user_id,
        "v":"5.199",
        "extended": 1
    }
    response = get("https://api.vk.com/method/wall.get", params=params).json()
    response = group_by_date(response)

    dates = list(response.keys())
    counts = [len(response[d]) for d in dates]

    # Создаем график с помощью Bokeh
    p = figure(x_range=dates, width=1000, height=350, title="Количество постов по дням")
    p.vbar(x=dates, top=counts, width=0.9)
    p.xaxis.axis_label = "Даты"
    p.yaxis.axis_label = "Количество постов"

    # Генерируем компоненты для вставки в HTML
    script, div = components(p)
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Диаграмма постов по дням</title>
        <!-- Загружаем ресурсы Bokeh -->
        {CDN.render()}
    </head>
    <body>
        <h1>График количества постов по дням</h1>
        {div}
        {script}
    </body>
    </html>
    """
    return HTMLResponse(content=html)

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


@app.get("/user-base-info/{user_id}")
async def get_user_info(user_id: int):
    params = {
        "access_token": VK_SERVICE_KEY,
        "user_ids": user_id,
        "v": "5.199"
    }

    return get("https://api.vk.com/method/users.get", params=params).json()


async def get_user_friends_info(parameters):
    return get("https://api.vk.com/method/friends.get", params=parameters).json()


@app.get("/user-friends/{user_id}")
async def get_user_info(user_id: int) -> dict:
    friends_params = {
        "access_token": VK_SERVICE_KEY,
        "user_id": user_id,
        "v": "5.199",
        # "count": 10 # временный параметр
    }

    friends_ids = get("https://api.vk.com/method/friends.get", params=friends_params).json()

    print(friends_ids)
    data = dict()
    for id in friends_ids["response"]["items"]:
        user_params = {
            "access_token": VK_SERVICE_KEY,
            "user_ids": id,
            "v": "5.199",
        }
        user_info = get("https://api.vk.com/method/users.get", params=user_params).json()
        time.sleep(0.3)

        # tmp_user_info = user_info["response"][0]
        # del tmp_user_info["id"]
        # del tmp_user_info["can_access_closed"]
        # del tmp_user_info["is_closed"]

        tmp_user_info = user_info["response"][0]
        data[id] = {"first_name": tmp_user_info["first_name"], "last_name": tmp_user_info["last_name"]}
        # data[id] = tmp_user_info
        get_friend_graph(user_id)

    return data


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
