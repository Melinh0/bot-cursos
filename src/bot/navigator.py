import time
from urllib.parse import parse_qs, urlparse

from selenium.common.exceptions import (
    InvalidSessionIdException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from src.bot.recovery import RecoveryManager
from src.bot.selectors import SelectorMemory
from src.config.settings import settings
from src.courses.course_map import CourseMap, extract_course_id
from src.utils.helpers import (
    click_element,
    find_first,
    is_visible,
    js_any_visible,
    js_click_first,
    js_match_selector,
    locators_to_css,
    random_delay,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

ERROR_URL_MARKERS = ("/error", "premium-content", "not-found")

COMPLETION_INDICATORS = (
    "100% concluído",
    "100% concluido",
    "curso concluído",
    "curso concluido",
    "concluído com sucesso",
    "concluido com sucesso",
    "course-completed",
    "congratulations",
)


class CourseNavigator:
    def __init__(
        self,
        driver: WebDriver,
        memory: SelectorMemory | None = None,
        recovery: RecoveryManager | None = None,
        relogin=None,
        scanner=None,
        restart_browser=None,
        course_map: CourseMap | None = None,
        run_log=None,
    ):
        self.driver = driver
        self.memory = memory or SelectorMemory()
        self.recovery = recovery or RecoveryManager()
        self.relogin = relogin
        self.restart_browser = restart_browser
        self.scanner = scanner
        self.course_map = course_map
        self.run_log = run_log
        self.report: dict = {}
        self.course_completed = False
        self.current_unit = ""
        self.stuck_count = 0
        self.visited_units: list[str] = []
        self.consecutive_errors = 0
        self.wrong_page_count = 0

    def _log_event(self, kind: str, **fields) -> None:
        if self.run_log is not None:
            self.run_log.event(kind, **fields)

    def scan_page(self, label: str) -> dict:

        if self.scanner is None:
            return {}
        try:
            self.report = self.scanner.scan(self.driver, label)
        except Exception as e:
            logger.warning(f"Page scan failed: {e}")
            self.report = {}
        return self.report

    def _suggest(self, tokens: tuple[str, ...]) -> list[tuple]:
        if self.scanner is None or not self.report:
            return []
        suggestions = self.scanner.suggest_css(self.report, tokens)
        return [("css selector", suggestion) for suggestion in suggestions]

    def _locators(self, name: str, tokens: tuple[str, ...] = ()) -> list[tuple]:
        locators = self.memory.locators(name)
        if tokens:
            for suggestion in self._suggest(tokens):
                if suggestion not in locators:
                    locators.append(suggestion)
        return locators

    def get_current_unit(self) -> str:
        try:
            query = parse_qs(urlparse(self.driver.current_url).query)
            return query.get("unit", [""])[0]
        except Exception:
            return ""

    def _on_error_page(self) -> bool:
        try:
            url = (self.driver.current_url or "").lower()
        except Exception:
            return False
        return any(marker in url for marker in ERROR_URL_MARKERS)

    def _driver_alive(self) -> bool:
        try:
            _ = self.driver.current_url
            return True
        except (InvalidSessionIdException, WebDriverException):
            return False
        except Exception:
            return True

    def _logged_in(self) -> bool:
        result = js_any_visible(self.driver, locators_to_css(self.memory.locators("logged_in")))
        if result is not None:
            return result
        for selector in self.memory.locators("logged_in"):
            try:
                for element in self.driver.find_elements(*selector):
                    if is_visible(element):
                        return True
            except Exception:
                continue
        return False

    def navigate_to_course(self, course_url: str) -> bool:
        try:
            logger.info(f"Navigating to course: {course_url}")
            self.driver.get(course_url)
            random_delay(1.5, 2.5)

            if self._on_error_page():
                logger.error(f"Course URL redirected to an error page: {self.driver.current_url}")
                return False

            if (
                "/course/" in self.driver.current_url
                and "path-player" not in self.driver.current_url
            ):
                logger.info("On course landing page, looking for 'Continuar' to enter player...")
                if self._enter_course_player():
                    logger.info("Entered course player successfully")
                else:
                    logger.warning("Could not find 'Continuar' button on course landing page")

            return True
        except Exception as e:
            logger.error(f"Failed to navigate to course: {e}")
            return False

    def build_course_map(self, course_url: str, title: str = "") -> str:

        course_id = extract_course_id(course_url) or extract_course_id(self.driver.current_url)
        if not course_id or self.course_map is None:
            return course_id
        self.course_map.build_from_driver(self.driver, course_id, title=title)
        return course_id

    def _enter_course_player(self) -> bool:

        try:
            clicked = self.driver.execute_script(
                """
                function vis(el) {
                    const st = getComputedStyle(el);
                    return st.display !== 'none' && st.visibility !== 'hidden' &&
                        (el.offsetHeight > 0 || el.getClientRects().length > 0);
                }
                const terms = ['continuar', 'retomar', 'iniciar'];
                const els = document.querySelectorAll('a, button, [role="button"]');
                for (const el of els) {
                    const t = (el.textContent || '').trim().toLowerCase();
                    if (!terms.some(w => t.includes(w))) continue;
                    if (!vis(el)) continue;
                    el.click();
                    return true;
                }
                const link = document.querySelector("a[href*='path-player'], a[href*='unit=']");
                if (link && vis(link)) { link.click(); return true; }
                return false;
                """
            )
            if clicked:
                random_delay(1, 2)
                return "path-player" in self.driver.current_url

            return False
        except Exception as e:
            logger.warning(f"Failed to enter course player: {e}")
            return False

    def _click_next(self) -> bool:
        css = locators_to_css(self._locators("next_button", ("next", "proxima", "avancar")))
        clicked = js_click_first(self.driver, css)
        if clicked:
            self.memory.learn("next_button", ("css selector", clicked))
            logger.info("Clicked 'Next' button")
            random_delay(1, 2)
            return True

        button = find_first(
            self.driver,
            self._locators("next_button", ("next", "proxima", "avancar")),
            timeout=8,
            condition=EC.presence_of_element_located,
        )

        if button is None:
            logger.warning("'Next' button not found, rescanning the page HTML to learn the markup")
            self.scan_page("course_player")
            button = find_first(
                self.driver,
                self._locators("next_button", ("next", "proxima", "avancar")),
                timeout=8,
                condition=EC.presence_of_element_located,
            )

        if button is None:
            return False

        if not is_visible(button):
            logger.warning("'Next' button found but not visible, clicking via JS")
            if not click_element(self.driver, button):
                return False
        elif not click_element(self.driver, button):
            return False

        self.memory.learn_from_element("next_button", button)
        logger.info("Clicked 'Next' button")
        random_delay(1, 2)
        return True

    def click_next(self) -> bool:
        try:
            return self._click_next()
        except Exception as e:
            logger.error(f"Error clicking next: {e}")
            return False

    def check_for_quiz(self) -> dict | None:
        css = locators_to_css(self._locators("quiz_container", ("quiz", "question")))
        matched = js_match_selector(
            self.driver,
            css,
            "input[type='radio']",
            "[class*='quiz'], [class*='question'], [class*='assessment'], [id*='quiz']",
        )

        container = None
        if matched:
            try:
                container = self.driver.find_element(By.CSS_SELECTOR, matched)
            except Exception:
                container = None
        elif matched is None:
            container = find_first(
                self.driver,
                self._locators("quiz_container", ("quiz", "question")),
                timeout=2,
                condition=EC.presence_of_element_located,
            )

        if container is None:
            return None
        try:
            if container.tag_name.lower() in ("html", "body", "head"):
                return None
        except Exception:
            return None

        data = self.extract_quiz_data(container)
        if data["options"]:
            self.memory.learn_from_element("quiz_container", container)
        return data

    def check_for_activity(self) -> dict | None:
        container = self._find_activity_container()
        if container is None:
            return None

        data = self.extract_activity_data(container)
        if data["prompt"]:
            self.memory.learn_from_element("activity_container", container)
        return data

    def _find_activity_container(self):
        css = locators_to_css(self._locators("activity_container", ("activity", "exercise")))
        matched = js_match_selector(
            self.driver,
            css + [".course-player-content textarea"],
            "textarea",
            "[class*='activity'], [class*='exercise'], [class*='prompt']",
            context_visible=True,
        )

        container = None
        if matched:
            try:
                container = self.driver.find_element(By.CSS_SELECTOR, matched)
            except Exception:
                container = None
        elif matched is None:
            container = find_first(
                self.driver,
                self._locators("activity_container", ("activity", "exercise")),
                timeout=2,
                condition=EC.presence_of_element_located,
            )
            if container is None:
                try:
                    container = self.driver.find_element(
                        By.CSS_SELECTOR, ".course-player-content textarea"
                    )
                except Exception:
                    container = None

        if container is None:
            return None

        try:
            if container.tag_name.lower() == "textarea":
                container = container.find_element(By.XPATH, "./..")
            if container.tag_name.lower() in ("html", "body", "head"):
                return None
        except Exception:
            return None

        if not self._has_visible_textarea(container):
            return None
        return container

    def _has_visible_textarea(self, container) -> bool:
        try:
            return any(is_visible(ta) for ta in container.find_elements(By.TAG_NAME, "textarea"))
        except Exception:
            return False

    def extract_quiz_data(self, container) -> dict:
        try:
            question = container.text.strip()[:400] if container.text else ""
        except Exception:
            question = ""

        options: list[str] = []
        try:
            for option in container.find_elements(By.CSS_SELECTOR, ".quiz-option"):
                text = (option.text or "").strip()
                if text:
                    options.append(text)
        except Exception:
            pass

        if not options:
            options = self._extract_options_from_radios(container)

        return {
            "type": "quiz",
            "question": question,
            "options": options,
            "container": container,
        }

    def _extract_options_from_radios(self, container) -> list[str]:
        options: list[str] = []
        try:
            radios = container.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        except Exception:
            radios = []

        for radio in radios:
            label_text = ""
            try:
                label = radio.find_element(By.XPATH, "ancestor::label[1]")
                label_text = (label.text or "").strip()
            except Exception:
                try:
                    label_text = (radio.get_attribute("aria-label") or "").strip()
                except Exception:
                    label_text = ""

            if not label_text:
                try:
                    label_text = (radio.get_attribute("value") or "").strip()
                except Exception:
                    label_text = ""

            options.append(label_text or f"Opcao {len(options) + 1}")

        return options

    def extract_activity_data(self, container) -> dict:
        prompt = ""
        try:
            prompt_element = container.find_element(
                By.CSS_SELECTOR, "[class*='prompt'], [class*='question']"
            )
            prompt = (prompt_element.text or "").strip()
        except Exception:
            try:
                prompt = (container.text or "").strip()[:400]
            except Exception:
                prompt = ""

        return {
            "type": "activity",
            "prompt": prompt,
            "container": container,
        }

    def submit_quiz_answer(self, container, answer_index: int) -> bool:
        try:
            options = container.find_elements(By.CSS_SELECTOR, ".quiz-option")
            if not options:
                options = container.find_elements(By.CSS_SELECTOR, "input[type='radio']")

            if not (0 <= answer_index < len(options)):
                logger.warning(f"Answer index {answer_index} out of range ({len(options)} options)")
                return False

            if not click_element(self.driver, options[answer_index]):
                return False
            random_delay(0.5, 1)

            submit_btn = find_first(
                self.driver,
                self._locators("quiz_submit", ("submit", "enviar", "confirmar")),
                timeout=5,
                condition=EC.presence_of_element_located,
            )

            if submit_btn is not None and click_element(self.driver, submit_btn):
                random_delay(1, 2)
                logger.info(f"Submitted quiz answer: index {answer_index}")
                return True

            logger.warning("Quiz submit button not found, falling back to 'Next'")
            return self._click_next()

        except StaleElementReferenceException:
            logger.warning("Stale element while submitting the quiz, retrying once")
            return False
        except Exception as e:
            logger.error(f"Failed to submit quiz answer: {e}")
            return False

    def submit_activity_response(self, container, response: str) -> bool:
        try:
            textarea = container.find_element(By.TAG_NAME, "textarea")
            textarea.clear()
            textarea.send_keys(response)
            random_delay(0.5, 1)

            submit_btn = find_first(
                self.driver,
                self._locators("activity_submit", ("submit", "enviar", "confirmar")),
                timeout=5,
                condition=EC.presence_of_element_located,
            )

            if submit_btn is not None and click_element(self.driver, submit_btn):
                random_delay(1, 2)
                logger.info("Submitted activity response")
                return True

            logger.warning("Activity submit button not found, falling back to 'Next'")
            return self._click_next()

        except Exception as e:
            logger.error(f"Failed to submit activity: {e}")
            return False

    def is_course_completed(self) -> bool:
        try:
            if "path-player" not in self.driver.current_url:
                return False

            page_source = self.driver.page_source.lower()
            return any(indicator in page_source for indicator in COMPLETION_INDICATORS)
        except Exception:
            return False

    def _session_lost(self) -> bool:
        try:
            state = self.driver.execute_script(
                """
                function vis(sel) {
                    let els;
                    try { els = document.querySelectorAll(sel); } catch (e) { return false; }
                    for (const el of els) {
                        const st = getComputedStyle(el);
                        if (st.display !== 'none' && st.visibility !== 'hidden' &&
                            (el.offsetHeight > 0 || el.getClientRects().length > 0)) return true;
                    }
                    return false;
                }
                const logged = arguments[0].some(vis);
                const email = vis('#signin-email');
                const form = vis('.login-form');
                return [logged, email, form];
                """,
                locators_to_css(self.memory.locators("logged_in")),
            )
            logged, email_visible, form_visible = state
            if logged:
                return False
            return bool(email_visible) and bool(form_visible)
        except Exception:
            pass

        try:
            if self._logged_in():
                return False

            email_visible = any(
                is_visible(element) for element in self.driver.find_elements(By.ID, "signin-email")
            )
            if not email_visible:
                return False

            form_visible = any(
                is_visible(element)
                for element in self.driver.find_elements(By.CSS_SELECTOR, ".login-form")
            )
            return form_visible
        except Exception:
            return False

    def _handle_stuck(self, course_url: str) -> bool:

        self.stuck_count += 1
        logger.warning(f"Stuck on unit '{self.current_unit}' ({self.stuck_count}x)")
        self._log_event("stuck", unit=self.current_unit, count=self.stuck_count)

        actions = [
            ("reload page", lambda: self._reload()),
            ("re-login", self._relogin_action()),
            ("restart browser and re-login", self._restart_action()),
            ("navigate to course url", lambda: self.navigate_to_course(course_url)),
        ]

        return self.recovery.recover(
            "stuck_unit",
            actions,
            detail=f"unit={self.current_unit} stuck={self.stuck_count}",
        )

    def _relogin_action(self):
        if self.relogin is None:
            return lambda: False

        def _do_relogin() -> bool:
            logger.info("Attempting to re-login during recovery")
            try:
                return bool(self.relogin())
            except Exception as e:
                logger.error(f"Re-login failed: {e}")
                return False

        return _do_relogin

    def _restart_action(self):

        def _do_restart() -> bool:
            if self.restart_browser is None:
                logger.error("No browser restart handler configured")
                return False
            try:
                new_driver = self.restart_browser()
            except Exception as e:
                logger.error(f"Browser restart failed: {e}")
                return False
            if new_driver is None:
                return False
            self.driver = new_driver
            logger.info("Browser restarted, logging in again")
            if self.relogin is not None:
                try:
                    if not self.relogin():
                        logger.error("Re-login after browser restart failed")
                        return False
                except Exception as e:
                    logger.error(f"Re-login after restart raised: {e}")
                    return False
            return True

        return _do_restart

    def _reload(self) -> bool:
        try:
            self.driver.refresh()
            random_delay(1.5, 3)
            return True
        except Exception as e:
            logger.error(f"Failed to reload the page: {e}")
            return False

    def _skip_unit(self, unit: str, course_id: str, progress_tracker=None) -> None:
        if unit and course_id and self.course_map is not None:
            self.course_map.mark_skipped(course_id, unit)
        if progress_tracker:
            progress_tracker.record_event("unit_skipped", unit=unit)
        self._log_event("unit_skipped", unit=unit)

    def _mark_unit_done(
        self, unit: str, course_id: str, course_url: str, progress_tracker=None
    ) -> None:
        if unit and course_id and self.course_map is not None:
            self.course_map.mark_done(course_id, unit)
        if progress_tracker:
            progress_tracker.update_course_progress(course_url, unit, completed=True)
        self._log_event("unit_done", unit=unit)

    def _goto_next_pending(self, course_id: str) -> bool:
        if not (course_id and self.course_map is not None):
            return False
        next_unit = self.course_map.next_pending(course_id)
        if not next_unit:
            return False
        logger.info(f"Navigating to next pending unit: {next_unit['id']}")
        try:
            self.driver.get(next_unit["url"])
            random_delay(1, 2)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to next unit: {e}")
            return False

    def _handle_video(self) -> None:

        try:
            videos = self.driver.find_elements(By.CSS_SELECTOR, "video")
        except Exception:
            return
        for video in videos:
            try:
                if not video.is_displayed():
                    continue
                self.driver.execute_script(
                    """
                    const v = arguments[0];
                    if (v.duration && isFinite(v.duration) && v.currentTime < v.duration - 1) {
                        v.currentTime = v.duration - 0.5;
                        const p = v.play();
                        if (p && p.catch) { p.catch(() => {}); }
                    }
                    """,
                    video,
                )
                logger.info("Video found: seeked to the end")
                self._log_event("video_seeked")
                random_delay(1, 2)
                complete = find_first(
                    self.driver,
                    self.memory.locators("complete_button"),
                    timeout=3,
                    condition=EC.presence_of_element_located,
                )
                if complete is not None and is_visible(complete):
                    click_element(self.driver, complete)
                    logger.info("Clicked 'complete' button after video")
                    random_delay(0.5, 1)
                return
            except Exception as e:
                logger.debug(f"Video handling failed: {e}")
                return

    def run_course_loop(
        self,
        llm_solver,
        progress_tracker=None,
        course_url: str = "",
        course_id: str = "",
        max_units: int | None = None,
    ) -> dict:

        logger.info("Starting course navigation loop")
        if max_units is None:
            max_units = settings.max_units_per_run or 0
        processed = 0
        skipped = 0
        summary = {"completed": False, "processed": 0, "skipped": 0}

        if not course_id and self.course_map is not None:
            course_id = extract_course_id(course_url) or extract_course_id(self.driver.current_url)

        if "/course/" in self.driver.current_url and "path-player" not in self.driver.current_url:
            logger.info("Starting on course landing page, attempting to enter player...")
            if not self._enter_course_player():
                logger.warning("Could not enter player from landing page, continuing anyway")

        unit_deadline = time.time() + settings.unit_timeout_seconds

        while True:
            if not self._driver_alive():
                logger.error("Browser session is dead, attempting recovery")
                self._log_event("browser_dead")
                if not self.recovery.recover(
                    "browser_dead",
                    [("restart browser and re-login", self._restart_action())],
                    detail=f"unit={self.current_unit}",
                ):
                    logger.error("Could not recover the browser, aborting the loop")
                    break
                if course_url and not self.navigate_to_course(course_url):
                    break
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            if (
                "/course/" in self.driver.current_url
                and "path-player" not in self.driver.current_url
            ):
                logger.info("Detected course landing page, re-entering player...")
                if not self._enter_course_player():
                    logger.warning("Failed to re-enter player, trying to navigate to course URL")
                    self.navigate_to_course(course_url)
                continue

            map_complete = (
                course_id
                and self.course_map is not None
                and self.course_map.is_complete(course_id)
                and self.course_map.is_enumerated(course_id)
            )
            if self.is_course_completed() or map_complete:
                logger.info("Course completed!")
                self.course_completed = True
                summary["completed"] = True
                self._log_event("course_completed")
                break

            if self._on_error_page():
                self.consecutive_errors += 1
                logger.error(
                    f"Landed on an error page ({self.driver.current_url}), "
                    f"consecutive={self.consecutive_errors}"
                )
                self._log_event("error_page", url=self.driver.current_url)
                if self.consecutive_errors >= 3:
                    logger.error("Too many consecutive error pages, aborting the loop")
                    break
                current = self.get_current_unit()
                self._skip_unit(current, course_id, progress_tracker)
                skipped += 1
                if not self._goto_next_pending(course_id):
                    break
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            self.consecutive_errors = 0

            if "path-player" not in self.driver.current_url and not self._session_lost():
                self.wrong_page_count += 1
                logger.warning(
                    f"Off the course player ({self.driver.current_url}), "
                    f"recovery {self.wrong_page_count}/3"
                )
                self._log_event(
                    "wrong_page",
                    url=self.driver.current_url,
                    count=self.wrong_page_count,
                )
                if self.wrong_page_count > 3:
                    logger.error("Too many off-player pages, aborting the loop")
                    break
                navigated = self._goto_next_pending(course_id)
                if not navigated and course_url:
                    navigated = self.navigate_to_course(course_url)
                if not navigated:
                    logger.error("Could not get back to the course player, aborting the loop")
                    break
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue
            self.wrong_page_count = 0

            unit = self.get_current_unit()
            if unit and unit != self.current_unit:
                if self.current_unit:
                    logger.info(
                        f"[{self.course_map.progress_label(course_id) if self.course_map and course_id else '?'}]"
                        f" unit '{self.current_unit}' -> '{unit}'"
                    )
                self.current_unit = unit
                self.stuck_count = 0
                self.visited_units.append(unit)
                if course_id and self.course_map is not None:
                    self.course_map.ensure_unit(course_id, unit, url=self.driver.current_url)
                unit_deadline = time.time() + settings.unit_timeout_seconds

            if max_units and processed >= max_units:
                logger.info(f"Reached the limit of {max_units} units for this run")
                self._log_event("unit_limit_reached", processed=processed)
                break

            if self._session_lost():
                logger.warning("Session lost, trying to log in again")
                self._log_event("session_lost", unit=unit)
                if not self.recovery.recover(
                    "session_lost",
                    [
                        ("re-login", self._relogin_action()),
                        ("restart browser and re-login", self._restart_action()),
                    ],
                    detail=f"unit={unit}",
                ):
                    logger.error("Could not recover the session, aborting the loop")
                    break
                self.wrong_page_count = 0
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            if time.time() > unit_deadline:
                logger.warning(
                    f"Unit '{unit}' exceeded the {settings.unit_timeout_seconds}s budget"
                )
                if self.stuck_count + 1 >= settings.max_stuck_attempts:
                    logger.warning(f"Giving up on unit '{unit}' and skipping it")
                    self._skip_unit(unit, course_id, progress_tracker)
                    skipped += 1
                    self.stuck_count = 0
                    if not self._goto_next_pending(course_id):
                        break
                    unit_deadline = time.time() + settings.unit_timeout_seconds
                    continue
                if not self._handle_stuck(course_url):
                    self._skip_unit(unit, course_id, progress_tracker)
                    skipped += 1
                    if not self._goto_next_pending(course_id):
                        break
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            self._handle_video()

            quiz_data = self.check_for_quiz()
            if quiz_data and quiz_data["options"]:
                logger.info(f"Quiz detected: {quiz_data['question'][:80]}...")
                answer = llm_solver.solve_quiz(quiz_data)
                if answer is None:
                    logger.warning("LLM could not solve the quiz, using heuristic fallback")
                    answer = self._heuristic_answer(quiz_data)
                if answer is not None:
                    submitted = self.submit_quiz_answer(quiz_data["container"], answer)
                    if submitted and progress_tracker:
                        progress_tracker.increment_quiz_count(
                            unit=unit,
                            detail=quiz_data["question"][:120],
                        )
                    if submitted:
                        self._log_event("quiz_solved", unit=unit)
                processed += 1
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            activity_data = self.check_for_activity()
            if activity_data and activity_data["prompt"]:
                logger.info(f"Activity detected: {activity_data['prompt'][:80]}...")
                response = llm_solver.solve_activity(activity_data)
                if response is None:
                    logger.warning("LLM could not solve the activity, using generic fallback")
                    response = "# Resposta automatica do bot DSA"
                submitted = self.submit_activity_response(activity_data["container"], response)
                if submitted and progress_tracker:
                    progress_tracker.increment_activity_count(
                        unit=unit,
                        detail=activity_data["prompt"][:120],
                    )
                if submitted:
                    self._log_event("activity_done", unit=unit)
                processed += 1
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            if self.click_next():
                if unit:
                    self._mark_unit_done(unit, course_id, course_url, progress_tracker)
                processed += 1
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            if self.is_course_completed():
                self.course_completed = True
                summary["completed"] = True
                break

            if not self._handle_stuck(course_url):
                logger.error("Unable to move forward, skipping the unit")
                self._skip_unit(unit, course_id, progress_tracker)
                skipped += 1
                self.stuck_count = 0
                if not self._goto_next_pending(course_id):
                    logger.error("No more pending units, aborting the loop")
                    break
                unit_deadline = time.time() + settings.unit_timeout_seconds
                continue

            random_delay(0.5, 1.2)

        summary["processed"] = processed
        summary["skipped"] = skipped
        logger.info(
            f"Course loop finished: completed={summary['completed']} "
            f"processed={processed} skipped={skipped}"
        )
        return summary

    def _heuristic_answer(self, quiz_data: dict) -> int:

        options = quiz_data.get("options", [])
        if not options:
            return None

        keywords = ("correta", "correct", "verdadeiro", "true", "sim", "yes")
        for index, option in enumerate(options):
            if any(keyword in option.lower() for keyword in keywords):
                return index

        return 0
