import asyncio
import logging
import os

from redis.exceptions import ResponseError

from .config import settings
from .extractor import enrich
from .pii_client import PresidioClient
from .validator import parse_event
from .writer import write_batch

logger = logging.getLogger(__name__)

STREAM_KEY = settings.redis_stream_key
GROUP = settings.redis_consumer_group
BATCH = settings.batch_size
BLOCK_MS = settings.batch_timeout_ms
CONSUMER_NAME = f"worker-{os.getpid()}"
PEL_MIN_IDLE_MS = 60_000  # reclaim messages pending > 60s


async def _ensure_group(redis) -> None:
    try:
        await redis.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
        logger.info(f"Consumer group '{GROUP}' created on stream '{STREAM_KEY}'")
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def _process_batch(
    messages: list[tuple[str, dict]],
    pii: PresidioClient,
    redis,
) -> None:
    """Validate → enrich → write → ACK. Bad messages are ACK'd immediately."""
    good_rows: list[dict] = []
    bad_ids: list[str] = []
    good_ids: list[str] = []

    for msg_id, fields in messages:
        event = parse_event(msg_id, fields)
        if event is None:
            bad_ids.append(msg_id)
            continue
        try:
            row = await enrich(event, pii)
            good_rows.append(row)
            good_ids.append(msg_id)
        except Exception as e:
            logger.error(f"Enrichment failed for {msg_id}: {e}")
            bad_ids.append(msg_id)

    # ACK bad messages immediately — they can't be fixed by retry
    if bad_ids:
        await redis.xack(STREAM_KEY, GROUP, *bad_ids)
        logger.warning(f"ACK'd {len(bad_ids)} unparseable messages")

    if good_rows:
        await write_batch(good_rows)
        await redis.xack(STREAM_KEY, GROUP, *good_ids)
        logger.info(f"Ingested {len(good_rows)} inference events")


async def run_consumer(redis, pii: PresidioClient) -> None:
    """Main consumer loop. Runs indefinitely until cancelled."""
    await _ensure_group(redis)
    logger.info(f"Consumer '{CONSUMER_NAME}' started — stream={STREAM_KEY} group={GROUP}")

    while True:
        try:
            # 1. Claim pending messages from crashed consumers (PEL)
            try:
                claimed = await redis.xautoclaim(
                    STREAM_KEY,
                    GROUP,
                    CONSUMER_NAME,
                    min_idle_time=PEL_MIN_IDLE_MS,
                    start_id="0-0",
                    count=BATCH,
                )
                # xautoclaim returns (next_start_id, messages, deleted_ids)
                pending_msgs = claimed[1] if claimed and len(claimed) > 1 else []
                if pending_msgs:
                    logger.info(f"Reclaimed {len(pending_msgs)} pending messages from PEL")
                    await _process_batch(pending_msgs, pii, redis)
            except Exception as e:
                # xautoclaim not available in Redis < 7 — log and continue
                logger.debug(f"XAUTOCLAIM skipped: {e}")

            # 2. Read new messages
            result = await redis.xreadgroup(
                groupname=GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: ">"},
                count=BATCH,
                block=BLOCK_MS,
            )

            if not result:
                continue  # timeout — no new messages, loop again

            for _stream, messages in result:
                await _process_batch(messages, pii, redis)

        except asyncio.CancelledError:
            logger.info("Consumer cancelled — shutting down")
            break
        except Exception as e:
            logger.error(f"Consumer loop error: {e}", exc_info=True)
            await asyncio.sleep(1)  # back off before retry
