from src.courses.discovery import CourseDiscovery, player_url, select_lowest_progress


class FakeLink:
    def __init__(self, href: str, text: str = ""):
        self._href = href
        self.text = text

    def get_attribute(self, name: str):
        return self._href if name == "href" else None


class FakeDriver:
    def __init__(self, links=None):
        self._links = links or []
        self.visited = []

    def get(self, url):
        self.visited.append(url)

    def find_elements(self, by, selector):
        if "/course/" in selector:
            return list(self._links)
        return []


def test_player_url():
    assert (
        player_url("meu-curso")
        == "https://www.datascienceacademy.com.br/path-player?courseid=meu-curso"
    )


def test_select_lowest_progress():
    courses = [
        {"slug": "a", "progress": 92},
        {"slug": "b", "progress": 0},
        {"slug": "c", "progress": 100},
    ]
    assert select_lowest_progress(courses)["slug"] == "b"


def test_select_lowest_progress_ignores_completed():
    courses = [{"slug": "c", "progress": 100}]
    assert select_lowest_progress(courses) is None


def test_select_lowest_progress_empty():
    assert select_lowest_progress([]) is None


def test_discover_enrolled_parses_progress(tmp_path):
    base = "https://www.datascienceacademy.com.br/course/"
    links = [
        FakeLink(f"{base}engenharia", "24 h\nFundamentos de Engenharia de Dados"),
        FakeLink(f"{base}engenharia", "92% Concluído"),
        FakeLink(f"{base}power-bi", "Microsoft Power BI"),
        FakeLink(f"{base}power-bi", "0% Concluído"),
        FakeLink("https://www.datascienceacademy.com.br/course/python", "100% Concluído"),
    ]
    driver = FakeDriver(links)
    discovery = CourseDiscovery(driver)

    courses = discovery.discover_enrolled()
    by_slug = {c["slug"]: c for c in courses}

    assert by_slug["engenharia"]["progress"] == 92
    assert "Engenharia" in by_slug["engenharia"]["title"]
    assert by_slug["power-bi"]["progress"] == 0
    assert by_slug["python"]["progress"] == 100
    assert driver.visited == [CourseDiscovery.START_URL]

    target = select_lowest_progress(courses)
    assert target["slug"] == "power-bi"
