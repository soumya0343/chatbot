import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from .config import settings
from .consumer import run_consumer
from .pii_client import PresidioClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    pii = PresidioClient(settings.presidio_url)

    # Start consumer loop as background task
    task = asyncio.create_task(run_consumer(redis_client, pii))
    logger.info("Ingestion consumer started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    await pii.aclose()
    await redis_client.aclose()
    logger.info("Ingestion consumer stopped")


app = FastAPI(title="Ingestion Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ingestion"}
