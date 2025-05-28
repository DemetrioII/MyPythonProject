import base64
import datetime
import json
import asyncio
from collections import Counter
import plotly.express as px
import httpx
import pandas as pd
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
from fastapi import Query
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
from VkRequest import *

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

tasks = []

db = Database()


def get_metrics():
    metrics = dict()
    with open("data.json", "r") as fi:
        raw_data = fi.read()
    data = json.loads(raw_data)
    for key, info in data.items():
        if key == "base_info":
            relationship_status = {
                0: "не указано",
                1: "не женат/не замужем",
                2: "есть друг/есть подруга",
                3: "помолвлен/помолвлена",
                4: "женат/замужем",
                5: "всё сложно",
                6: "в активном поиске",
                7: "влюблён/влюблена",
                8: "в гражданском браке"
            }
            sex_status = {
                1: "Ж",
                2: "М"
            }
            metrics[key] = info.copy()
            try:
                metrics[key]["relation"] = relationship_status[metrics[key]["relation"]]
            except KeyError:
                pass
            try:
                metrics[key]["sex"] = sex_status[metrics[key]["sex"]]
            except KeyError:
                pass

        elif key == "groups":
            metrics[key] = dict()
            metrics[key]["count"] = info.get("count", 0)
            items = info.get("items", [])
            for item in items:
                for tag, value in item.items():
                    if tag not in metrics[key].keys():
                        metrics[key][tag] = dict()
                    metrics[key][tag][value] = metrics[key][tag].get(value, 0) + 1

        elif key == "wall":
            metrics[key] = dict()
            items = info.get("items", [])

            metrics[key]["last_post"] = items[0].get("date", 0) if items else 0
            total_reactions = sum(item.get('reactions', 0) for item in items)
            total_views = sum(item.get('views', 0) for item in items)
            metrics[key]["social_activity"] = (total_reactions / total_views) * 100 if total_views else 0
            marked_ads = sum(item.get('marked_as_ads', 0) for item in items)
            post_count = info.get("count", 0)
            metrics[key]["post_count"] = post_count
            metrics[key]["ads_to_posts"] = marked_ads / post_count if post_count else 0

        elif key == "friends":
            metrics[key] = dict()
            items = info.get("items", [])
            allow_tags = {"city", "sex"}
            for item in items:
                for tag, value in item.items():
                    if tag in allow_tags:
                        if tag not in metrics[key].keys():
                            metrics[key][tag] = dict()
                        if tag == "city":
                            metrics[key][tag][value.get("title", "Unknown")] = metrics[key][tag].get(
                                value.get("title", "Unknown"), 0) + 1
                        elif tag == "sex":
                            metrics[key][tag][value] = metrics[key][tag].get(value, 0) + 1
        elif key == "followers":
            metrics[key] = dict()
            items = info.get("items", [])
            allow_tags = {"city", "sex"}
            for item in items:
                for tag, value in item.items():
                    if tag in allow_tags:
                        if tag not in metrics[key].keys():
                            metrics[key][tag] = dict()
                        if tag == "city":
                            metrics[key][tag][value.get("title", "Unknown")] = metrics[key][tag].get(
                                value.get("title", "Unknown"), 0) + 1
                        elif tag == "sex":
                            metrics[key][tag][value] = metrics[key][tag].get(value, 0) + 1

        return metrics


@app.post("/full-profile/")
async def get_profile_analyze(user_id: int = Form(...)):
    return RedirectResponse(url=f"/full-profile/{user_id}", status_code=303)


