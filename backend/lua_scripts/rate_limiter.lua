local total_key = KEYS[1]
local ip_key = KEYS[2]

-- Embedded configuration parameters
local per_ip_limit = {{PER_IP_LIMIT}}
local total_limit = {{TOTAL_LIMIT}}
local limit_interval = {{LIMIT_INTERVAL}}

-- Initialize requests
redis.call("SET", ip_key, 0, "NX", "EX", limit_interval)
redis.call("SET", total_key, 0, "NX", "EX", limit_interval)


-- Check per-IP limit
local current_ip = tonumber(redis.call("GET", ip_key))
if current_ip >= per_ip_limit then
    local ttl = redis.call("TTL", ip_key)
    return {0, "ip", ttl}
end

-- Check global limit
local current_total = tonumber(redis.call("GET", total_key))
if current_total >= total_limit then
    local ttl = redis.call("TTL", total_key)
    return {0, "global", ttl}
end

-- Increment counts
redis.call("INCR", total_key)
redis.call("INCR", ip_key)

return {1, "none", 0}