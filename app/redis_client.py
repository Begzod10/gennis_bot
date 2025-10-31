import os
import redis
from dotenv import load_dotenv

load_dotenv()

redis_pool = redis.ConnectionPool(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB_BOT", 0)),
    decode_responses=True
)

redis_client = redis.Redis(connection_pool=redis_pool)