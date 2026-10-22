from src.bot.navigator import CourseNavigator
from src.bot.selectors import SelectorMemory


class FakeElement:
    def __init__(self, displayed: bool = True):
        self._displayed = displayed

    def is_displayed(self):
        return self._displayed

    def is_enabled(self):
        return True


class FakeDriver:
    def __init__(self, visible=None, hidden=None, url="https://x/path-player?courseid=c1&unit=u1"):
        self.visible = visible or {}
        self.hidden = hidden or {}
        self.current_url = url

    def find_elements(self, by, selector):
        elements = list(self.visible.get(selector, []))
        elements += [FakeElement(displayed=False) for _ in self.hidden.get(selector, [])]
        return elements


def make_navigator(driver, tmp_path):
    memory = SelectorMemory(storage_path=str(tmp_path / "sel.json"))
    return CourseNavigator(driver, memory=memory)


def test_session_lost_false_positives_are_gone(tmp_path):
    driver = FakeDriver(hidden={"signin-email": [1], ".login-form": [1]})
    navigator = make_navigator(driver, tmp_path)
    assert navigator._session_lost() is False


def test_session_lost_when_form_is_really_visible(tmp_path):
    driver = FakeDriver(visible={"signin-email": [FakeElement()], ".login-form": [FakeElement()]})
    navigator = make_navigator(driver, tmp_path)
    assert navigator._session_lost() is True


def test_session_lost_false_when_logged_in_marker_visible(tmp_path):
    driver = FakeDriver(
        visible={
            "signin-email": [FakeElement()],
            ".login-form": [FakeElement()],
            "a[href*='logout']": [FakeElement()],
        }
    )
    navigator = make_navigator(driver, tmp_path)
    assert navigator._session_lost() is False


def test_session_lost_no_elements(tmp_path):
    driver = FakeDriver()
    navigator = make_navigator(driver, tmp_path)
    assert navigator._session_lost() is False


def test_on_error_page_detection(tmp_path):
    driver = FakeDriver(url="https://www.datascienceacademy.com.br/error?premium-content")
    navigator = make_navigator(driver, tmp_path)
    assert navigator._on_error_page() is True

    driver.current_url = "https://www.datascienceacademy.com.br/path-player?courseid=c1&unit=u1"
    assert navigator._on_error_page() is False


def test_driver_alive_with_working_url(tmp_path):
    driver = FakeDriver()
    navigator = make_navigator(driver, tmp_path)
    assert navigator._driver_alive() is True


def test_driver_alive_false_when_browser_dead(tmp_path):
    from selenium.common.exceptions import InvalidSessionIdException

    class DeadDriver:
        @property
        def current_url(self):
            raise InvalidSessionIdException("session deleted")

    navigator = make_navigator(DeadDriver(), tmp_path)
    assert navigator._driver_alive() is False
