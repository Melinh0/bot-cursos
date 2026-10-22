from selenium.webdriver.remote.webdriver import WebDriver

from src.bot.selectors import SelectorMemory
from src.config.settings import settings
from src.utils.helpers import (
    js_any_visible,
    locators_to_css,
    random_delay,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

JS_LOGIN_STATE = """
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
function textOf(sels) {
    for (const sel of sels) {
        let els;
        try { els = document.querySelectorAll(sel); } catch (e) { continue; }
        for (const el of els) {
            const t = (el.textContent || '').trim();
            if (t) return t;
        }
    }
    return '';
}
const loggedIn = arguments[0].some(vis);
const formVisible = arguments[1].some(vis);
const error = textOf(arguments[2]);
return [loggedIn, formVisible, error];
"""


class LoginHandler:
    LOGIN_URL = "https://www.datascienceacademy.com.br/"

    def __init__(self, driver: WebDriver, memory: SelectorMemory | None = None):
        self.driver = driver
        self.memory = memory or SelectorMemory()
        self.last_error = ""

    def _locators(self, name: str) -> list[tuple]:
        return self.memory.locators(name)

    def _login_state(self) -> tuple[bool, bool, str]:
        try:
            logged, form_visible, error = self.driver.execute_script(
                JS_LOGIN_STATE,
                locators_to_css(self._locators("logged_in")),
                locators_to_css(self._locators("email_input")),
                locators_to_css(self._locators("signin_error")),
            )
            return bool(logged), bool(form_visible), (error or "").strip()
        except Exception as e:
            logger.debug(f"JS login state failed: {e}")
            return False, False, ""

    def is_logged_in(self) -> bool:
        result = js_any_visible(self.driver, locators_to_css(self._locators("logged_in")))
        if result is not None:
            return result
        for selector in self._locators("logged_in"):
            elements = self.driver.find_elements(*selector)
            if any(el.is_displayed() for el in elements):
                return True
        return False

    def _open_login_form(self) -> bool:
        opened = self.driver.execute_script(
            """
            var form = document.querySelector('.login-form');
            if (!form) {
                form = document.querySelector('[class*="login-form"], [class*="signin-form"]');
            }
            if (!form) { return false; }
            form.style.display = 'flex';
            form.style.visibility = 'visible';
            form.style.opacity = '1';
            form.style.zIndex = '99999';
            return true;
            """
        )
        if opened:
            return True
        logger.warning("Could not force the sign-in form via JS")
        return False

    def _fill_credentials(self) -> bool:
        filled = self.driver.execute_script(
            """
            var form = document.querySelector('.login-form') ||
                       document.querySelector('[class*="login-form"]') ||
                       document;
            var email = form.querySelector('#signin-email') ||
                        form.querySelector('input[name="email"]') ||
                        form.querySelector('input[type="email"]');
            var pass = form.querySelector('#signin-password') ||
                       form.querySelector('input[name="password"]') ||
                       form.querySelector('input[type="password"]');
            if (!email || !pass) { return false; }
            function setVal(el, v) {
                var proto = (el.tagName === 'TEXTAREA')
                    ? HTMLTextAreaElement.prototype
                    : HTMLInputElement.prototype;
                var desc = Object.getOwnPropertyDescriptor(proto, 'value');
                if (desc && desc.set) { desc.set.call(el, v); }
                else { el.value = v; }
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }
            setVal(email, arguments[0]);
            setVal(pass, arguments[1]);
            return true;
            """,
            settings.dsa_email,
            settings.dsa_password,
        )
        if not filled:
            logger.error("Login form fields not found")
            return False
        return True

    def _submit(self) -> bool:
        submitted = self.driver.execute_script(
            """
            var form = document.querySelector('.login-form') ||
                       document.querySelector('[class*="login-form"]') ||
                       document;
            var btn = form.querySelector('#submitLogin') ||
                      form.querySelector('button[type="submit"]') ||
                      form.querySelector('input[type="submit"]') ||
                      document.querySelector('#submitLogin');
            if (!btn) { return false; }
            btn.click();
            return true;
            """
        )
        if not submitted:
            logger.error("Login submit button not found")
            return False
        random_delay(0.5, 1.0)
        return True

    def login(self) -> bool:
        self.last_error = ""

        try:
            logger.info("Accessing login page")
            self.driver.get(self.LOGIN_URL)
            random_delay(1, 2)

            if self.is_logged_in():
                logger.info("Already logged in, skipping login form")
                return True

            for attempt in range(6):
                self._open_login_form()
                if self._fill_credentials():
                    break
                logger.info(f"Login form not ready yet (attempt {attempt + 1}/6)")
                random_delay(1, 2)
            else:
                logger.error("Could not fill the sign-in form via JS")
                return False

            if not self._submit():
                return False

            for _ in range(10):
                random_delay(0.5, 1.0)
                logged, form_visible, error = self._login_state()
                if logged:
                    logger.info("Login confirmed by positive marker (user menu/profile visible)")
                    return True

                if not form_visible:
                    logger.info("Sign-in form disappeared, double-checking login state...")
                    random_delay(1, 2)
                    logged, form_visible, error = self._login_state()
                    if logged:
                        logger.info("Login confirmed after form disappeared")
                        return True
                    if not form_visible:
                        logger.warning(
                            "Sign-in form is gone but no logged-in marker found - "
                            "assuming login succeeded (will be re-checked by the loop)"
                        )
                        return True

                if error:
                    self.last_error = error
                    logger.error(f"Login rejected by the platform: {error}")
                    return False

            self.last_error = "Session was not established after submitting the form"
            logger.error(self.last_error)
            return False

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Login failed: {e}")
            return False
