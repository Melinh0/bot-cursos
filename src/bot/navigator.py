from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from src.utils.helpers import random_delay, safe_click, wait_for_element
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CourseNavigator:
    NEXT_BUTTON_CLASS = "default-course-player-nav-btn.next"
    COURSE_CONTENT_CLASS = "course-player-content"
    QUIZ_CONTAINER_CLASS = "quiz-container"
    ACTIVITY_CONTAINER_CLASS = "activity-container"

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.course_completed = False

    def navigate_to_course(self, course_url: str) -> bool:
        try:
            logger.info(f"Navigating to course: {course_url}")
            self.driver.get(course_url)
            random_delay(10, 15)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to course: {e}")
            return False

    def click_next(self) -> bool:
        try:
            next_button = wait_for_element(
                self.driver,
                (By.CLASS_NAME, self.NEXT_BUTTON_CLASS),
                timeout=20,
                condition=EC.element_to_be_clickable,
            )

            if not next_button:
                logger.warning("Next button not found")
                return False

            if safe_click(self.driver, next_button):
                logger.info("Clicked 'Next' button")
                random_delay(5, 10)
                return True

            return False

        except Exception as e:
            logger.error(f"Error clicking next: {e}")
            return False

    def check_for_quiz(self) -> dict | None:
        try:
            quiz_container = wait_for_element(
                self.driver,
                (By.CLASS_NAME, self.QUIZ_CONTAINER_CLASS),
                timeout=5,
            )
            if quiz_container:
                return self.extract_quiz_data(quiz_container)
        except TimeoutException:
            pass
        return None

    def check_for_activity(self) -> dict | None:
        try:
            activity_container = wait_for_element(
                self.driver,
                (By.CLASS_NAME, self.ACTIVITY_CONTAINER_CLASS),
                timeout=5,
            )
            if activity_container:
                return self.extract_activity_data(activity_container)
        except TimeoutException:
            pass
        return None

    def extract_quiz_data(self, container) -> dict:
        try:
            question_elem = container.find_element(By.CLASS_NAME, "quiz-question")
            question = question_elem.text.strip()

            options = []
            option_elements = container.find_elements(By.CLASS_NAME, "quiz-option")
            for opt in option_elements:
                options.append(opt.text.strip())

            return {
                "type": "quiz",
                "question": question,
                "options": options,
                "container": container,
            }
        except NoSuchElementException:
            return {"type": "quiz", "question": "", "options": [], "container": container}

    def extract_activity_data(self, container) -> dict:
        try:
            prompt_elem = container.find_element(By.CLASS_NAME, "activity-prompt")
            prompt = prompt_elem.text.strip()

            return {
                "type": "activity",
                "prompt": prompt,
                "container": container,
            }
        except NoSuchElementException:
            return {"type": "activity", "prompt": "", "container": container}

    def submit_quiz_answer(self, container, answer_index: int) -> bool:
        try:
            options = container.find_elements(By.CLASS_NAME, "quiz-option")
            if 0 <= answer_index < len(options):
                safe_click(self.driver, options[answer_index])
                random_delay(1, 2)

                submit_btn = container.find_element(By.CLASS_NAME, "quiz-submit")
                safe_click(self.driver, submit_btn)
                random_delay(2, 3)
                logger.info(f"Submitted quiz answer: index {answer_index}")
                return True
        except Exception as e:
            logger.error(f"Failed to submit quiz answer: {e}")
        return False

    def submit_activity_response(self, container, response: str) -> bool:
        try:
            textarea = container.find_element(By.TAG_NAME, "textarea")
            textarea.clear()
            textarea.send_keys(response)
            random_delay(1, 2)

            submit_btn = container.find_element(By.CLASS_NAME, "activity-submit")
            safe_click(self.driver, submit_btn)
            random_delay(2, 3)
            logger.info("Submitted activity response")
            return True
        except Exception as e:
            logger.error(f"Failed to submit activity: {e}")
        return False

    def is_course_completed(self) -> bool:
        try:
            completion_indicators = [
                "course-completed",
                "congratulations",
                "certificado",
                "parabéns",
            ]
            page_source = self.driver.page_source.lower()
            return any(indicator in page_source for indicator in completion_indicators)
        except Exception:
            return False

    def run_course_loop(self, llm_solver) -> None:
        logger.info("Starting course navigation loop")

        while not self.course_completed:
            if self.is_course_completed():
                logger.info("Course completed!")
                self.course_completed = True
                break

            quiz_data = self.check_for_quiz()
            if quiz_data:
                logger.info(f"Quiz detected: {quiz_data['question'][:50]}...")
                answer = llm_solver.solve_quiz(quiz_data)
                if answer is not None:
                    self.submit_quiz_answer(quiz_data["container"], answer)
                continue

            activity_data = self.check_for_activity()
            if activity_data:
                logger.info(f"Activity detected: {activity_data['prompt'][:50]}...")
                response = llm_solver.solve_activity(activity_data)
                if response:
                    self.submit_activity_response(activity_data["container"], response)
                continue

            if not self.click_next():
                logger.warning("Could not click next, checking completion")
                if self.is_course_completed():
                    self.course_completed = True
                    break
                random_delay(5, 10)
