import shutil
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.webdriver import WebDriver

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

JS_ACTIVITY_HOOK = """
function __lwRecord(url, body) {
    try {
        if (String(url).indexOf('update-path-player-activity') === -1) return;
        const arr = JSON.parse(sessionStorage.getItem('__lwPosts') || '[]');
        arr.push({t: Date.now(), url: String(url), body: body ? String(body).slice(0, 1500) : ''});
        sessionStorage.setItem('__lwPosts', JSON.stringify(arr.slice(-40)));
    } catch (e) {}
}
const __lwOpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url) {
    this.__lwUrl = url;
    this.__lwMethod = method;
    return __lwOpen.apply(this, arguments);
};
const __lwSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(body) {
    try {
        if (String(this.__lwMethod || '').toUpperCase() === 'POST') __lwRecord(this.__lwUrl, body);
    } catch (e) {}
    return __lwSend.apply(this, arguments);
};
const __lwFetch = window.fetch;
window.fetch = function() {
    try {
        const u = arguments[0];
        const init = arguments[1] || {};
        if (String(init.method || 'GET').toUpperCase() === 'POST') __lwRecord(u && u.url || u, init.body);
    } catch (e) {}
    return __lwFetch.apply(this, arguments);
};
const __lwBeacon = navigator.sendBeacon;
navigator.sendBeacon = function(url, data) {
    try { __lwRecord(url, data); } catch (e) {}
    return __lwBeacon.apply(this, arguments);
};
window.__lwFind = function(unitId) {
    try {
        const arr = JSON.parse(sessionStorage.getItem('__lwPosts') || '[]');
        return arr.some(function(p) {
            return p.body.indexOf(unitId) !== -1 && p.body.indexOf('"completed":true') !== -1;
        });
    } catch (e) { return false; }
};
"""


class BrowserManager:
    def __init__(self):
        self.driver: WebDriver | None = None

    def create_driver(self) -> WebDriver:
        options = ChromeOptions()

        if settings.headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={settings.window_size}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--log-level=3")
        options.add_argument("--lang=pt-BR")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if settings.browser_persistent_profile:
            options.add_argument(f"--user-data-dir={self._prepare_profile_dir()}")

        self.driver = webdriver.Chrome(options=options)

        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument", {"source": JS_ACTIVITY_HOOK}
            )
        except Exception as e:
            logger.warning(f"Could not install activity hook: {e}")

        if not settings.headless:
            self._apply_window_layout()

        self.driver.implicitly_wait(settings.implicit_wait)
        self.driver.set_page_load_timeout(settings.browser_timeout)

        logger.info("Browser initialized successfully")
        return self.driver

    def _prepare_profile_dir(self) -> str:
        profile = Path(settings.browser_profile_dir)
        profile.mkdir(parents=True, exist_ok=True)
        for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            leftover = profile / name
            if leftover.exists() or leftover.is_symlink():
                try:
                    leftover.unlink()
                except OSError:
                    pass
        lock_dir = profile / "lockfile"
        if lock_dir.exists():
            shutil.rmtree(lock_dir, ignore_errors=True)
        return str(profile.resolve())

    def _apply_window_layout(self) -> None:
        try:
            if settings.browser_half_screen:
                width, height = self.driver.execute_script("return [screen.width, screen.height];")
                self.driver.set_window_position(0, 0)
                self.driver.set_window_size(int(width) // 2, int(height))
            else:
                self.driver.set_window_position(0, 0)
                self.driver.set_window_size(*settings.window_size_list)
        except Exception as e:
            logger.warning(f"Could not set the window layout: {e}")

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
