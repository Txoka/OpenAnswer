import redis.asyncio as aioredis
import base64
import mmh3
from ipaddress import ip_address, AddressValueError

class RateLimiter:
    def __init__(
        self,
        redis_client: aioredis.Redis,
        per_ip_limit: int,
        total_limit: int,
        limit_interval: int,  # in seconds
        obfuscate_ips: bool,
        salt: str,
    ):
        self.redis = redis_client
        self.per_ip_limit = per_ip_limit
        self.total_limit = total_limit
        self.limit_interval = limit_interval
        self.total_key = "global"
        self.ip_key_prefix = "ip:"
        self.obfuscate_ips = obfuscate_ips
        self.salt = base64.b64decode(salt)
    
    def _validate_and_encode_ip(self, ip: str) -> bytes:
        """
        Validates and encodes the IP address to bytes.
        """
        try:
            ip_obj = ip_address(ip)
            return ip_obj.packed  # Returns the binary representation
        except AddressValueError:
            raise ValueError(f"Invalid IP address format: {ip}")

    def _hash_ip(self, ip: str) -> str:
        """
        Hashes (or not) the byte-encoded IP with a secret salt and returns a base64-encoded string.
        """
        if not self.obfuscate_ips:
            return ip
        
        # Concatenate salt and IP bytes
        hash_input = self.salt + self._validate_and_encode_ip(ip)
        # Generate 128-bit MurmurHash3
        full_hash = mmh3.hash_bytes(hash_input, 42)  # seed=42
        # Truncate to 80 bits (10 bytes)
        truncated_hash = full_hash[:9]
        # Encode to base64 for Redis key compatibility
        return base64.urlsafe_b64encode(truncated_hash).decode('utf-8')

    async def check_limits(self, ip: str) -> dict:
        ip_key = f"{self.ip_key_prefix}{self._hash_ip(ip)}"
        """
        Checks and updates the rate limits for a given IP address.

        Returns:
            dict: {
                "allowed": bool,
                "exceeded": str or None,
                "retry_after": int or None
            }
        """

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