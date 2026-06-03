import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# Ładowanie pliku .env na starcie aplikacji
load_dotenv()

app = FastAPI(title="StegChat")

# Sprawdzamy czy foldery istnieją, żeby FastAPI nie zgłosiło błędu przy starcie
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/templates", exist_ok=True)

# Podpinamy pliki statyczne i szablony Jinja2
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def read_chat(request: Request):
    # Renderujemy plik chat.html
    return templates.TemplateResponse("chat.html", {"request": request})