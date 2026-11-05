from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.logging import get_logger

logger = get_logger(__name__)

COLLECT_ACTIVITIES_JS = """
return Array.from(document.querySelectorAll('li.activity, .activity-item')).slice(0, 60)
    .map(function(li) {
        var a = li.querySelector('a[href*="/mod/"]');
        if (!a) return null;
        var cls = li.className || '';
        var box = li.closest('.activity-item');
        if (box) cls += ' ' + (box.className || '');
        return {
            title: (a.innerText || '').trim(),
            url: a.href,
            done: /completion-complete|activity-complete|completion-auto-done/.test(cls)
        };
    })
    .filter(function(x) { return x && x.title && x.url; });
"""


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

    def collect_activities(self):
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            items = self.driver.execute_script(COLLECT_ACTIVITIES_JS) or []
        except Exception:
            items = []
        activities = []
        for item in items:
            url = item.get("url") or ""
            activity_type = "atividade"
            if "mod/quiz" in url:
                activity_type = "quiz"
            elif "mod/assign" in url:
                activity_type = "assignment"
            elif "mod/feedback" in url:
                activity_type = "feedback"
            elif "mod/resource" in url:
                activity_type = "resource"
            elif "mod/page" in url:
                activity_type = "page"
            elif "mod/forum" in url:
                activity_type = "forum"
            activities.append(
                {
                    "title": item.get("title", ""),
                    "url": url,
                    "done": bool(item.get("done")),
                    "type": activity_type,
                }
            )
        logger.info(f"Collected {len(activities)} activities from course page")
        return activities
