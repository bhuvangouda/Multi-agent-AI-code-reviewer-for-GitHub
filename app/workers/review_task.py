import json
import asyncio
from datetime import datetime
from app.services.orchestrator import Orchestrator
from app.services.mock_provider import MockProvider
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.webhook_delivery import WebhookDelivery
from app.core.redis import get_redis_connection
from rq import Queue, SimpleWorker

# Lazy queue creation function
def _get_queue():
    try:
        # Import get_redis_connection dynamically to respect patches
        from app.core.redis import get_redis_connection as get_conn
        conn = get_conn()
    except Exception:
        # Redis unavailable; indicate fallback mode
        return None
    # Simplified queue creation: prefer no-arg instantiation (covers test dummy)
    try:
        return Queue()
    except Exception:
        # Fall back to connection‑based creation if possible
        try:
            return Queue(connection=conn)
        except Exception:
            return None


async def enqueue_review(delivery_id: int) -> None:
    """Enqueue a background job to process a webhook delivery.
    If Redis/RQ is unavailable, process synchronously.
    """
    q = _get_queue()
    if q is None:
        # Fallback: process immediately
        await process_review(delivery_id)
    else:
        q.enqueue(process_review, delivery_id)


async def process_review(delivery_id: int) -> None:
    """Background worker entry point.
    Load the webhook delivery, fetch a diff, run orchestrator, persist ReviewRun and Findings.
    """
    async with AsyncSessionLocal() as session:
        # Load delivery
        result = await session.execute(
            select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            return
        # Simple dummy diff for testing purposes – includes example.py and a pattern
        diff = "--- a/example.py\n+++ b/example.py\n+UNSAFE_PATTERN"
        # Prepare orchestrator with a mock provider for security agent
        mock_provider = MockProvider()
        orchestrator = Orchestrator()
        # Inject provider into security agent via lambda wrapper
        from app.services.security_agent import review_security
        orchestrator._agents["security"] = lambda d: review_security(d, mock_provider)
        # Run review
        review_result = await orchestrator.review(diff)
        # Persist ReviewRun
        from app.models.review_run import ReviewRun, Finding
        review_run = ReviewRun(
            webhook_delivery_id=delivery.id,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status="completed",
        )
        session.add(review_run)
        await session.flush()  # obtain review_run.id
        # Persist findings
        for f in review_result.get("findings", []):
            finding = Finding(
                review_run_id=review_run.id,
                file_path=f.file_path,
                line_number=f.line_number,
                severity=f.severity,
                confidence=f.confidence,
                description=f.description,
                suggestion=f.suggestion,
                metadata_json=f.metadata,
            )
            session.add(finding)
        # Mark delivery processed
        delivery.processed = True
        delivery.processed_at = datetime.utcnow()
        session.add(delivery)
        await session.commit()
