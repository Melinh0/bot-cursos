import random
import time
from collections.abc import Callable
from typing import TypeVar

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def safe_click(driver: WebDriver, element: WebElement, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            random_delay(0.5, 1.0)
            element.click()
            return True
        except (ElementClickInterceptedException, StaleElementReferenceException) as e:
            logger.warning(f"Click attempt {attempt + 1} failed: {e}")
            random_delay(1.0, 2.0)
    return False


def wait_for_element(
    driver: WebDriver,
    locator: tuple,
    timeout: int = 30,
    condition: Callable = EC.presence_of_element_located,
) -> WebElement | None:
    try:
        return WebDriverWait(driver, timeout).until(condition(locator))
    except TimeoutException:
        logger.error(f"Element not found: {locator} within {timeout}s")
        return None


def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
) -> T:
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            delay = min(base_delay * (2**attempt) + random.uniform(0, 1), max_delay)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
            time.sleep(delay)
    raise last_exception
