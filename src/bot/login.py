from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from src.config.settings import settings
from src.utils.helpers import random_delay, wait_for_element
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LoginHandler:
    LOGIN_URL = "https://www.datascienceacademy.com.br/"
    ENTRAR_BUTTON_ID = "menuItem_1592487994826_6"

    EMAIL_POS = (872, 456)
    PASSWORD_POS = (868, 539)
    LOGIN_BUTTON_POS = (945, 599)

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def login(self) -> bool:
        import pyautogui
        try:
            logger.info("Accessing login page")
            self.driver.get(self.LOGIN_URL)
            random_delay(2, 3)

            logger.info("Waiting for 'Entrar' button")
            entrar_button = wait_for_element(
                self.driver,
                (By.ID, self.ENTRAR_BUTTON_ID),
                timeout=20,
                condition=EC.element_to_be_clickable,
            )

            if not entrar_button:
                logger.error("'Entrar' button not found")
                return False

            entrar_button.click()
            random_delay(2, 3)

            logger.info("Filling credentials via pyautogui")
            pyautogui.click(self.EMAIL_POS)
            pyautogui.write(settings.dsa_email, interval=0.05)
            random_delay(0.5, 1.0)

            pyautogui.click(self.PASSWORD_POS)
            pyautogui.write(settings.dsa_password, interval=0.05)
            random_delay(0.5, 1.0)

            pyautogui.click(self.LOGIN_BUTTON_POS)
            random_delay(5, 7)

            logger.info("Login completed successfully")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
