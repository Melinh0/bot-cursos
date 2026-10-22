import random
import time
from collections.abc import Callable
from typing import TypeVar

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def random_delay(min_seconds: float | None = None, max_seconds: float | None = None) -> None:
    if min_seconds is None:
        min_seconds = settings.humanize_delay_min
    if max_seconds is None:
        max_seconds = settings.humanize_delay_max
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


def find_first(
    driver: WebDriver,
    locators: list[tuple],
    timeout: int = 15,
    condition: Callable = EC.presence_of_element_located,
) -> WebElement | None:

    if not locators:
        return None

    per_locator = max(1, timeout // len(locators))

    for locator in locators:
        element = wait_for_element(
            driver,
            locator,
            timeout=per_locator,
            condition=condition,
        )
        if element is not None:
            return element

    logger.warning(f"None of the {len(locators)} locators matched: {locators}")
    return None


def find_by_text(
    driver: WebDriver,
    tags: tuple[str, ...] = ("a", "button", "span", "div"),
    texts: tuple[str, ...] = (),
    timeout: int = 10,
) -> WebElement | None:

    if not texts:
        return None

    for tag in tags:
        for text in texts:
            xpath = (
                f"//{tag}[contains(translate(normalize-space(.),"
                f" 'abcdefghijklmnopqrstuvwxyzáàâãéêíóôõúç',"
                f" 'ABCDEFGHIJKLMNOPQRSTUVWXYZAAAAEEEEIOOOOUC'),"
                f" '{text.lower()}')]"
            )
            element = wait_for_element(driver, (By.XPATH, xpath), timeout=timeout)
            if element is not None:
                return element

    return None


def is_visible(element) -> bool:
    try:
        return element.is_displayed() and element.is_enabled()
    except Exception:
        return False


def locators_to_css(locators: list[tuple]) -> list[str]:
    css = []
    for by, value in locators:
        if by == By.CSS_SELECTOR:
            css.append(value)
        elif by == By.ID:
            css.append("#" + value)
        elif by == By.CLASS_NAME:
            css.append("." + value)
    return css


JS_VIS = """
function __vis(el) {
    const st = getComputedStyle(el);
    return st.display !== 'none' && st.visibility !== 'hidden' && (el.offsetHeight > 0 || el.getClientRects().length > 0);
}
"""

JS_ANY_VISIBLE = (
    JS_VIS
    + """
const sels = arguments[0];
for (const sel of sels) {
    let els;
    try { els = document.querySelectorAll(sel); } catch (e) { continue; }
    for (const el of els) { if (__vis(el)) return true; }
}
return false;
"""
)

JS_MATCH_SELECTOR = (
    JS_VIS
    + """
const sels = arguments[0];
for (const sel of sels) {
    try { if (document.querySelector(sel)) return sel; } catch (e) {}
}
const ctx = arguments[1];
const target = arguments[2];
const ctxVisible = arguments[3];
if (ctx && target) {
    let els;
    try { els = document.querySelectorAll(ctx); } catch (e) { return ""; }
    for (const el of els) {
        if (ctxVisible && !__vis(el)) continue;
        let p;
        try { p = el.closest(target); } catch (e) { continue; }
        if (!p || p === document.body || p === document.documentElement) continue;
        const tag = p.tagName.toLowerCase();
        if (p.id) return tag + "#" + CSS.escape(p.id);
        if (p.classList && p.classList.length) {
            return tag + "." + Array.from(p.classList).map(c => CSS.escape(c)).join(".");
        }
        return tag;
    }
}
return "";
"""
)

JS_CLICK_FIRST = (
    JS_VIS
    + """
const sels = arguments[0];
for (const sel of sels) {
    let els;
    try { els = document.querySelectorAll(sel); } catch (e) { continue; }
    for (const el of els) { if (__vis(el)) { el.click(); return sel; } }
}
return "";
"""
)


def js_any_visible(driver, css_selectors) -> bool | None:
    if not css_selectors:
        return False
    try:
        return bool(driver.execute_script(JS_ANY_VISIBLE, css_selectors))
    except Exception as e:
        logger.debug(f"js_any_visible failed: {e}")
        return None


def js_match_selector(
    driver,
    css_selectors,
    context_sel: str = "",
    context_target: str = "",
    context_visible: bool = False,
) -> str | None:
    if not css_selectors and not (context_sel and context_target):
        return ""
    try:
        result = driver.execute_script(
            JS_MATCH_SELECTOR,
            css_selectors,
            context_sel,
            context_target,
            bool(context_visible),
        )
        return str(result or "")
    except Exception as e:
        logger.debug(f"js_match_selector failed: {e}")
        return None


def js_click_first(driver, css_selectors) -> str:
    if not css_selectors:
        return ""
    try:
        return str(driver.execute_script(JS_CLICK_FIRST, css_selectors) or "")
    except Exception as e:
        logger.debug(f"js_click_first failed: {e}")
        return ""


def js_click(driver: WebDriver, element) -> bool:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        logger.warning(f"JS click failed: {e}")
        return False


def click_element(driver: WebDriver, element, use_js_fallback: bool = True) -> bool:
    if safe_click(driver, element):
        return True
    if use_js_fallback:
        return js_click(driver, element)
    return False


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
