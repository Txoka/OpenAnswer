# TODO List

## Backend
- [x] **Implement Redis-based rate limiting**
  Integrate Redis for controlling the rate at which users can access the API. This should be based on an asynchronous Redis client to ensure non-blocking operations.

- [x] **Add rate limit API responses**
  Ensure proper responses (e.g., `429 Too Many Requests`) are returned when rate limits are exceeded. Include details such as retry times to guide users on when they can attempt another request.

- [ ] **Develop a function based approach**
  Provide llm with functions for performing multiple parallel web searches and then multiple parallel data extraction jobs using other llm call as currently implemented.
  Feed the raw google search results by query and markdown extracted data snippets to the model and give it freedom to retry searches and extractions if necesary.
  Implement data extraction llm directly on crawler according to crawl4ai documentation.
  Implement as another api call, /api/answer-pro.

## Frontend
- [x] **Add frontend messages for rate limiting**
  Display clear and concise error messages on the frontend when users hit the rate limit. Messages should include retry timing information for a better user experience.

- [ ] **Dynamic streaming based frontend**
  Make it fancy, show in real time what model is doing and what webs its crawling and stuff. Pretty self explanatory.