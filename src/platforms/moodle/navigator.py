from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MoodleNavigator:
    def __init__(self, driver):
        self.driver = driver

    def get_courses(self):
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        courses = []
        cards = self.driver.find_elements(By.CSS_SELECTOR, ".course-card, .card, .coursebox")
        for card in cards:
            try:
                link = card.find_element(By.CSS_SELECTOR, "a")
                title = link.text.strip()
                href = link.get_attribute("href")
                if title and href:
                    courses.append({"title": title, "url": href})
            except Exception:
                continue
        logger.info(f"Found {len(courses)} courses")
        return courses

    def find_course(self, name_substring):
        courses = self.get_courses()
        for c in courses:
            if name_substring.lower() in c["title"].lower():
                return c
        return None
