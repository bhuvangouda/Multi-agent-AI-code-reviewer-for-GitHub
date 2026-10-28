import asyncio
import json
import hmac
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.main import app
from app.github.webhook import verify_signature
from app.workers.review_task import enqueue_review, process_review
from app.models.webhook_delivery import WebhookDelivery
from app.models.review_run import ReviewRun, Finding
from app.database import AsyncSessionLocal, get_db, Base, engine
from app.core.config import settings

# ----------------------------------------------------------------------
# Helper – dummy Redis queue that records enqueue calls
# ----------------------------------------------------------------------
class DummyQueue:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, func, *args, **kwargs):
        # Record the call and return a simple object mimicking an RQ Job
        self.enqueued.append((func, args, kwargs))
        job = MagicMock()
        job.func = func
        job.args = args
        job.kwargs = kwargs
        job.id = "dummy-job-id"
        return job

# ----------------------------------------------------------------------
# Fresh DB fixture (same as other tests)
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

# ----------------------------------------------------------------------
# 1️⃣  When Redis is *available* the webhook should enqueue a job
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_webhook_enqueues_job_when_redis_available():
    dummy_queue = DummyQueue()

    # Patch the Redis helper to return an object with a Queue attribute
    with patch("app.core.redis.get_redis_connection", return_value=MagicMock()), \
         patch("app.workers.review_task.Queue", return_value=dummy_queue):
        payload = {
            "action": "opened",
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/1", "head": {"sha": "deadbeef"}},
            "repository": {"full_name": "owner/repo"},
        }
        body = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            resp = await client.post(
                "/webhook",
                content=body,
                headers={
                    "X-GitHub-Delivery": "deliv-1",
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": signature,
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "accepted"

        # Verify a job was queued for the newly created delivery ID
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WebhookDelivery).where(WebhookDelivery.delivery_id == "deliv-1")
            )
            delivery: WebhookDelivery = result.scalar_one()
            # The dummy queue should have recorded one enqueue call with the correct ID
            assert len(dummy_queue.enqueued) == 1
            func, args, kwargs = dummy_queue.enqueued[0]
            assert func.__name__ == "process_review"
            assert args == (delivery.id,)

# ----------------------------------------------------------------------
# 2️⃣  Fallback path – when Redis is unavailable the job runs synchronously
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fallback_runs_process_review_synchronously():
    # Force get_redis_connection to raise, causing _get_queue() to return None
    with patch("app.core.redis.get_redis_connection", side_effect=Exception("Redis down")):
        payload = {
            "action": "opened",
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/2", "head": {"sha": "feedface"}},
            "repository": {"full_name": "owner/repo"},
        }
        body = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            resp = await client.post(
                "/webhook",
                content=body,
                headers={
                    "X-GitHub-Delivery": "deliv-2",
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": signature,
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "accepted"

        # The review should have been processed immediately – check DB
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ReviewRun).join(WebhookDelivery).where(WebhookDelivery.delivery_id == "deliv-2")
            )
            review: ReviewRun = result.scalar_one()
            assert review.status == "completed"
            assert len(review.findings) > 0

# ----------------------------------------------------------------------
# 3️⃣  Verify that process_review persists a ReviewRun and Findings correctly
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_process_review_persists_review_and_findings():
    # Create a webhook delivery directly
    async with AsyncSessionLocal() as db:
        delivery = WebhookDelivery(
            delivery_id="direct-1",
            event="pull_request",
            payload={"action": "opened", "pull_request": {"url": "url", "head": {"sha": "sha"}}},
            processed=False,
            received_at=datetime.utcnow(),
        )
        db.add(delivery)
        await db.commit()
        await db.refresh(delivery)
        delivery_id = delivery.id

    # Run the processing function (synchronous path)
    await process_review(delivery_id)

    async with AsyncSessionLocal() as db:
        review = await db.get(ReviewRun, 1)
        assert review is not None
        assert review.webhook_delivery_id == delivery_id
        assert review.status == "completed"
        assert len(review.findings) > 0
        # Spot‑check a finding field
        f = review.findings[0]
        assert f.file_path.endswith("example.py")
        assert f.severity in {"low", "medium", "high"}

# ----------------------------------------------------------------------
# 4️⃣  Job failure handling – if the orchestrator raises, the job propagates
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_process_review_exception_propagates():
    # Create a delivery
    async with AsyncSessionLocal() as db:
        delivery = WebhookDelivery(
            delivery_id="fail-1",
            event="pull_request",
            payload={"action": "opened", "pull_request": {"url": "url", "head": {"sha": "sha"}}},
            processed=False,
            received_at=datetime.utcnow(),
        )
        db.add(delivery)
        await db.commit()
        await db.refresh(delivery)
        delivery_id = delivery.id

    # Patch the orchestrator to raise an exception
    with patch("app.workers.review_task.Orchestrator.review", side_effect=Exception("Orchestrator crash")):
        with pytest.raises(Exception) as exc:
            await process_review(delivery_id)
        assert "Orchestrator crash" in str(exc.value)
