import os
import redis
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.StrictRedis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB_BOT', 2)),
    decode_responses=True
)