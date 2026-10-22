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
    llm_timeout: int = Field(default=120, alias="LLM_TIMEOUT")
    llm_fallback_models: str = Field(default="", alias="LLM_FALLBACK_MODELS")

    ollama_api_keys: str = Field(default="", alias="OLLAMA_API_KEYS")

    headless: bool = Field(default=False, alias="HEADLESS")
    browser_timeout: int = Field(default=30, alias="BROWSER_TIMEOUT")
    implicit_wait: int = Field(default=0, alias="IMPLICIT_WAIT")
    window_size: str = Field(default="1920,1080", alias="WINDOW_SIZE")
    browser_half_screen: bool = Field(default=True, alias="BROWSER_HALF_SCREEN")

    max_run_attempts: int = Field(default=3, alias="MAX_RUN_ATTEMPTS")
    max_units_per_run: int = Field(default=0, alias="MAX_UNITS_PER_RUN")
    max_recovery_rounds: int = Field(default=3, alias="MAX_RECOVERY_ROUNDS")

    humanize_delay_min: float = Field(default=0.4, alias="HUMANIZE_DELAY_MIN")
    humanize_delay_max: float = Field(default=1.2, alias="HUMANIZE_DELAY_MAX")
    unit_timeout_seconds: int = Field(default=180, alias="UNIT_TIMEOUT_SECONDS")
    unit_min_dwell_seconds: int = Field(default=15, alias="UNIT_MIN_DWELL_SECONDS")
    unit_activity_flush_seconds: int = Field(default=10, alias="UNIT_ACTIVITY_FLUSH_SECONDS")
    max_stuck_attempts: int = Field(default=3, alias="MAX_STUCK_ATTEMPTS")
    smoke_mode: bool = Field(default=False, alias="SMOKE_MODE")

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

    @property
    def llm_fallback_models_list(self) -> list[str]:
        if not self.llm_fallback_models:
            return []
        return [model.strip() for model in self.llm_fallback_models.split(",") if model.strip()]

    @property
    def window_size_list(self) -> list[int]:
        try:
            width, height = self.window_size.lower().replace(",", "x").split("x")
            return [int(width), int(height)]
        except Exception:
            return [1920, 1080]


settings = Settings()
