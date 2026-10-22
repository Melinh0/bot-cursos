from src.courses.course_map import (
    STATUS_DONE,
    STATUS_PENDING,
    STATUS_SKIPPED,
    CourseMap,
    extract_course_id,
)


class FakeLink:
    def __init__(self, href: str, text: str = ""):
        self._href = href
        self.text = text

    def get_attribute(self, name: str):
        return self._href if name == "href" else None


class FakeDriver:
    def __init__(self, links=None):
        self._links = links or []

    def find_elements(self, by, selector):
        if "unit=" in selector:
            return list(self._links)
        return []


def test_extract_course_id():
    url = "https://www.datascienceacademy.com.br/path-player?courseid=meu-curso&unit=abc"
    assert extract_course_id(url) == "meu-curso"
    assert extract_course_id("https://example.com/") == ""
    assert extract_course_id("") == ""


def test_build_mark_and_resume(tmp_path):
    storage = str(tmp_path / "courses.json")
    course_map = CourseMap(storage)

    links = [
        FakeLink("https://x/path-player?courseid=c1&unit=u1", "Aula 1"),
        FakeLink("https://x/path-player?courseid=c1&unit=u2", "Aula 2"),
        FakeLink("https://x/path-player?courseid=c1&unit=u3", "Aula 3"),
        FakeLink("https://x/path-player?courseid=c1&unit=u1", "Aula 1"),
    ]
    driver = FakeDriver(links)
    course_map.build_from_driver(driver, "c1", title="Curso Teste")

    units = course_map.units("c1")
    assert [u["id"] for u in units] == ["u1", "u2", "u3"]
    assert all(u["status"] == STATUS_PENDING for u in units)
    assert not course_map.is_complete("c1")

    course_map.mark_done("c1", "u1")
    assert course_map.units("c1")[0]["status"] == STATUS_DONE
    assert course_map.next_pending("c1")["id"] == "u2"

    course_map2 = CourseMap(storage)
    course_map2.build_from_driver(driver, "c1")
    assert course_map2.units("c1")[0]["status"] == STATUS_DONE
    assert course_map2.next_pending("c1")["id"] == "u2"

    course_map2.mark_done("c1", "u2")
    course_map2.mark_skipped("c1", "u3")
    assert course_map2.is_complete("c1")
    assert course_map2.next_pending("c1") is None
    assert course_map2.counts("c1") == (3, 3)
    assert course_map2.progress_label("c1") == "3/3"


def test_skipped_is_not_pending(tmp_path):
    course_map = CourseMap(str(tmp_path / "courses.json"))
    driver = FakeDriver(
        [
            FakeLink("https://x/path-player?courseid=c1&unit=u1"),
            FakeLink("https://x/path-player?courseid=c1&unit=u2"),
        ]
    )
    course_map.build_from_driver(driver, "c1")
    course_map.mark_skipped("c1", "u1")
    assert course_map.units("c1")[0]["status"] == STATUS_SKIPPED
    assert course_map.next_pending("c1")["id"] == "u2"


def test_empty_course_is_not_complete(tmp_path):
    course_map = CourseMap(str(tmp_path / "courses.json"))
    assert not course_map.is_complete("missing-course")
    assert course_map.next_pending("missing-course") is None
