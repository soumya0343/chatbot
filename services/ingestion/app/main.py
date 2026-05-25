import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Ingestion service starting — consumer loop will start in Stage 4")
    yield
    logger.info("Ingestion service shutting down")


app = FastAPI(title="Ingestion Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ingestion"}
