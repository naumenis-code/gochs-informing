#!/usr/bin/env python3
"""
ГО-ЧС Информирование - Главный модуль FastAPI приложения
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск ГО-ЧС Информирование...")
    try:
        from app.core.redis_client import redis_client
        await redis_client.connect()
        logger.info("Redis подключен")
    except Exception as e:
        logger.warning(f"Redis недоступен: {e}")
    yield
    logger.info("Завершение работы")


app = FastAPI(
    title="ГО-ЧС Информирование",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy", "database": True, "redis": True, "asterisk": True}


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": "1.0.0", "status": "running"}
