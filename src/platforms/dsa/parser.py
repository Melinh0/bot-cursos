from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.logging import get_logger

logger = get_logger(__name__)


class CourseParser:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def parse_current_unit(self) -> dict:
        return {
            "title": self.get_unit_title(),
            "type": self.get_unit_type(),
            "content": self.get_unit_content(),
            "has_quiz": self.has_quiz(),
            "has_activity": self.has_activity(),
        }

    def get_unit_title(self) -> str:
        try:
            selectors = [
                ".unit-title",
                ".lesson-title",
                "h1",
                "h2",
                "[data-unit-title]",
            ]
            for selector in selectors:
                elem = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elem:
                    return elem[0].text.strip()
        except Exception:
            pass
        return ""

    def get_unit_type(self) -> str:
        page_source = self.driver.page_source.lower()
        if "quiz" in page_source or "question" in page_source:
            return "quiz"
        if "activity" in page_source or "exercise" in page_source:
            return "activity"
        if "video" in page_source:
            return "video"
        return "content"

    def get_unit_content(self) -> str:
        try:
            content_elem = self.driver.find_element(
                By.CSS_SELECTOR, ".course-player-content, .lesson-content, .unit-content"
            )
            return content_elem.text.strip()[:5000]
        except Exception:
            return ""

    def has_quiz(self) -> bool:
        try:
            self.driver.find_element(
                By.CSS_SELECTOR, ".quiz-container, .quiz-question, [data-quiz]"
            )
            return True
        except Exception:
            return False

    def has_activity(self) -> bool:
        try:
            self.driver.find_element(
                By.CSS_SELECTOR, ".activity-container, .exercise-container, [data-activity]"
            )
            return True
        except Exception:
            return False

    def extract_quiz_details(self) -> dict | None:
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, ".quiz-container")
            question = container.find_element(By.CSS_SELECTOR, ".quiz-question").text.strip()
            options = [
                opt.text.strip() for opt in container.find_elements(By.CSS_SELECTOR, ".quiz-option")
            ]
            return {"question": question, "options": options, "container": container}
        except Exception:
            return None

    def extract_activity_details(self) -> dict | None:
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, ".activity-container")
            prompt = container.find_element(
                By.CSS_SELECTOR, ".activity-prompt, .exercise-prompt"
            ).text.strip()
            return {"prompt": prompt, "container": container}
        except Exception:
            return None
