-- Get involved keys
local ip_key = KEYS[1]

-- Embedded configuration parameters
local total_key = "{{TOTAL_KEY}}"
local per_ip_limit = {{PER_IP_LIMIT}}
local total_limit = {{TOTAL_LIMIT}}
local limit_interval = {{LIMIT_INTERVAL}}

-- Check per-IP limit
if tonumber(redis.call("GET", ip_key) or 0) >= per_ip_limit then
    return {0, "ip", redis.call("TTL", ip_key)} -- Return deny message
end

-- Check global limit
if tonumber(redis.call("GET", total_key) or 0) >= total_limit then
    return {0, "global", redis.call("TTL", total_key)} -- Return deny message
end

-- Increment counts and set expiration
if redis.call("INCR", total_key) == 1 then redis.call("EXPIRE", total_key, limit_interval) end
if redis.call("INCR", ip_key) == 1 then redis.call("EXPIRE", ip_key, limit_interval) end

-- Return allow message
return {1, nil, nil}