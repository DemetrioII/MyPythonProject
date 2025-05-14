from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import requests
from dotenv import load_dotenv

# Настройки ВКонтакте
CLIENT_ID = load_dotenv("CLIENT_ID")
REDIRECT_URI = "https://brown-kiwis-relax.loca.lt/"
VK_API_VERSION = "5.131"
CLIENT_SECRET_KEY = load_dotenv("CLIENT_SECRET")

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def index():
    """Главная страница с кнопкой авторизации"""
    html = """
    <h1>Авторизация через ВКонтакте</h1>
    <a href="{link}" class="btn btn-primary">
      Авторизоваться через ВКонтакте
    </a>
    """.format(
        link=f"https://oauth.vk.com/authorize?client_id={CLIENT_ID}&scope=email&redirect_uri={REDIRECT_URI}&response_type=code")
    return HTMLResponse(content=html)


@app.get("/auth/vk/callback", response_class=HTMLResponse)
async def vk_callback(code: str):
    """Обработчик Callback URL после авторизации"""
    # Меняем authorization_code на access_token
    response = requests.post(
        "https://oauth.vk.com/access_token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET_KEY,  # Ваш секретный ключ
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
