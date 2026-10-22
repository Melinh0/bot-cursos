import re

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.helpers import random_delay
from src.utils.logging import get_logger

logger = get_logger(__name__)

COURSE_HREF_RE = re.compile(r"/course/([^/?#]+)")
PROGRESS_RE = re.compile(r"(\d+)\s*%")

COURSE_CARD_SELECTOR = ".course-card, .course-item, [data-course-id]"

BASE_URL = "https://www.datascienceacademy.com.br"


def player_url(course_slug: str) -> str:
    return f"{BASE_URL}/path-player?courseid={course_slug}"


def select_lowest_progress(courses: list[dict]) -> dict | None:

    candidates = [c for c in courses if (c.get("progress") or 0) < 100]
    if not candidates:
        return None
    return min(candidates, key=lambda c: c.get("progress") or 0)


class CourseDiscovery:
    START_URL = f"{BASE_URL}/start"
    DASHBOARD_URL = f"{BASE_URL}/dashboard"

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def discover_enrolled(self) -> list[dict]:

        logger.info("Discovering enrolled courses")
        try:
            self.driver.get(self.START_URL)
        except Exception as e:
            logger.error(f"Failed to open the student home page: {e}")
            return []

        random_delay(1.5, 2.5)

        courses: dict[str, dict] = {}
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/course/']")
        except Exception as e:
            logger.error(f"Course discovery failed: {e}")
            return []

        for element in links:
            try:
                href = element.get_attribute("href") or ""
                text = (element.text or "").strip()
            except Exception:
                continue

            match = COURSE_HREF_RE.search(href)
            if not match:
                continue
            slug = match.group(1)

            entry = courses.setdefault(
                slug,
                {"slug": slug, "title": "", "progress": 0, "url": f"{BASE_URL}/course/{slug}"},
            )

            progress_match = PROGRESS_RE.search(text)
            if progress_match:
                entry["progress"] = int(progress_match.group(1))
            elif text and len(text) > len(entry["title"]):
                entry["title"] = text.replace("\n", " ")[:120]

        result = list(courses.values())
        for course in result:
            course["title"] = re.sub(r"^\d+\s*h\s*", "", course["title"]).strip()
            if not course["title"]:
                course["title"] = course["slug"].replace("-", " ").title()

        logger.info(f"Discovered {len(result)} enrolled courses")
        for course in result:
            logger.info(f"  - {course['title']}: {course['progress']}%")

        return result

    def discover_courses(self) -> list[dict]:

        logger.info("Discovering available courses via dashboard")
        self.driver.get(self.DASHBOARD_URL)
        random_delay(2, 3)

        courses = []
        try:
            course_elements = self.driver.find_elements(By.CSS_SELECTOR, COURSE_CARD_SELECTOR)
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

            link_elem = element.find_element(
                By.CSS_SELECTOR, "a[href*='path-player'], a[href*='course']"
            )
            url = link_elem.get_attribute("href")

            progress_elem = element.find_elements(
                By.CSS_SELECTOR, ".progress, .completion, [data-progress]"
            )
            progress = progress_elem[0].text.strip() if progress_elem else "0%"

            return {"title": title, "url": url, "progress": progress}
        except Exception:
            return None

    def get_course_url_by_title(self, title: str) -> str | None:
        courses = self.discover_enrolled()
        for course in courses:
            if title.lower() in course["title"].lower():
                return course["url"]
        return None
