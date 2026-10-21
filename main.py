import sys
from src.config.settings import settings
from src.bot import BrowserManager, LoginHandler, CourseNavigator
from src.courses import CourseDiscovery, ProgressTracker
from src.llm import QuizSolver
from src.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def main():
    setup_logging()
    logger.info("Starting DataScienceAcademy Bot")

    progress_tracker = ProgressTracker()
    quiz_solver = QuizSolver()

    with BrowserManager() as driver:
        login_handler = LoginHandler(driver)

        if not login_handler.login():
            logger.error("Login failed, exiting")
            sys.exit(1)

        navigator = CourseNavigator(driver)

        if settings.auto_discover_courses:
            discovery = CourseDiscovery(driver)
            courses = discovery.discover_courses()

            if courses:
                logger.info(f"Found {len(courses)} courses")
                for course in courses:
                    logger.info(f"  - {course['title']}: {course['progress']}")

                target_course = next(
                    (c for c in courses if "fundamentos" in c["title"].lower()),
                    courses[0]
                )
                course_url = target_course["url"]
                logger.info(f"Selected course: {target_course['title']}")
            else:
                logger.warning("No courses discovered, using target URL")
                course_url = settings.target_course_url
        else:
            course_url = settings.target_course_url

        if not navigator.navigate_to_course(course_url):
            logger.error("Failed to navigate to course")
            sys.exit(1)

        logger.info("Starting course automation loop")
        navigator.run_course_loop(quiz_solver)

        stats = progress_tracker.get_stats()
        logger.info(f"Final stats: {stats}")


if __name__ == "__main__":
    main()