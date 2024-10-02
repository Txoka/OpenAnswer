import httpx
import asyncio
from typing import List, Dict, NamedTuple
from config import config
from crawl4ai import AsyncWebCrawler
from llm_operations import LLMHandler
import logging
from logging import Filter

class NoApiKeysFilter(Filter):
    def filter(self, record):
        # Remove API keys or any other sensitive information from the logs
        record.msg = record.msg.replace(config.api_keys.google_search_api_key.get_secret_value(), "[API_KEY]")
        record.msg = record.msg.replace(config.search.search_engine_id.get_secret_value(), "[SEARCH_ENGINE_ID]")
        return True


logger = logging.getLogger(__name__)
logger.propagate = False
logger.addFilter(NoApiKeysFilter())

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)
httpx_logger.addFilter(NoApiKeysFilter())

class SearchResult(NamedTuple):
    title: str
    url: str
    snippet: str

class WebResearcher:
    def __init__(self):
        self.api_key = config.api_keys.google_search_api_key.get_secret_value()
        self.search_engine_id = config.search.search_engine_id.get_secret_value()
        self.llm_handler = LLMHandler()
        self.crawler = AsyncWebCrawler(verbose=False)
        self.httpx_client = httpx.AsyncClient()

    async def __aenter__(self):
        await self.crawler.__aenter__()
        await self.httpx_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
        if self.httpx_client:
            await self.httpx_client.__aexit__(exc_type, exc_val, exc_tb)

    async def research(self, question: str) -> Dict[str, str]:
        search_terms, custom_urls = await self.llm_handler.generate_search_queries(question)
        logger.info(f"Generated search terms: {search_terms}")
        logger.info(f"Custom URLs: {custom_urls}")

        search_results = await self.search_web(search_terms)
        
        all_urls = custom_urls + [result.url for result in search_results]

        relevant_urls = await self.llm_handler.filter_relevant_results(
            [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in search_results],
            question
        )
        relevant_urls = list(dict.fromkeys(relevant_urls + custom_urls))  # Remove duplicates while preserving order
        logger.info(f"Filtered relevant URLs: {relevant_urls}")

        extracted_info = await self.fetch_and_extract_content(relevant_urls, question)
        return extracted_info

    async def search_web(self, queries: List[str], results_per_query: int = 10) -> List[SearchResult]:
        all_results = []
        for query in queries:
            try:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "q": query,
                    "cx": self.search_engine_id,
                    "key": self.api_key,
                    "num": results_per_query
                }
                response = await self.httpx_client.get(url, params=params)
                response.raise_for_status()  # Raise an exception for a failed request
                search_results = response.json()
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
                extracted_info = await self.llm_handler.extract_relevant_info(question, result.markdown, url)
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
