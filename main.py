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
import redis.asyncio as aioredis
from datetime import datetime, timedelta

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

class RateLimiter:
    def __init__(self, redis_client: aioredis.Redis, ip_daily_limit: int, total_daily_limit: int):
        self.redis = redis_client
        self.ip_daily_limit = ip_daily_limit
        self.total_daily_limit = total_daily_limit
        self.total_key = "total_requests"
        self.ip_key_prefix = "ip-requests:"

    async def is_allowed(self, ip: str) -> bool:
        pipeline = self.redis.pipeline()
        
        # Increment total requests
        pipeline.incr(self.total_key)
        # Set expiration for total requests to end of day
        pipeline.expire(self.total_key, self.seconds_until_end_of_day())
        
        # Increment IP requests
        ip_key = f"{self.ip_key_prefix}{ip}"
        pipeline.incr(ip_key)
        # Set expiration for IP requests to end of day
        pipeline.expire(ip_key, self.seconds_until_end_of_day())

        results = await pipeline.execute()
        total_requests = results[0]
        ip_requests = results[2]

        if total_requests > self.total_daily_limit:
            return False

        if ip_requests > self.ip_daily_limit:
            return False

        return True

    def seconds_until_end_of_day(self) -> int:
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        midnight = datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day)
        return int((midnight - now).total_seconds())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis client
    app.state.redis = aioredis.from_url(config.redis.redis_url, decode_responses=True)
    
    # Create RateLimiter instance
    app.state.rate_limiter = RateLimiter(
        redis_client=app.state.redis,
        ip_daily_limit=config.rate_limits.ip_daily,
        total_daily_limit=config.rate_limits.total_daily
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
    openapi_url=None, # Disable OpenAPI
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.cors.domain],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

class Question(BaseModel):
    content: str

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    rate_limiter: RateLimiter = request.app.state.rate_limiter
    is_allowed = await rate_limiter.is_allowed(client_ip)
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    response = await call_next(request)
    return response

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