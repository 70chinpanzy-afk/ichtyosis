"""FastAPIアプリケーション"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ichthyosis_curator.config import load_config
from ichthyosis_curator.db import init_db
from ichthyosis_curator.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    init_db(config.db_path)
    app.state.config = config
    yield


app = FastAPI(
    title="魚鱗癬紅皮症 ニュースキュレーター API",
    description="魚鱗癬紅皮症に関する最新医学情報を毎日キュレーションするAPI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
