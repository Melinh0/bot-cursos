from src.bot import BrowserManager
from src.platforms.moodle.login import MoodleLogin
from src.platforms.moodle.navigator import MoodleNavigator
from src.utils.logging import get_logger

logger = get_logger(__name__)


def discover_softer_course(course_name_substring="Softex"):
    manager = BrowserManager()
    with manager:
        driver = manager.get_driver()
        login = MoodleLogin(driver)
        login.login()
        navigator = MoodleNavigator(driver)
        course = navigator.find_course(course_name_substring)
        if course:
            logger.info(f"Course found: {course['title']} -> {course['url']}")
            return course
        logger.warning("Course not found")
        return None
