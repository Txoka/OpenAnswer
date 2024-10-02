# TODO List

## Backend
- [ ] **Implement Redis-based rate limiting**
  Integrate Redis for controlling the rate at which users can access the API. This should be based on an asynchronous Redis client to ensure non-blocking operations.

- [ ] **Add rate limit API responses**
  Ensure proper responses (e.g., `429 Too Many Requests`) are returned when rate limits are exceeded. Include details such as retry times to guide users on when they can attempt another request.

## Frontend
- [ ] **Add frontend messages for rate limiting**
  Display clear and concise error messages on the frontend when users hit the rate limit. Messages should include retry timing information for a better user experience.