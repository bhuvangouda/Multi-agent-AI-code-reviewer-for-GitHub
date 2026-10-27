import json
import asyncio
from datetime import datetime
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.webhook_delivery import WebhookDelivery
from app.core.redis import get_redis_connection
from rq import Queue, SimpleWorker

# Lazy queue creation function
def _get_queue():
    try:
        conn = get_redis_connection()
        return Queue('reviews', connection=conn)
    except Exception:
        # Redis unavailable; return None to indicate fallback mode
        return None


def enqueue_review(delivery_id: int) -> None:
    """Enqueue a background job to process a webhook delivery.
    If Redis/RQ is unavailable, process synchronously.
    """
    q = _get_queue()
    if q is None:
        # Fallback: process immediately
        process_review(delivery_id)
    else:
        q.enqueue(process_review, delivery_id)


def process_review(delivery_id: int) -> None:
    """Background worker entry point.
    Fetch the webhook payload, mark it as processed, and (later) run the review pipeline.
    """
    async def _run():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
            )
            delivery = result.scalar_one_or_none()
            if not delivery:
                return
            # Placeholder: future orchestrator call goes here
            delivery.processed = True
            delivery.processed_at = datetime.utcnow()
            session.add(delivery)
            await session.commit()
    asyncio.run(_run())
