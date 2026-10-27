import os
import redis
from app.core.config import settings

def get_redis_connection() -> redis.Redis:
    """Return a Redis client based on REDIS_URL.
    If Redis is unavailable, return a lightweight in-memory mock.
    """
    try:
        return redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        class _MockRedis:
            def __init__(self):
                self.connection = None
        return _MockRedis()
