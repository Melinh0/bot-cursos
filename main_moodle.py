import sys
from src.bot import BrowserManager
from src.config.settings import settings
from src.utils.logging import setup_logging, get_logger
from src.utils.runlog import RunLog
from src.platforms.moodle.login import MoodleLogin
from src.platforms.moodle.navigator import MoodleNavigator
from src.platforms.moodle.activity_handlers import MoodleActivityHandler

logger = get_logger(__name__)

def main():
    setup_logging()
    logger.info("Starting Moodle Softex Bot")
    run_log = RunLog()
    manager = BrowserManager()
    with manager:
        driver = manager.get_driver()
        login = MoodleLogin(driver)
        if not login.login():
            logger.error("Login failed")
            run_log.event("login_failed")
            return 1
        run_log.event("login_ok")
        navigator = MoodleNavigator(driver)
        course = navigator.find_course("Softex")
        if not course:
            logger.error("Course not found")
            run_log.event("course_not_found")
            return 2
        logger.info(f"Course found: {course['title']}")
        run_log.event("course_found", title=course["title"], url=course["url"])
        driver.get(course["url"])
        from selenium.webdriver.common.by import By
        links = driver.find_elements(By.CSS_SELECTOR, "a")
        activity_urls = []
        for link in links:
            href = link.get_attribute("href") or ""
            if "mod/" in href:
                activity_urls.append(href)
        handler = MoodleActivityHandler(driver)
        handled = 0
        for url in activity_urls[:10]:
            if handler.handle(url):
                handled += 1
        logger.info(f"Handled {handled}/{len(activity_urls)} activities")
        run_log.event("activities_handled", handled=handled, total=len(activity_urls))
    run_log.event("finished", status="completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
