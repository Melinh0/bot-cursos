import sys
import time

from selenium.webdriver.common.by import By

from src.bot import BrowserManager, CourseNavigator, LoginHandler
from src.bot.recovery import RecoveryManager
from src.bot.scanner import PageScanner
from src.bot.selectors import SelectorMemory
from src.config.settings import settings
from src.courses import (
    CourseDiscovery,
    CourseMap,
    ProgressTracker,
    extract_course_id,
    player_url,
    select_lowest_progress,
)
from src.llm import QuizSolver
from src.utils.helpers import random_delay
from src.utils.logging import get_logger, setup_logging
from src.utils.runlog import RunLog

logger = get_logger(__name__)

COURSE_KEYWORDS = ("fundamentos", "python", "curso", "course", "continuar", "retomar")

EXPLORATION_URLS = (
    "https://www.datascienceacademy.com.br/cursosgratuitos",
    "https://www.datascienceacademy.com.br/todoscursosdsa",
    "https://www.datascienceacademy.com.br/todas-formacoes-dsa",
    "https://www.datascienceacademy.com.br/dashboard",
)


def explore_site(driver, scanner: PageScanner) -> None:
    logger.info("Starting site exploration to discover and enroll in courses...")

    for url in EXPLORATION_URLS[:2]:
        try:
            logger.info(f"Exploring: {url}")
            driver.get(url)
            random_delay(1.5, 2.5)

            report = scanner.scan(driver, label=url.split("/")[-1] or "page")

            enroll_buttons = scanner.get_enroll_buttons(report)
            for btn in enroll_buttons[:3]:
                try:
                    elements = driver.find_elements(
                        By.XPATH, f"//*[contains(text(), '{btn['text']}')]"
                    )
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            driver.execute_script("arguments[0].click();", el)
                            logger.info(f"Clicked enroll button: {btn['text']}")
                            random_delay(1, 2)
                            break
                except Exception as e:
                    logger.debug(f"Could not click enroll button: {e}")

        except Exception as e:
            logger.warning(f"Failed to explore {url}: {e}")


def choose_course_url(driver, scanner: PageScanner, report: dict) -> str:
    scanned = scanner.find_entry_points(report, keywords=COURSE_KEYWORDS)
    for link in scanned:
        href = link.get("href", "")
        if "path-player" in href or "unit=" in href:
            logger.info(f"Course player URL found by scanning: {href}")
            return href

    if settings.auto_discover_courses:
        discovery = CourseDiscovery(driver)
        courses = discovery.discover_enrolled()

        if courses:
            target = select_lowest_progress(courses)
            if target:
                logger.info(f"Selected course (fallback): {target['title']}")
                return player_url(target["slug"])

    for link in scanned:
        if link.get("category") in ("course", "dashboard"):
            logger.info(f"Falling back to scanned course link: {link['href']}")
            return link["href"]

    logger.warning("No course link found, using configured target URL")
    return settings.target_course_url


