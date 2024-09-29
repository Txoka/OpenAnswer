from typing import List, Dict, NamedTuple
from googleapiclient.discovery import build
from config import config
from crawl4ai import AsyncWebCrawler
from llm_operations import LLMHandler
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.propagate = False

class SearchResult(NamedTuple):
    title: str
    url: str
    snippet: str

class WebResearcher:
    def __init__(self):
        self.google_service = build("customsearch", "v1", developerKey=config.api_keys.google_search_api_key.get_secret_value())
        self.llm_handler = LLMHandler()
        self.crawler = AsyncWebCrawler(verbose=False)

    async def __aenter__(self):
        await self.crawler.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)

    async def research(self, question: str) -> Dict[str, str]:
        search_terms, custom_urls = self.llm_handler.generate_search_queries(question)
        logger.info(f"Generated search terms: {search_terms}")
        logger.info(f"Custom URLs: {custom_urls}")

        search_results = self.search_web(search_terms)
        
        all_urls = custom_urls + [result.url for result in search_results]

        relevant_urls = self.llm_handler.filter_relevant_results(
            [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in search_results],
            question
        )
        relevant_urls = list(dict.fromkeys(relevant_urls + custom_urls))  # Remove duplicates while preserving order
        logger.info(f"Filtered relevant URLs: {relevant_urls}")

        extracted_info = await self.fetch_and_extract_content(relevant_urls, question)
        return extracted_info

    def search_web(self, queries: List[str], results_per_query: int = 10) -> List[SearchResult]:
        all_results = []
        for query in queries:
            try:
                search_results = self.google_service.cse().list(q=query, cx=config.search.search_engine_id.get_secret_value(), num=results_per_query).execute()
                for item in search_results.get('items', []):
                    result = SearchResult(
                        title=item['title'],
                        url=item['link'],
                        snippet=item['snippet']
                    )
                    if result not in all_results:
                        all_results.append(result)
            except Exception as e:
                logger.error(f"Error searching for '{query}': {str(e)}")

        return all_results

    async def fetch_and_extract_content(self, urls: List[str], question: str) -> Dict[str, str]:
        async def process_url(url: str) -> tuple[str, str]:
            try:
                result = await asyncio.wait_for(self.crawler.arun(url=url), timeout=config.crawler.crawl_timeout)
                if not result or not result.markdown or result.markdown.strip() == "":
                    logger.warning(f"No content retrieved from {url}")
                    return url, None
                extracted_info = self.llm_handler.extract_relevant_info(question, result.markdown, url)
                return url, extracted_info
            except asyncio.TimeoutError:
                logger.warning(f"crawl_timeout while crawling {url}")
                return url, None
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                return url, None
        
        tasks = [process_url(url) for url in urls]
        results = await asyncio.gather(*tasks)
    
        return {url: info for url, info in results if info is not None}