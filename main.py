import asyncio
import sys
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from web_research import WebResearcher
from llm_operations import LLMHandler
from config import config
from utils import setup_logging, render_markdown
import logging
from contextlib import asynccontextmanager
import subprocess
import os
import redis


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




# Function to track requests per IP using Redis
def track_requests(ip_address: str) -> bool:
    # Define a unique key for each IP (e.g., "ip-requests:1.2.3.4")
    redis_key = f"ip-requests:{ip_address}"
    
    # Check if the IP already has a request count
    current_requests = redis_client.get(redis_key)
    
    if current_requests is None:
        # First request, set the count to 1 and expire after 24 hours (86400 seconds)
        redis_client.set(redis_key, 1, ex=86400)
        return True
    elif int(current_requests) < 5:
        # Increment the request count if under the limit
        redis_client.incr(redis_key)
        return True
    else:
        # Limit reached
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Print inside the lifespan
    
    # Create a single ResearchAssistant instance for the entire application
    app.state.research_assistant = await ResearchAssistant().__aenter__()
    yield
    await app.state.research_assistant.__aexit__(None, None, None)

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