@app.get("/full-profile/{user_id}", tags=["Агрегированный профиль"])
async def get_full_profile(user_id: int,
                           request: Request,
                           color_posts: str = Query("Год", description="Цветовая категория", enum=["Год", "Месяц"]),
                           color_friends: str = Query("Пол", description="Цветовая категория", enum=["Пол", "Город"]),
                           chart_type: str = Query("bar", regex="^(bar|pie)$",
                                                   description="Тип графика: bar или pie"),
                           theme: str = Query("plotly", description="Тема оформления"),
                           current_user: User = Depends(get_current_active_user)):
    url = "https://api.vk.com/method/"
    token = VK_SERVICE_KEY
    version = "5.199"
    async with httpx.AsyncClient() as client:
        try:
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
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"VK API request failed: {str(e)}")

        try:
            responses = await asyncio.gather(base_info, groups, wall, friends, followers)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing VK responses: {str(e)}")
        try:
            data = {
                "base_info": responses[0].json().get("response", {}),
                "groups": responses[1].json().get("response", {}),
                "wall": responses[2].json().get("response", {}),
                "friends": responses[3].json().get("response", {}),
                "followers": responses[4].json().get("response", {})
            }

            for info, answer in data.items():
                if not answer:
                    continue
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
                if info == "followers":
                    fields_to_keep = {'id', 'deactivated', 'sex', 'first_name', 'last_name', 'can_access_closed',
                                      'is_closed', 'city'}
                    for item in data[info]['items']:
                        keys = list(item.keys())
                        for key in keys:
                            if key not in fields_to_keep:
                                del item[key]
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            json.dumps(data)
            posts = data["wall"]["items"]
            months = []
            for post in posts:
                dt = datetime.utcfromtimestamp(post["date"])
                months.append(dt.strftime("%Y-%m"))

            month_count = dict(Counter(months))
            df_month = pd.DataFrame(
                {"Месяц": month_count.keys(),
                 "Количество записей": month_count.values()}
            )

            sexes = [1, 2]
            cities = set()
            friends = data["friends"]["items"]
            for friend in friends:
                if "city" in friend.keys():
                    cities.add(friend["city"]["title"])
            cities = list(cities)
            if color_friends == "Пол":
                friends_count = dict()
                for i in friends:
                    friends_count[i["sex"]] = friends_count.get(i["sex"], 0) + 1
                df_friends = pd.DataFrame(
                    {"Пол": sexes,
                     "Количество": friends_count.values()}
                )
            else:
                friends_count = dict()
                for friend in friends:
                    if "city" in friend.keys():
                        friends_count[friend["city"]["title"]] = friends_count.get(friend["city"]["title"], 0) + 1
                df_friends = pd.DataFrame(
                    {"Город": cities,
                     "Количество": friends_count.values()}
                )

            # Добавляем год для цвета
            df_month["Год"] = df_month["Месяц"].str[:4]

            # Выбираем, как раскрашивать
            color_column = color_posts if color_posts in ["Год", "Месяц"] else "Год"
            color_for_friends = color_friends if color_friends in ["Пол", "Город"] else "Пол"
            print(color_for_friends)

            # Построение графика
            if chart_type == "bar":
                fig = px.bar(
                    df_month,
                    x="Месяц",
                    y="Количество записей",
                    color=color_column,
                    title="Активность пользователя по месяцам",
                    template=theme
                )
                fig2 = px.bar(
                    df_friends,
                    x=color_for_friends,
                    y="Количество",
                    color=color_for_friends,
                    title="Друзья",
                    template=theme
                )
            else:
                fig = px.pie(
                    df_month,
                    names="Месяц",
                    values="Количество записей",
                    color=color_column,
                    title="Активность пользователя по месяцам",
                    template=theme
                )
                fig2 = px.pie(
                    df_friends,
                    names=color_for_friends,
                    values="Количество",
                    color=color_for_friends,
                    title="Друзья",
                    template=theme
                )

            graph_html = fig.to_html(full_html=False)
            graph_2 = fig2.to_html(full_html=False)

            metrics = get_metrics()

            return templates.TemplateResponse("Graphics.html", {
                "request": request,
                "graph_html": graph_html,
                "graph2": graph_2,
                "color": color_posts,
                "chart_type": chart_type,
                "theme": theme,
                "user_id": user_id,
                "metrics": metrics
            })


        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing profile data: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def get_base_page(request: Request):
    return templates.TemplateResponse("BasePage.html", {"request": request})


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


# надо переписать
@app.get("/user-wall/{user_id}", tags=["Стена"])
async def get_user_wall_info(request: Request,
                             user_id: int,
                             color: str = Query("Год", description="Цветовая категория", enum=["Год", "Месяц"]),
                             chart_type: str = Query("bar", regex="^(bar|pie)$",
                                                     description="Тип графика: bar или pie"),
                             theme: str = Query("plotly", description="Тема оформления")
                             ):
    pass


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
