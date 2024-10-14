import redis.asyncio as aioredis
import base64
import mmh3
from ipaddress import ip_address, AddressValueError
from jinja2 import Template

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

        self.script_content = self._load_and_format_lua_script("./lua_scripts/rate_limiter.lua")
        self.script = self.redis.register_script(self.script_content)

    def _load_and_format_lua_script(self, lua_script_path: str) -> str:
        """
        Loads the Lua script from the given path and replaces placeholders with actual configuration values using str.format().
        """
        try:
            with open(lua_script_path, 'r') as file:
                script = file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Lua script not found at path: {lua_script_path}")

        # Replace placeholders with actual configuration values using str.format()
        template = Template(script)
        script = template.render(
            PER_IP_LIMIT=100,
            TOTAL_LIMIT=1000,
            LIMIT_INTERVAL=60
        )

        print(script)

        return script
    
    def _validate_and_encode_ip(self, ip: str) -> bytes:
        """
        Validates and encodes the IP address to bytes.
        """
        try:
            ip_obj = ip_address(ip)
            return ip_obj.packed
        except AddressValueError:
            raise ValueError(f"Invalid IP address format: {ip}")

    def _hash_ip(self, ip: str) -> str:
        """
        Hashes (or not) the byte-encoded IP with a secret salt and returns a base64-encoded string.
        """
        if not self.obfuscate_ips:
            return ip
        
        hash_input = self.salt + self._validate_and_encode_ip(ip)
        full_hash = mmh3.hash_bytes(hash_input, 42)
        truncated_hash = full_hash[:9]
        return base64.urlsafe_b64encode(truncated_hash).decode('utf-8')

    async def check_limits(self, ip: str):
        """
        Checks and updates the rate limits for a given IP address.

        Returns:
            dict: {
                "allowed": bool,
                "exceeded": str or None,
                "retry_after": int or None
            }
        """
        try:
            # Validate and encode the IP address
            ip_bytes = self._validate_and_encode_ip(ip)
            # Hash the IP address
            hashed_ip = self._hash_ip(ip_bytes)
            ip_key = f"{self.ip_key_prefix}{hashed_ip}"

            # Execute the Lua script atomically
            result = await self.rate_limit_script(
                keys=[ip_key, self.total_key]
            )

            allowed = bool(result[0])
            exceeded = result[1]
            retry_after = result[2]

            return {
                "allowed": allowed,
                "exceeded": exceeded,
                "retry_after": retry_after
            }

        except Exception as e:
            return {
                "allowed": False,
                "exceeded": "ERROR",
                "retry_after": None
            }