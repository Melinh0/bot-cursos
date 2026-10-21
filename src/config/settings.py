from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    dsa_email: str = Field(..., alias="DSA_EMAIL")
    dsa_password: str = Field(..., alias="DSA_PASSWORD")

    llm_base_url: str = Field(default="http://localhost:11434/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="llama3.1", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")

    ollama_api_keys: str = Field(default="", alias="OLLAMA_API_KEYS")

    headless: bool = Field(default=False, alias="HEADLESS")
    browser_timeout: int = Field(default=30, alias="BROWSER_TIMEOUT")
    implicit_wait: int = Field(default=10, alias="IMPLICIT_WAIT")

    target_course_url: str = Field(
        default="https://www.datascienceacademy.com.br/path-player?courseid=fundamentos-de-linguagem-python-para-analise-de-dados-e-data-science&unit=63aa11114343420e8702d3c7Unit",
        alias="TARGET_COURSE_URL",
    )
    auto_discover_courses: bool = Field(default=True, alias="AUTO_DISCOVER_COURSES")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/bot.log", alias="LOG_FILE")

    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_delay: int = Field(default=5, alias="RETRY_DELAY")

    @property
    def api_keys_list(self) -> list[str]:
        if not self.ollama_api_keys:
            return []
        return [key.strip() for key in self.ollama_api_keys.split(",") if key.strip()]


settings = Settings()