def run_attempt(
    manager: BrowserManager,
    tracker: ProgressTracker,
    quiz_solver: QuizSolver,
    memory: SelectorMemory,
    recovery: RecoveryManager,
    scanner: PageScanner,
    course_map: CourseMap,
    run_log: RunLog,
) -> bool:

    driver = manager.get_driver()
    login_handler = LoginHandler(driver, memory)

    if not login_handler.login():
        logger.error(f"Login failed: {login_handler.last_error or 'unknown error'}")
        run_log.event("login_failed", error=login_handler.last_error)
        return False
    run_log.event("login_ok")

    target = None
    discovery = CourseDiscovery(driver)
    courses = discovery.discover_enrolled()
    if courses:
        target = select_lowest_progress(courses)

    if target:
        course_url = player_url(target["slug"])
        course_title = target["title"]
        logger.info(f"Target course: {course_title} ({target.get('progress', 0)}%) -> {course_url}")
        run_log.event("course_selected", slug=target["slug"], progress=target.get("progress", 0))
    else:
        logger.warning("No enrolled course found - falling back to site exploration")
        run_log.event("no_enrolled_course", fallback="explore_site")
        report = scanner.scan(driver, "post_login")
        explore_site(driver, scanner)
        report = scanner.scan(driver, "post_login_explored")
        course_url = choose_course_url(driver, scanner, report)
        course_title = ""

    course_id = extract_course_id(course_url)
    if course_id and course_map is not None:
        entry = course_map.course(course_id)
        if entry.get("title") and not course_title:
            course_title = entry["title"]

    navigator = None

    def do_relogin() -> bool:
        return LoginHandler(navigator.driver, memory).login()

    def do_restart():
        return manager.restart()

    navigator = CourseNavigator(
        driver,
        memory=memory,
        recovery=recovery,
        scanner=scanner,
        relogin=do_relogin,
        restart_browser=do_restart,
        course_map=course_map,
        run_log=run_log,
    )

    if not navigator.navigate_to_course(course_url):
        logger.error("Failed to navigate to course")
        return False

    course_id = navigator.build_course_map(course_url, title=course_title) or course_id

    if course_id and course_map is not None:
        current_unit = navigator.get_current_unit()
        next_unit = course_map.next_pending(course_id)
        if next_unit and next_unit["id"] != current_unit:
            logger.info(f"Jumping to first pending unit: {next_unit['id']}")
            navigator.driver.get(next_unit["url"])
            random_delay(1, 2)
            jump_deadline = time.time() + 8
            while time.time() < jump_deadline and not navigator.get_current_unit():
                time.sleep(0.5)
            if not navigator.get_current_unit():
                logger.warning(f"Unit did not apply after jump, retrying: {next_unit['url']}")
                navigator.driver.get(next_unit["url"])
                random_delay(1, 2)

    navigator.scan_page("course_player")
    logger.info("Starting course automation loop")
    run_log.event("loop_started", course=course_id)

    max_units = 1 if settings.smoke_mode else (settings.max_units_per_run or None)
    result = navigator.run_course_loop(
        quiz_solver,
        tracker,
        course_url=course_url,
        course_id=course_id,
        max_units=max_units,
    )
    run_log.event("loop_finished", **result)
    return bool(result.get("completed"))


def main():
    setup_logging()
    logger.info("Starting DataScienceAcademy Bot")
    if settings.smoke_mode:
        logger.info("SMOKE MODE: will process at most 1 unit")

    tracker = ProgressTracker()
    quiz_solver = QuizSolver()
    memory = SelectorMemory()
    scanner = PageScanner()
    course_map = CourseMap()
    run_log = RunLog()
    recovery = RecoveryManager(tracker, max_rounds=settings.max_recovery_rounds)

    logger.info(f"Run log: {run_log.path}")

    success = False

    for attempt in range(1, settings.max_run_attempts + 1):
        logger.info(f"Run attempt {attempt}/{settings.max_run_attempts}")
        run_log.event("attempt_started", attempt=attempt)
        started_at = time.time()

        manager = BrowserManager()
        try:
            with manager:
                success = run_attempt(
                    manager, tracker, quiz_solver, memory, recovery, scanner, course_map, run_log
                )
        except Exception as e:
            logger.exception(f"Unexpected error during attempt {attempt}: {e}")
            run_log.event("attempt_crashed", attempt=attempt, error=str(e))
            success = False

        run_log.event(
            "attempt_finished",
            attempt=attempt,
            success=success,
            duration_s=round(time.time() - started_at, 1),
        )

        if success:
            stats = tracker.get_stats()
            logger.info(f"Final stats: {stats}")
            run_log.event("finished", status="completed", stats=stats)
            return 0

        logger.warning(f"Attempt {attempt} did not complete the course")

        if attempt < settings.max_run_attempts:
            recovered = recovery.recover(
                "run_failed",
                [
                    ("fresh browser on next attempt (automatic)", lambda: True),
                    ("retry with the learned selectors", lambda: True),
                ],
                detail=f"attempt={attempt}",
            )
            if not recovered:
                logger.error("No recovery action left, stopping")

    stats = tracker.get_stats()
    progressed = stats["completed_units"] > 0 or stats["quizzes_solved"] > 0
    run_log.event("finished", status="incomplete", stats=stats)

    if progressed:
        logger.error("Bot stopped with saved progress - run again to resume")
        logger.info(f"Final stats: {stats}")
        return 1

    logger.error("Bot stopped after exhausting all attempts")
    return 2


if __name__ == "__main__":
    sys.exit(main())
