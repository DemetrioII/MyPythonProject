from fastapi import FastAPI, Request, Form
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
async def post_root(login: str = Form(None), password: str = Form(None)):
    try:
        hash_from_db = db.get_password_by_name(name=login)
        if hash_from_db == password_hash(password):
            return f"Success"
        return f"Wrong Password"
    except Exception as e:
        return f"{str(e)}"

# db.close()
