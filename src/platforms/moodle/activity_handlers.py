from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.llm import QuizSolver
from src.utils.helpers import random_delay
from src.utils.logging import get_logger

logger = get_logger(__name__)

MAX_ANALYSIS_CHARS = 3500

PAGE_TEXT_JS = """
var el = document.querySelector('#region-main') ||
         document.querySelector('[role="main"]') ||
         document.body;
return el ? el.innerText.substring(0, arguments[0]) : '';
"""


class MoodleActivityHandler:
    def __init__(self, driver, run_log=None):
        self.driver = driver
        self.run_log = run_log
        self.solver = QuizSolver()

    def handle(self, url):
        self.driver.get(url)
        random_delay(1, 2)
        analysis = self._analyze(url)
        action = (analysis.get("acao") or "").lower()
        if "mod/assign" in url:
            return self.handle_assign()
        if "mod/quiz" in url:
            return self.handle_quiz()
        if "mod/feedback" in url:
            return self.handle_feedback()
        if "mod/resource" in url or "mod/url" in url:
            return self.handle_resource()
        if action in ("responder", "enviar"):
            return self.handle_llm_form(analysis)
        return self.handle_generic()

    def _analyze(self, url):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            title = f"{self.driver.title}\n{url}"
            content = self.driver.execute_script(PAGE_TEXT_JS, MAX_ANALYSIS_CHARS) or ""
            analysis = self.solver.analyze_activity(title, content)
            if analysis:
                logger.info(
                    f"LLM analysis [{analysis.get('tipo', '?')} / "
                    f"{analysis.get('acao', '?')}]: {analysis.get('motivo', '')}"
                )
                if self.run_log:
                    self.run_log.event(
                        "llm_activity_analysis",
                        url=url,
                        type=analysis.get("tipo", ""),
                        action=analysis.get("acao", ""),
                        reasoning=analysis.get("motivo", ""),
                    )
            return analysis or {}
        except Exception:
            return {}

    def _field_label(self, element):
        try:
            parent = element.find_element(
                By.XPATH,
                "./ancestor::div[contains(@class,'fitem') or contains(@class,'form-group')][1]",
            )
        except Exception:
            try:
                parent = element.find_element(By.XPATH, "./ancestor::div[1]")
            except Exception:
                return ""
        try:
            labels = parent.find_elements(By.CSS_SELECTOR, "label, .fitemtitle")
            if labels:
                return labels[0].text.strip()
        except Exception:
            pass
        return ""

    def _fill_text_fields(self, analysis):
        filled = 0
        inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
        fallback = (analysis.get("resposta") or "").strip()
        for inp in inputs:
            try:
                if not inp.is_displayed():
                    continue
                label = self._field_label(inp)
                answer = ""
                if label:
                    answer = self.solver.solve_activity({"prompt": label}) or ""
                if not answer:
                    answer = fallback
                if not answer:
                    continue
                inp.clear()
                inp.send_keys(answer[:500])
                filled += 1
            except Exception:
                continue
        return filled

    def _click_submit(self):
        submit = self.driver.find_elements(
            By.CSS_SELECTOR, "input[type='submit'], button[type='submit'], #submitbutton"
        )
        for btn in submit:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    random_delay(2, 3)
                    return True
            except Exception:
                continue
        return False

    def _click_completion(self):
        buttons = self.driver.find_elements(
            By.CSS_SELECTOR,
            "button[data-action='completion-toggle'], "
            "input[name='submitbutton'], "
            ".completion-button, "
            "button.btn-mark-done",
        )
        for btn in buttons:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    random_delay(1, 2)
                    logger.info("Completion marked")
                    return True
            except Exception:
                continue
        return False

    def handle_llm_form(self, analysis):
        try:
            filled = self._fill_text_fields(analysis)
            random_delay(1, 2)
            self._click_submit()
            logger.info(f"LLM form handled ({filled} fields filled from LLM answers)")
            return True
        except Exception:
            return False

    def handle_assign(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            random_delay(2, 4)
            self._click_submit()
            self._click_completion()
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
            solved = 0
            for q in questions:
                try:
                    qtext = q.find_element(By.CSS_SELECTOR, ".qtext, .que__content").text.strip()
                    options = q.find_elements(
                        By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']"
                    )
                    opts = [opt.get_attribute("value") or "" for opt in options]
                    if qtext and opts:
                        quiz_data = {"question": qtext, "options": opts}
                        idx = self.solver.solve_quiz(quiz_data)
                        if idx is not None and idx < len(options):
                            options[idx].click()
                            solved += 1
                except Exception:
                    continue
            random_delay(1, 2)
            self._click_submit()
            logger.info(f"Quiz handled with LLM ({solved} questions solved)")
            return True
        except Exception:
            return False

    def handle_feedback(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            filled = self._fill_text_fields({})
            random_delay(1, 2)
            self._click_submit()
            logger.info(f"Feedback handled with LLM ({filled} fields filled)")
            return True
        except Exception:
            return False

    def handle_resource(self):
        random_delay(15, 25)
        self._click_completion()
        logger.info("Resource viewed")
        return True

    def handle_generic(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            random_delay(3, 5)
            self._click_completion()
            logger.info("Generic activity handled")
            return True
        except Exception:
            return False
