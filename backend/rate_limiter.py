import redis.asyncio as aioredis
import base64
import mmh3
from ipaddress import ip_address, AddressValueError
from jinja2 import Template
import traceback

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
            TOTAL_KEY=self.total_key,
            PER_IP_LIMIT=self.per_ip_limit,
            TOTAL_LIMIT=self.total_limit,
            LIMIT_INTERVAL=self.limit_interval
        )

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
        hash = mmh3.hash_bytes(hash_input, 42)[:9]
        return base64.urlsafe_b64encode(hash).decode('utf-8')

    async def _run_script(self, ip_key):
        result = await self.script(
            keys=[ip_key]
        )
        print(len(result))

        allowed = bool(result[0])
        exceeded = result[1] if len(result) > 1 else None
        retry_after = result[2] if len(result) > 2 else None
        
        return allowed, exceeded, retry_after

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
            allowed, exceeded, retry_after = await self._run_script(ip_key)

            return {
                "allowed": allowed,
                "exceeded": exceeded,
                "retry_after": retry_after
            }

        except ValueError as ve:
            print(f"An error occurred: {ve}")
            traceback.print_exc()
            
            return {
                "allowed": False,
                "exceeded": "INVALID IP ERROR",
                "retry_after": None
            }
        except aioredis.RedisError as re:
            print(f"An error occurred: {re}")
            traceback.print_exc()

            return {
                "allowed": False,
                "exceeded": "REDIS ERROR",
                "retry_after": None
            }
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()

            return {
                "allowed": False,
                "exceeded": "UNKNOWN ERROR",
                "retry_after": None
            }