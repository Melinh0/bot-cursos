import json
from pathlib import Path

from selenium.webdriver.common.by import By

from src.utils.logging import get_logger

logger = get_logger(__name__)

Locator = tuple[str, str]

BASE_SELECTORS: dict[str, list[Locator]] = {
    "login_link": [
        (By.ID, "menuItem_1592487994826_6"),
        (By.CSS_SELECTOR, "a[data-interactive-link-var1='signin']"),
        (By.XPATH, "//a[contains(normalize-space(.), 'Entrar')]"),
        (By.XPATH, "//span[contains(normalize-space(.), 'Entrar')]/ancestor::a[1]"),
    ],
    "email_input": [
        (By.ID, "signin-email"),
        (By.CSS_SELECTOR, "input[name='email']"),
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, ".login-form input[type='email']"),
    ],
    "password_input": [
        (By.ID, "signin-password"),
        (By.CSS_SELECTOR, "input[name='password']"),
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.CSS_SELECTOR, ".login-form input[type='password']"),
    ],
    "submit_login": [
        (By.ID, "submitLogin"),
        (By.CSS_SELECTOR, ".login-form button"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ],
    "signin_error": [
        (By.CSS_SELECTOR, ".js-signin-error-msg"),
        (By.CSS_SELECTOR, ".js-original-signin-error-wrapper p"),
    ],
    "logged_in": [
        (By.CSS_SELECTOR, ".lw-user-menu"),
        (By.CSS_SELECTOR, ".user-dropdown"),
        (By.CSS_SELECTOR, ".lw-avatar"),
        (By.CSS_SELECTOR, "a[href*='logout']"),
        (By.CSS_SELECTOR, "a[href$='/profile']"),
        (By.CSS_SELECTOR, "a[href$='/account']"),
        (By.CSS_SELECTOR, "[class*='user-menu']"),
    ],
    "next_button": [
        (By.CSS_SELECTOR, ".default-course-player-nav-btn.next"),
        (By.CSS_SELECTOR, "button[class*='next']"),
        (By.CSS_SELECTOR, "a[class*='next']"),
        (By.XPATH, "//button[contains(translate(text(), 'próximan', 'PRÓXIMAN'), 'PRÓXIM')]"),
        (By.XPATH, "//a[contains(translate(text(), 'próximan', 'PRÓXIMAN'), 'PRÓXIM')]"),
        (By.XPATH, "//button[contains(translate(text(), 'next', 'NEXT'), 'NEXT')]"),
    ],
    "complete_button": [
        (By.CSS_SELECTOR, "button[class*='complete']"),
        (By.CSS_SELECTOR, "[class*='mark-as']"),
        (By.CSS_SELECTOR, "[class*='complete']:not(div):not(span)"),
        (
            By.XPATH,
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'conclu')]",
        ),
        (
            By.XPATH,
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete')]",
        ),
        (
            By.XPATH,
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'marcar')]",
        ),
    ],
    "video_element": [
        (By.CSS_SELECTOR, "video"),
        (By.CSS_SELECTOR, ".course-player-content video"),
        (By.CSS_SELECTOR, "iframe[src*='video'], iframe[src*='player']"),
    ],
    "quiz_container": [
        (By.CLASS_NAME, "quiz-container"),
        (By.CSS_SELECTOR, "[class*='quiz'][class*='container']"),
        (By.CSS_SELECTOR, ".course-player-content [class*='quiz']"),
    ],
    "quiz_option": [
        (By.CLASS_NAME, "quiz-option"),
        (By.CSS_SELECTOR, ".quiz-container [class*='option']"),
        (By.CSS_SELECTOR, "label[class*='option']"),
    ],
    "quiz_submit": [
        (By.CLASS_NAME, "quiz-submit"),
        (By.CSS_SELECTOR, ".quiz-container button[type='submit']"),
        (By.CSS_SELECTOR, ".quiz-container button"),
    ],
    "activity_container": [
        (By.CLASS_NAME, "activity-container"),
        (By.CSS_SELECTOR, ".course-player-content [class*='activity']"),
        (By.CSS_SELECTOR, ".course-player-content textarea"),
    ],
    "activity_prompt": [
        (By.CLASS_NAME, "activity-prompt"),
        (By.CSS_SELECTOR, "[class*='activity'] [class*='prompt']"),
    ],
    "activity_submit": [
        (By.CLASS_NAME, "activity-submit"),
        (By.CSS_SELECTOR, ".activity-container button[type='submit']"),
        (By.CSS_SELECTOR, ".course-player-content [class*='activity'] button"),
    ],
    "course_content": [
        (By.CLASS_NAME, "course-player-content"),
        (By.CSS_SELECTOR, "[class*='course-player']"),
    ],
}


class SelectorMemory:
    def __init__(self, storage_path: str = "data/selector_memory.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load()

    def _load(self) -> dict:
        if not self.storage_path.exists():
            return {}
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load selector memory: {e}")
            return {}

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save selector memory: {e}")

    def locators(self, name: str) -> list[Locator]:
        learned = self.memory.get(name, [])
        base = BASE_SELECTORS.get(name, [])
        merged: list[Locator] = []
        for locator in [*learned, *base]:
            if locator not in merged:
                merged.append(locator)
        return merged

    def learn(self, name: str, locator: Locator) -> None:
        learned = self.memory.setdefault(name, [])
        if locator in learned:
            return
        learned.insert(0, list(locator))
        logger.info(f"Learned new selector for '{name}': {locator}")
        self._save()

    def learn_from_element(self, name: str, element) -> Locator | None:
        try:
            element_id = element.get_attribute("id")
            if element_id:
                locator = (By.ID, element_id)
            else:
                css = element.get_attribute("class")
                if not css:
                    return None
                locator = (By.CSS_SELECTOR, "." + ".".join(css.split()[:2]))
        except Exception as e:
            logger.warning(f"Could not derive selector for '{name}': {e}")
            return None

        self.learn(name, locator)
        return locator
