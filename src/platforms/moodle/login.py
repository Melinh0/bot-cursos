from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

FILL_LOGIN_JS = """
var user = arguments[0];
var pass = arguments[1];
var u = document.getElementById('username');
var p = document.getElementById('password');
if (!u || !p) { return false; }
function setVal(el, v) {
    el.value = v;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
}
setVal(u, user);
setVal(p, pass);
return true;
"""

SUBMIT_LOGIN_JS = """
var btn = document.getElementById('loginbtn');
if (!btn) { return false; }
btn.click();
return true;
"""


class MoodleLogin:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = getattr(settings, "moodle_base_url", "https://ead.hardware.org.br")
        self.username = getattr(settings, "moodle_user", "")
        self.password = getattr(settings, "moodle_pass", "")

    def login(self):
        login_url = f"{self.base_url}/login/index.php"
        self.driver.get(login_url)
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "username")))
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "password")))
        filled = self.driver.execute_script(FILL_LOGIN_JS, self.username, self.password)
        if not filled:
            logger.error("Could not fill Moodle login fields")
            return False
        submitted = self.driver.execute_script(SUBMIT_LOGIN_JS)
        if not submitted:
            logger.error("Moodle login button not found")
            return False
        WebDriverWait(self.driver, 20).until(lambda d: "/login/" not in d.current_url)
        logger.info("Moodle login successful")
        return True
