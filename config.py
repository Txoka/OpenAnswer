import os
from dotenv import load_dotenv
from typing import Dict, Any
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()

class APIKeys(BaseSettings):
    google_search_api_key: SecretStr
    openai_api_key: SecretStr

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


class SearchSettings(BaseSettings):
    search_engine_id: SecretStr
    max_results: int

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class ModelSettings(BaseSettings):
    search_model: str = "gpt-4o-mini"
    extract_model: str = "gpt-4o-mini"
    answer_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class CrawlerSettings(BaseSettings):
    max_urls: int = 5
    crawl_timeout: int = 60

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class APISettings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class Config(BaseSettings):
    api_keys: APIKeys = Field(default_factory=APIKeys)
    search: SearchSettings = Field(default_factory=SearchSettings)
    models: ModelSettings = Field(default_factory=ModelSettings)
    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    api: APISettings = Field(default_factory=APISettings)

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    def as_dict(self) -> Dict[str, Any]:
        return {
            "api_keys": self.api_keys.model_dump(),
            "search": self.search.model_dump(),
            "models": self.models.model_dump(),
            "crawler": self.crawler.model_dump(),
            "api": self.api.model_dump(),
        }

config = Config()