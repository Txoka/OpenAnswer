import asyncio
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web_research import WebResearcher
from llm_operations import LLMHandler
from config import config
from utils import setup_logging
import logging
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from rate_limiter import RateLimiter, aioredis

# Setup logging
log_level = getattr(logging, config.logging.log_level, logging.INFO)
setup_logging(log_file='app.log', log_level=log_level)
logger = logging.getLogger(__name__)

class ResearchAssistant:
    def __init__(self):
        self.web_researcher = WebResearcher()
        self.llm_handler = LLMHandler()
    
    async def __aenter__(self):
        await self.web_researcher.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.web_researcher.__aexit__(exc_type, exc_value, traceback)

    async def research_and_answer(self, question: str) -> dict:
        try:
            # Generate search queries
            search_terms, custom_urls = await self.llm_handler.generate_search_queries(question)
            if not search_terms and not custom_urls:
                raise ValueError("Failed to generate search terms")
            logger.info(f"Generated search terms: {search_terms}")
            logger.info(f"Custom URLs: {custom_urls}")

            # Perform web research
            extracted_info = await self.web_researcher.research(question)
            if not extracted_info:
                raise ValueError("Failed to extract relevant information")
            
            # Synthesize answer
            answer = await self.llm_handler.synthesize_answer(question, extracted_info)
            if not answer:
                raise ValueError("Failed to generate an answer")

            return {
                "question": question,
                "answer": answer,
                "search_terms": search_terms,
                "relevant_urls": list(extracted_info.keys())
            }
        except ValueError as e:
            logger.error(f"Research process failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis client
    app.state.redis = aioredis.from_url(config.redis.redis_url, decode_responses=True)
    
    # Create RateLimiter instance
    app.state.rate_limiter = RateLimiter(
        redis_client=app.state.redis,
        per_ip_limit=config.rate_limits.limit_per_ip,
        total_limit=config.rate_limits.limit_total,
        limit_interval=config.rate_limits.limit_interval
    )
    
    # Create ResearchAssistant instance
    app.state.research_assistant = await ResearchAssistant().__aenter__()
    
    try:
        yield
    finally:
        await app.state.research_assistant.__aexit__(None, None, None)
        await app.state.redis.close()

app = FastAPI(
    title="OpenAnswer Research Assistant API",
    description="This API provides answers to user questions by performing web research and utilizing large language models (LLMs) to synthesize responses.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable Swagger UI
    redoc_url=None,  # Disable ReDoc UI
    openapi_url=None # Disable OpenAPI
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.cors.domain],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

cors_headers = {
    "Access-Control-Allow-Origin": config.cors.domain,  # Use the domain from your config
    "Access-Control-Allow-Methods": "POST, GET",  # Only allow POST and GET
    "Access-Control-Allow-Headers": "*",  # Allow all headers
    "Access-Control-Allow-Credentials": "true"  # Enable credentials if allowed
}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    # Apply rate limiting only to /api/answer
    if request.url.path == "/api/answer":
        client_ip = request.client.host
        rate_limiter: RateLimiter = request.app.state.rate_limiter
        limit_status = await rate_limiter.check_limits(client_ip)
        
        if not limit_status["allowed"]:
            limit_type = limit_status["exceeded"]
            retry_after = limit_status["retry_after"]

            # Construct detailed response
            detail = {
                "detail": "Rate limit exceeded",
                "limit_type": limit_type.upper(),
                "retry_after_seconds": retry_after
            }
            return JSONResponse(
                status_code=429,
                content=detail,
                headers={
                    "Retry-After": str(retry_after),
                    **cors_headers  # Dynamically include CORS headers
                }
            )
    
    # Proceed with the request if rate limits are not exceeded or for other paths
    response = await call_next(request)
    return response


class Question(BaseModel):
    content: str

@app.post("/api/answer")
async def get_answer_for_question(question: Question = Body(...)):
    result = await app.state.research_assistant.research_and_answer(question.content)
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def main():
    from uvicorn import Config, Server

    uvicorn_config = Config(
        app="main:app",
        host=config.api.api_host,
        port=config.api.api_port,
        reload=False,
        log_level="info"
    )
    server = Server(config=uvicorn_config)
    
    asyncio.run(server.serve())

if __name__ == "__main__":
    main()