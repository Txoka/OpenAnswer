-- Get involved keys
local ip_key = KEYS[1]

-- Embedded configuration parameters
local total_key = "{{TOTAL_KEY}}"
local per_ip_limit = {{PER_IP_LIMIT}}
local total_limit = {{TOTAL_LIMIT}}
local limit_interval = {{LIMIT_INTERVAL}}

-- Check per-IP limit
local current_ip = tonumber(redis.call("GET", ip_key))
if current_ip >= per_ip_limit then
    local ttl = redis.call("TTL", ip_key)
    return {0, "ip", ttl} -- Return deny message
end

-- Check global limit
local current_total = tonumber(redis.call("GET", total_key))
if current_total >= total_limit then
    local ttl = redis.call("TTL", total_key)
    return {0, "global", ttl} -- Return deny message
end

-- Increment counts and set expiration
if redis.call("INCR", total_key) == 1 then redis.call("EXPIRE", total_key, ttl) end
if redis.call("INCR", ip_key) == 1 then redis.call("EXPIRE", ip_key, ttl) end

-- Return allow message
return {1, nil, nil}