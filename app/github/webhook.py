from fastapi import APIRouter, Request, HTTPException, Depends, status
import hmac
import hashlib
import json
from app.core.config import settings
from app.workers.review_task import enqueue_review
from app.models.webhook_delivery import WebhookDelivery
from app.database import AsyncSessionLocal, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

router = APIRouter()

def verify_signature(secret: str, signature: str, payload: bytes) -> bool:
    """Validate GitHub HMAC SHA256 signature.
    GitHub sends the header ``X-Hub-Signature-256`` with value ``sha256=<hexdigest>``.
    """
    if not signature:
        return False
    try:
        sha_name, signature_hash = signature.split('=')
    except ValueError:
        return False
    if sha_name != 'sha256':
        return False
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature_hash)

@router.post("/webhook")
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    # GitHub delivery ID for deduplication
    delivery_id = request.headers.get('X-GitHub-Delivery')
    event = request.headers.get('X-GitHub-Event')
    signature = request.headers.get('X-Hub-Signature-256')
    body = await request.body()

    # Verify signature
    if not verify_signature(settings.GITHUB_WEBHOOK_SECRET, signature, body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    # Parse JSON payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # Store delivery to avoid duplicate processing
    stmt = select(WebhookDelivery).where(WebhookDelivery.delivery_id == delivery_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        # Already processed – return success silently
        return {"status": "duplicate"}

    webhook_entry = WebhookDelivery(
        delivery_id=delivery_id,
        event=event,
        payload=payload,
        processed=False,
        received_at=datetime.utcnow(),
    )
    db.add(webhook_entry)
    await db.commit()
    await db.refresh(webhook_entry)

    # Only act on pull_request events we care about
    if event == "pull_request":
        action = payload.get("action")
        if action in {"opened", "reopened", "synchronize"}:
            # Enqueue background job (fire‑and‑forget)
            enqueue_review(webhook_entry.id)

    return {"status": "accepted"}
