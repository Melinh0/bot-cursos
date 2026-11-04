from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.llm import QuizSolver
from src.utils.helpers import random_delay
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MoodleActivityHandler:
    def __init__(self, driver):
        self.driver = driver

    def handle(self, url):
        self.driver.get(url)
        random_delay(1, 2)
        if "mod/assign" in url:
            return self.handle_assign()
        if "mod/quiz" in url:
            return self.handle_quiz()
        if "mod/feedback" in url:
            return self.handle_feedback()
        if "mod/resource" in url or "mod/url" in url:
            return self.handle_resource()
        if "mod/page" in url or "mod/forum" in url:
            return self.handle_generic()
        return self.handle_generic()

    def handle_assign(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            random_delay(2, 4)
            submit = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='submit'], button[type='submit']"
            )
            if submit:
                submit[0].click()
                random_delay(2, 3)
            logger.info("Assign handled")
            return True
        except Exception:
            return False

    def handle_quiz(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            questions = self.driver.find_elements(
                By.CSS_SELECTOR, ".que, .qtext, [data-region='question']"
            )
            if not questions:
                logger.warning("No quiz questions found")
                return False
            solver = QuizSolver()
            for q in questions:
                try:
                    qtext = q.find_element(By.CSS_SELECTOR, ".qtext, .que__content").text.strip()
                    options = q.find_elements(
                        By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']"
                    )
                    opts = [opt.get_attribute("value") or "" for opt in options]
                    if qtext and opts:
                        quiz_data = {"question": qtext, "options": opts}
                        idx = solver.solve_quiz(quiz_data)
                        if idx is not None and idx < len(options):
                            options[idx].click()
                except Exception:
                    continue
            random_delay(1, 2)
            submit = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='submit'], button[type='submit'], #submitbutton"
            )
            if submit:
                submit[0].click()
                random_delay(2, 3)
            logger.info("Quiz handled with LLM")
            return True
        except Exception:
            return False

    def handle_feedback(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            solver = QuizSolver()
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
            for inp in inputs:
                try:
                    label = ""
                    parent = inp.find_element(By.XPATH, "./ancestor::div[1]")
                    labels = parent.find_elements(By.CSS_SELECTOR, "label, .fitemtitle, .form-item")
                    if labels:
                        label = labels[0].text.strip()
                    prompt_text = f"Responda de forma breve e profissional à pergunta: {label}"
                    activity_data = {"prompt": prompt_text}
                    response = solver.solve_activity(activity_data)
                    if response:
                        inp.clear()
                        inp.send_keys(response[:500])
                except Exception:
                    continue
            random_delay(1, 2)
            submit = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='submit'], button[type='submit']"
            )
            if submit:
                submit[0].click()
                random_delay(2, 3)
            logger.info("Feedback handled with LLM")
            return True
        except Exception:
            return False

    def handle_resource(self):
        random_delay(15, 25)
        logger.info("Resource viewed")
        return True

    def handle_generic(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            random_delay(3, 5)
            submit = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='submit'], button[type='submit'], a.btn"
            )
            for btn in submit:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        random_delay(2, 3)
                        break
                except Exception:
                    continue
            logger.info("Generic activity handled")
            return True
        except Exception:
            return False
