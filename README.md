# TODO List

## Backend
- [ ] **Implement Redis-based rate limiting**  
  Integrate Redis into the FastAPI backend to enforce rate limiting using `AIORedis` for async operations. This will help prevent overloading the API with too many requests in a short time.

- [ ] **Add rate limit API responses**  
  Ensure that appropriate HTTP responses (e.g., `429 Too Many Requests`) are sent when the rate limit is exceeded. The response should include details about when the user can try again (e.g., retry after X seconds).

## Frontend
- [ ] **Add frontend messages for rate limiting**  
  Display user-friendly error messages on the frontend when the API rate limit is hit. Messages should explain the reason for the block and how long the user should wait before retrying.

---

### Notes:
- The rate limiting feature will improve performance and protect the backend from abuse.
- The Redis setup should be properly documented for local and production environments.
