import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import chat, dashboard, health, sessions

logger = logging.getLogger(__name__)


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

    # Optionally run the ingestion consumer in-process (single-service deploys,
    # e.g. Render free tier where a separate background worker isn't available).
    app.state.consumer_task = None
    app.state.consumer_pii = None
    if settings.enable_inline_ingestion:
        from ingestion_app.consumer import run_consumer
        from ingestion_app.pii_client import PresidioClient

        app.state.consumer_pii = PresidioClient(settings.presidio_url)
        app.state.consumer_task = asyncio.create_task(
            run_consumer(app.state.redis, app.state.consumer_pii)
        )
        logger.info("Inline ingestion consumer started")

    yield

    if app.state.consumer_task is not None:
        app.state.consumer_task.cancel()
        try:
            await app.state.consumer_task
        except asyncio.CancelledError:
            pass
        await app.state.consumer_pii.aclose()
    await app.state.redis.aclose()
    await app.state.presidio_client.aclose()


app = FastAPI(title="InferLog API", version="0.1.0", lifespan=lifespan)

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
app.include_router(dashboard.router)
