from openai import APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from src.config.settings import settings
from src.utils.helpers import retry_with_backoff
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.api_keys = settings.api_keys_list
        self.current_key_index = 0
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.api_keys:
            logger.warning("No API keys configured")
            return

        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=self.api_keys[self.current_key_index],
        )

    def _rotate_key(self) -> bool:
        if len(self.api_keys) <= 1:
            return False

        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=self.api_keys[self.current_key_index],
        )
        logger.info(f"Rotated to API key index {self.current_key_index}")
        return True

    def chat_completion(
        self,
        messages: list,
        temperature: float = None,
        max_tokens: int = None,
    ) -> str | None:
        if not self.client:
            logger.error("LLM client not initialized")
            return None

        temp = temperature if temperature is not None else settings.llm_temperature
        max_tok = max_tokens if max_tokens is not None else settings.llm_max_tokens

        def _make_request():
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
            )
            return response.choices[0].message.content

        max_key_retries = len(self.api_keys)
        for key_attempt in range(max_key_retries):
            try:
                return retry_with_backoff(
                    _make_request,
                    max_retries=2,
                    exceptions=(RateLimitError, AuthenticationError, APITimeoutError, ConnectionError),
                )
            except RateLimitError:
                logger.warning("Rate limit hit, rotating key")
                if not self._rotate_key():
                    break
            except AuthenticationError:
                logger.warning("Authentication error, rotating key")
                if not self._rotate_key():
                    break
            except APITimeoutError:
                logger.warning("Timeout, rotating key")
                if not self._rotate_key():
                    break
            except Exception as e:
                logger.error(f"LLM request failed: {e}")
                if not self._rotate_key():
                    break

        logger.error("All API keys exhausted")
        return None
