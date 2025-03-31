import base64

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from DataBase import Database
from hashlib import sha256

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

tasks = []

db = Database()


def password_hash(s: str) -> str:
    return sha256(s.encode('utf-8')).hexdigest()


@app.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def post_login_form(login: str = Form(None), password: str = Form(None)):
    try:
        hash_from_db = db.find_by_name(name=login)[1]
        if hash_from_db == password_hash(password):
            return f"Success"
        return f"Wrong Password"
    except Exception as e:
        return f"{str(e)}"


@app.get("/profile/{name}", response_class=HTMLResponse)
async def get_profile(name: str, request: Request):
    data = db.find_by_name(name=name)
    photo = base64.b64encode(data[6]).decode('utf-8')
    return templates.TemplateResponse("profile.html", {"request": request, "name": name, "register_time": data[1], "photo": photo})


@app.get("/register", response_class=HTMLResponse)
async def get_register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
async def post_register_form(login: str = Form(None), password: str = Form(None), password_repeat: str = Form(None),
                             image: UploadFile = File(None)):
    try:
        if password != password_repeat:
            return f"Passwords are different"
        if password is None:
            return f"password is none"
        image = await image.read()
        db.create_person(name=login, password=password_hash(password), image=image)
        return f"Success"
    except Exception as e:
        return f"{str(e)}"

# db.close()
