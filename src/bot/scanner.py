import re
from collections import Counter
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.logging import get_logger

logger = get_logger(__name__)

HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
CLASS_RE = re.compile(r"""\bclass\s*=\s*["']([^"']+)["']""", re.IGNORECASE)

CATEGORY_RULES: list[tuple[str, re.Pattern]] = [
    ("player", re.compile(r"path-player|/learningpath|/learning-path|/path/|/course/view", re.I)),
    ("unit", re.compile(r"[?&]unit=", re.I)),
    ("course", re.compile(r"^/course/|/courses?/", re.I)),
    ("program", re.compile(r"^/program/", re.I)),
    ("dashboard", re.compile(r"dashboard|/my[-_]?courses|/my[-_]?learning", re.I)),
    ("signin", re.compile(r"signin|sign-in|login", re.I)),
]


class PageScanner:
    def __init__(self, storage_path: str = "data/site_map.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.site_map: dict = self._load()

    def _load(self) -> dict:
        if not self.storage_path.exists():
            return {}
        try:
            import json

            with open(self.storage_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load site map: {e}")
            return {}

    def save(self) -> None:
        try:
            import json

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.site_map, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save site map: {e}")

    @staticmethod
    def categorize(href: str) -> str:
        for name, pattern in CATEGORY_RULES:
            if pattern.search(href):
                return name
        return "other"

    def scan(self, driver: WebDriver, label: str = "") -> dict:
        try:
            html = driver.page_source or ""
        except Exception as e:
            logger.error(f"Failed to read page source: {e}")
            return {}

        hrefs = HREF_RE.findall(html)
        ids = ID_RE.findall(html)
        classes: list[str] = []
        for raw in CLASS_RE.findall(html):
            classes.extend(raw.split())

        by_category: dict[str, list[str]] = {}
        for href in hrefs:
            if href.startswith("#") or href.startswith("javascript:"):
                continue
            by_category.setdefault(self.categorize(href), []).append(href)

        unique_links = []
        seen = set()
        for category, links in by_category.items():
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append({"href": link, "category": category})

        buttons = self._collect_buttons(driver)
        dom_links = self._collect_dom_links(driver)

        report = {
            "label": label,
            "url": self._safe(driver, "current_url"),
            "title": self._safe(driver, "title"),
            "html_size": len(html),
            "counts": {
                "links": len(hrefs),
                "ids": len(ids),
                "classes": len(set(classes)),
                "buttons": len(buttons),
            },
            "categories": {name: len(links) for name, links in by_category.items()},
            "links": unique_links[:200],
            "dom_links": dom_links[:200],
            "buttons": buttons[:100],
            "ids": sorted(set(ids))[:120],
            "classes": Counter(classes).most_common(60),
        }

        self.site_map[label or report["url"]] = report
        self.save()

        logger.info(
            f"Page scan[{label or 'page'}]: {report['counts']['links']} links, "
            f"{report['counts']['buttons']} buttons, "
            f"categories={report['categories']}"
        )
        return report

    def _safe(self, driver: WebDriver, attribute: str) -> str:
        try:
            return getattr(driver, attribute) or ""
        except Exception:
            return ""

    def _collect_buttons(self, driver: WebDriver) -> list[dict]:
        buttons: list[dict] = []
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, "button, a.button, [role='button']")
        except Exception:
            return buttons

        for element in elements[:200]:
            try:
                text = (element.text or "").strip()[:80]
                button_id = element.get_attribute("id") or ""
                css_class = (element.get_attribute("class") or "")[:120]
            except Exception:
                continue

            if text or button_id:
                buttons.append({"text": text, "id": button_id, "class": css_class})

        return buttons

    def _collect_dom_links(self, driver: WebDriver) -> list[dict]:
        links: list[dict] = []
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        except Exception:
            return links

        for element in elements[:400]:
            try:
                href = element.get_attribute("href") or ""
                text = (element.text or "").strip()[:100]
            except Exception:
                continue

            if not href or href.startswith("#"):
                continue

            links.append({"href": href, "text": text, "category": self.categorize(href)})

        return links

    def find_entry_points(self, report: dict, keywords: tuple[str, ...] = ()) -> list[dict]:
        candidates = [
            link for link in report.get("dom_links", []) if link["category"] in ("player", "unit")
        ]
        candidates += [
            link
            for link in report.get("dom_links", [])
            if link["category"] in ("dashboard", "course") and link not in candidates
        ]

        if keywords:

            def score(link: dict) -> int:
                text = link.get("text", "").lower()
                href = link.get("href", "").lower()
                return sum(
                    3 if keyword in text else (1 if keyword in href else 0) for keyword in keywords
                )

            candidates.sort(key=score, reverse=True)

        return candidates

    def remembered_entry_point(self, label: str = "entry") -> str | None:
        entry = self.site_map.get(label)
        if not entry:
            return None
        points = self.find_entry_points(entry)
        return points[0]["href"] if points else None

    def suggest_css(self, report: dict, tokens: tuple[str, ...], limit: int = 3) -> list[str]:
        if not report:
            return []

        suggestions: list[str] = []
        for element_id in report.get("ids", []):
            if any(token in element_id.lower() for token in tokens):
                selector = f"#{element_id}"
                if selector not in suggestions:
                    suggestions.append(selector)

        for class_name, _count in report.get("classes", []):
            if any(token in class_name.lower() for token in tokens):
                selector = f".{class_name}"
                if selector not in suggestions:
                    suggestions.append(selector)

        return suggestions[:limit]

    def get_navigation_urls(self, report: dict) -> list[dict]:
        nav_keywords = (
            "cursosgratuitos",
            "cursos-gratuitos",
            "free-courses",
            "todoscursosdsa",
            "all-courses",
            "todos-cursos",
            "todas-formacoes",
            "all-formations",
            "todas-formacoes-dsa",
            "dashboard",
            "meus-cursos",
            "my-courses",
            "formacoesdsa",
            "programas",
            "pos-graduacao",
        )
        nav_links = []
        for link in report.get("dom_links", []):
            href = link.get("href", "").lower()
            text = link.get("text", "").lower()
            if any(kw in href or kw in text for kw in nav_keywords):
                nav_links.append(link)
        return nav_links

    def get_course_cards(self, report: dict) -> list[dict]:
        course_links = []
        for link in report.get("dom_links", []):
            href = link.get("href", "")
            if "/course/" in href or "/program/" in href:
                course_links.append(link)
        return course_links

    def get_enroll_buttons(self, report: dict) -> list[dict]:
        enroll_texts = (
            "inscrever",
            "matricular",
            "enroll",
            "registrar",
            "register",
            "começar",
            "start",
            "iniciar",
            "access",
            "acessar",
            "gratuito",
            "free",
            "cadastrar",
            "sign up",
        )
        buttons = []
        for btn in report.get("buttons", []):
            text = btn.get("text", "").lower()
            if any(t in text for t in enroll_texts):
                buttons.append(btn)
        return buttons
