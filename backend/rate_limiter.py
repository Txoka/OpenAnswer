import redis.asyncio as aioredis

class RateLimiter:
    def __init__(
        self,
        redis_client: aioredis.Redis,
        per_ip_limit: int,
        total_limit: int,
        limit_interval: int  # in seconds
    ):
        self.redis = redis_client
        self.per_ip_limit = per_ip_limit
        self.total_limit = total_limit
        self.limit_interval = limit_interval
        self.total_key = "total-requests"
        self.ip_key_prefix = "ip-requests:"

    async def check_limits(self, ip: str):
        ip_key = f"{self.ip_key_prefix}{ip}"

        # Check current request counts without incrementing
        pipeline = self.redis.pipeline()

        pipeline.get(self.total_key)
        pipeline.ttl(self.total_key)

        pipeline.get(ip_key)
        pipeline.ttl(ip_key)

        results = await pipeline.execute()
        total_requests = int(results[0] or 0)
        total_ttl = results[1]
        ip_requests = int(results[2] or 0)
        ip_ttl = results[3]

        exceeded_limits = []
        retry_times = []

        if total_requests >= self.total_limit:
            exceeded_limits.append("global")
            retry_times.append(total_ttl)

        if ip_requests >= self.per_ip_limit:
            exceeded_limits.append("ip")
            retry_times.append(ip_ttl)

        if exceeded_limits:
            max_retry = max(retry_times)
            exceeded = exceeded_limits[retry_times.index(max_retry)]
            return {
                "allowed": False,
                "exceeded": exceeded,
                "retry_after": max_retry
            }

        # Increment only if limits are not exceeded
        pipeline = self.redis.pipeline()
        
        pipeline.set(self.total_key, 0, ex=self.limit_interval, nx=True)
        pipeline.set(ip_key, 0, ex=self.limit_interval, nx=True)
        
        pipeline.incr(self.total_key)
        pipeline.incr(ip_key)

        # Execute the increments
        await pipeline.execute()

        return {
            "allowed": True,
            "exceeded": None,
            "retry_after": None
        }