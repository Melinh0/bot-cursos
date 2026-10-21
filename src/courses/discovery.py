from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.helpers import random_delay
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CourseDiscovery:
    DASHBOARD_URL = "https://www.datascienceacademy.com.br/dashboard"
    COURSE_CARD_SELECTOR = ".course-card, .course-item, [data-course-id]"

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def discover_courses(self) -> list[dict]:
        logger.info("Discovering available courses")
        self.driver.get(self.DASHBOARD_URL)
        random_delay(5, 8)

        courses = []

        try:
            course_elements = self.driver.find_elements(By.CSS_SELECTOR, self.COURSE_CARD_SELECTOR)

            for elem in course_elements:
                try:
                    course_data = self.extract_course_info(elem)
                    if course_data:
                        courses.append(course_data)
                except Exception as e:
                    logger.warning(f"Failed to extract course info: {e}")

        except Exception as e:
            logger.error(f"Course discovery failed: {e}")

        logger.info(f"Discovered {len(courses)} courses")
        return courses

    def extract_course_info(self, element) -> dict | None:
        try:
            title_elem = element.find_element(By.CSS_SELECTOR, "h3, h4, .course-title, .title")
            title = title_elem.text.strip()

            link_elem = element.find_element(By.CSS_SELECTOR, "a[href*='path-player'], a[href*='course']")
            url = link_elem.get_attribute("href")

            progress_elem = element.find_elements(By.CSS_SELECTOR, ".progress, .completion, [data-progress]")
            progress = progress_elem[0].text.strip() if progress_elem else "0%"

            return {
                "title": title,
                "url": url,
                "progress": progress,
            }
        except Exception:
            return None

    def get_course_url_by_title(self, title: str) -> str | None:
        courses = self.discover_courses()
        for course in courses:
            if title.lower() in course["title"].lower():
                return course["url"]
        return None
