from typing import List, Tuple, Dict
from openai import AsyncOpenAI
from config import config
from utils import get_human_readable_datetime, extract_content_between_tags, fix_footnotes
import yaml
import logging
import os

logger = logging.getLogger(__name__)
logger.propagate = False

class PromptManager:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts = {}
        self._load_all_prompts(prompts_dir)

    def _load_all_prompts(self, prompts_dir: str):
        for filename in os.listdir(prompts_dir):
            if filename.endswith(".yaml"):
                prompt_name = filename[:-5]  # Remove .yaml extension
                try:
                    with open(os.path.join(prompts_dir, filename), 'r') as file:
                        self.prompts[prompt_name] = yaml.safe_load(file)
                except Exception as e:
                    logger.error(f"Error loading prompt file {filename}: {str(e)}")

    def get_formatted_prompt(self, prompt_name: str, **kwargs) -> Dict[str, str]:
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        formatted_prompt = {}
        for key, value in self.prompts[prompt_name].items():
            formatted_prompt[key] = value.format(date=get_human_readable_datetime(), **kwargs)
        return formatted_prompt

class LLMHandler:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.api_keys.openai_api_key.get_secret_value())
        self.prompt_manager = PromptManager()

    async def _call_llm(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.5, max_tokens: int = 150) -> str:
        try:
            completion = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise

    async def generate_search_queries(self, question: str) -> Tuple[List[str], List[str]]:
        formatted_prompt = self.prompt_manager.get_formatted_prompt("search_term", question=question)
        
        try:
            response = await self._call_llm(
                config.models.search_model,
                [
                    {"role": "system", "content": formatted_prompt['system']},
                    {"role": "user", "content": formatted_prompt['user']}
                ]
            )
            
            search_terms = extract_content_between_tags(response, 'search_terms')
            custom_urls = extract_content_between_tags(response, 'custom_urls')
            
            search_terms = [term.strip() for term in search_terms.split('\n') if term.strip()]
            custom_urls = [url.strip() for url in custom_urls.split('\n') if url.strip()]
            
            return search_terms, custom_urls
        except Exception as e:
            logger.error(f"Error in generate_search_queries: {str(e)}")
            return [], []

    async def filter_relevant_results(self, results: List[Dict[str, str]], question: str) -> List[str]:
        formatted_prompt = self.prompt_manager.get_formatted_prompt("url_selection", question=question, search_results=results)
        
        try:
            response = await self._call_llm(
                config.models.search_model,
                [
                    {"role": "system", "content": formatted_prompt['system']},
                    {"role": "user", "content": formatted_prompt['user']}
                ],
                max_tokens=512
            )
            
            urls = extract_content_between_tags(response, 'selected_urls')
            return [url.strip() for url in urls.split('\n') if url.strip()]
        except Exception as e:
            logger.error(f"Error in filter_relevant_results: {str(e)}")
            return []

    async def extract_relevant_info(self, question: str, content: str, url: str) -> str:
        formatted_prompt = self.prompt_manager.get_formatted_prompt("extraction", question=question, web_content=content, url=url)
        
        try:
            response = await self._call_llm(
                config.models.extract_model,
                [
                    {"role": "system", "content": formatted_prompt['system']},
                    {"role": "user", "content": formatted_prompt['user']}
                ],
                max_tokens=1024
            )
            
            if "[no_relevant_info]" in response:
                return None
            return response
        except Exception as e:
            logger.error(f"Error in extract_relevant_info: {str(e)}")
            return None

    async def synthesize_answer(self, question: str, extracted_info: Dict[str, str]) -> str:
        web_results_formatted = "\n\n".join([f"<url>{url}</url>\n<content>\n{content}\n</content>" for url, content in extracted_info.items()])
        formatted_prompt = self.prompt_manager.get_formatted_prompt("answer", web_results=web_results_formatted, question=question)
        
        try:
            response = await self._call_llm(
                config.models.answer_model,
                [
                    {"role": "system", "content": formatted_prompt['system']},
                    {"role": "user", "content": formatted_prompt['user']}
                ],
                max_tokens=2048
            )
            return fix_footnotes(response)
        except Exception as e:
            logger.error(f"Error in synthesize_answer: {str(e)}")
            return "I'm sorry, but I encountered an error while trying to generate an answer. Please try again later."