import redis
import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

def _connect_redis():
    """Try real Redis first; fall back to fakeredis for local dev."""
    try:
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        client.ping()
        logger.info("Connected to Redis at %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
        return client
    except (redis.ConnectionError, redis.TimeoutError, ConnectionRefusedError, OSError):
        try:
            import fakeredis
            logger.warning(
                "⚠ Real Redis unavailable — using fakeredis (in-memory). "
                "Data will NOT persist across restarts."
            )
            return fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            logger.error(
                "Redis not reachable and fakeredis not installed. "
                "Install fakeredis (`pip install fakeredis`) or start Redis."
            )
            raise

redis_client = _connect_redis()

def get_json(key: str) -> Optional[Dict[str, Any]]:
    """Fetch and decode JSON from Redis."""
    data = redis_client.get(key)
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None

def set_json(key: str, value: Dict[str, Any], ttl_s: Optional[int] = None) -> None:
    """Encode JSON and store in Redis."""
    encoded_value = json.dumps(value)
    redis_client.set(key, encoded_value, ex=ttl_s)
