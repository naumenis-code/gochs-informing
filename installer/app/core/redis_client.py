import redis.asyncio as redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.client = None

    async def connect(self):
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def disconnect(self):
        if self.client:
            await self.client.close()

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def set(self, key: str, value: str, expire: int = None):
        await self.client.set(key, value, ex=expire)

    async def get(self, key: str) -> str:
        return await self.client.get(key)

    async def delete(self, key: str):
        await self.client.delete(key)


redis_client = RedisClient()
