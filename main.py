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


# Setup logging
setup_logging(log_file='app.log', log_level=logging.INFO)
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
            search_terms, custom_urls = self.llm_handler.generate_search_queries(question)
            if not search_terms and not custom_urls:
                raise ValueError("Failed to generate search terms")
            logger.info(f"Generated search terms: {search_terms}")
            logger.info(f"Custom URLs: {custom_urls}")

            # Perform web research
            extracted_info = await self.web_researcher.research(question)
            if not extracted_info:
                raise ValueError("Failed to extract relevant information")
            
            # Synthesize answer
            answer = self.llm_handler.synthesize_answer(question, extracted_info)
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
    # Create a single ResearchAssistant instance for the entire application
    app.state.research_assistant = await ResearchAssistant().__aenter__()
    yield
    await app.state.research_assistant.__aexit__(None, None, None)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust this to match your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
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
        reload=True,
        log_level="info"
    )
    server = Server(config=uvicorn_config)
    
    asyncio.run(server.serve())

if __name__ == "__main__":
    main()