from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.webdriver import WebDriver

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BrowserManager:
    def __init__(self):
        self.driver: WebDriver | None = None

    def create_driver(self) -> WebDriver:
        options = ChromeOptions()

        if settings.headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={settings.window_size}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--log-level=3")
        options.add_argument("--lang=pt-BR")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(options=options)

        try:
            self.driver.set_window_size(*settings.window_size_list)
        except Exception as e:
            logger.warning(f"Could not set the window size: {e}")

        self.driver.implicitly_wait(settings.implicit_wait)
        self.driver.set_page_load_timeout(settings.browser_timeout)

        logger.info("Browser initialized successfully")
        return self.driver

    def get_driver(self) -> WebDriver:
        if self.driver is None:
            return self.create_driver()
        return self.driver

    def restart(self) -> WebDriver:

        logger.warning("Restarting the browser")
        self.quit()
        return self.create_driver()

    def quit(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None

    def __enter__(self) -> WebDriver:
        return self.create_driver()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.quit()
