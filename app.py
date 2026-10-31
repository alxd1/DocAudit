import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from utils.templates import templates
from packages.web_app.views import router as general_router

app = FastAPI()

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(general_router)

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)