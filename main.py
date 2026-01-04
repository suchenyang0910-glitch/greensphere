from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from db import init_db
from routes import router

app = FastAPI()

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(router)
