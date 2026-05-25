from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import chat, health, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Redis connection pool
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    # Persistent httpx client for Presidio (reused across requests)
    app.state.presidio_client = httpx.AsyncClient(
        base_url=settings.presidio_url,
        timeout=10.0,
    )

    yield

    await app.state.redis.aclose()
    await app.state.presidio_client.aclose()


app = FastAPI(title="Chatbot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)
