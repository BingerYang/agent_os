from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./dev.db"
    secret_key: str = "dev-secret-key-change-in-production"
    llm_encryption_key: str = ""
    debug: bool = True
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    redis_url: str = "redis://localhost:6379/0"
    redis_address: str = "localhost:6379"
    redis_db: str = 0
    redis_is_cluster: bool = False
    redis_stream_key: str = "agent:publish"
    runtime_agent_load_mode: str = "eager"  # eager | lazy
    runtime_agent_pool_max_size: int = 100

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    def load_redis_client(self):
        if self.redis_is_cluster:
            from redis.asyncio import RedisCluster
            from redis.asyncio.cluster import ClusterNode
            client = RedisCluster(
                startup_nodes=[ClusterNode(*addr.split(":")) for addr in self.redis_address.split(",")],
                decode_responses=True,
                encoding="utf8",
                max_connections=50,
            )

            return client
        else:
            import redis.asyncio as aioredis

            return aioredis.from_url(f"redis://{self.redis_address}/{self.redis_db}", decode_responses=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
