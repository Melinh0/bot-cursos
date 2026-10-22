from openai import APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from src.config.settings import settings
from src.utils.helpers import retry_with_backoff
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.api_keys = settings.api_keys_list or ["ollama"]
        self.current_key_index = 0
        self.models = self._build_model_list()
        self.current_model_index = 0
        self.client = None
        self._initialize_client()

    def _build_model_list(self) -> list[str]:
        models = [settings.llm_model]
        for extra in settings.llm_fallback_models_list:
            if extra and extra not in models:
                models.append(extra)
        return models

    def _initialize_client(self) -> None:
        try:
            self.client = OpenAI(
                base_url=settings.llm_base_url,
                api_key=self.api_keys[self.current_key_index],
                timeout=settings.llm_timeout,
            )
        except Exception as e:
            logger.error(f"Failed to initialize the LLM client: {e}")
            self.client = None

    def _rotate_key(self) -> bool:
        if len(self.api_keys) <= 1:
            return False

        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._initialize_client()
        logger.info(f"Rotated to API key index {self.current_key_index}")
        return True

    def _rotate_model(self) -> bool:
        if len(self.models) <= 1:
            return False

        self.current_model_index = (self.current_model_index + 1) % len(self.models)
        logger.info(f"Switched to fallback model: {self.models[self.current_model_index]}")
        return True

    def chat_completion(
        self,
        messages: list,
        temperature: float = None,
        max_tokens: int = None,
    ) -> str | None:
        if self.client is None:
            logger.error("LLM client not initialized")
            return None

        temp = temperature if temperature is not None else settings.llm_temperature
        max_tok = max_tokens if max_tokens is not None else settings.llm_max_tokens
        model = self.models[self.current_model_index]

        def _make_request():
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
            )
            return response.choices[0].message.content

        attempts = max(1, len(self.api_keys) * len(self.models))

        for attempt in range(attempts):
            try:
                return retry_with_backoff(
                    _make_request,
                    max_retries=2,
                    exceptions=(
                        RateLimitError,
                        AuthenticationError,
                        APITimeoutError,
                        ConnectionError,
                    ),
                )
            except (RateLimitError, AuthenticationError, APITimeoutError) as e:
                logger.warning(f"LLM request failed ({type(e).__name__}), rotating key/model")
                if not self._rotate_key() and not self._rotate_model():
                    break
                model = self.models[self.current_model_index]
            except Exception as e:
                logger.error(f"LLM request failed: {e}")
                if not self._rotate_model():
                    break
                model = self.models[self.current_model_index]

        logger.error("All LLM keys/models exhausted")
        return None
