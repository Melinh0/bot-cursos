from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MoodleLogin:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = getattr(settings, "moodle_base_url", "https://ead.hardware.org.br")
        self.username = getattr(settings, "moodle_user", "")
        self.password = getattr(settings, "moodle_pass", "")

    def login(self):
        login_url = f"{self.base_url}/login/index.php"
        self.driver.get(login_url)
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
        user_field = self.driver.find_element(By.ID, "username")
        pass_field = self.driver.find_element(By.ID, "password")
        user_field.clear()
        user_field.send_keys(self.username)
        pass_field.clear()
        pass_field.send_keys(self.password)
        submit = self.driver.find_element(By.ID, "loginbtn")
        submit.click()
        WebDriverWait(self.driver, 15).until(lambda d: "/login/" not in d.current_url)
        logger.info("Moodle login successful")
        return True
