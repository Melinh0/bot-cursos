import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.logging import get_logger

logger = get_logger(__name__)

UNIT_HREF_RE = re.compile(r"[?&]unit=([^&#]+)")
COURSE_ID_RE = re.compile(r"[?&]courseid=([^&#]+)")

STATUS_PENDING = "pending"
STATUS_DONE = "done"
STATUS_SKIPPED = "skipped"


def extract_course_id(url: str) -> str:
    match = COURSE_ID_RE.search(url or "")
    return match.group(1) if match else ""


def reconcile_outline(units: list[dict], outline: list[dict]) -> tuple[list[str], list[str]]:
    if not outline or len(outline) != len(units):
        return [], []
    to_done: list[str] = []
    to_pending: list[str] = []
    for unit, row in zip(units, outline):
        platform_done = bool(row.get("done"))
        local_done = unit.get("status") == STATUS_DONE
        if platform_done and not local_done:
            to_done.append(unit["id"])
        elif not platform_done and local_done:
            to_pending.append(unit["id"])
    return to_done, to_pending


class CourseMap:
    def __init__(self, storage_path: str = "data/courses.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load course map: {e}")
        return {"courses": {}}

    def save(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save course map: {e}")

    def course(self, course_id: str) -> dict:
        return self.data["courses"].setdefault(
            course_id,
            {"title": "", "built_at": None, "enumerated": False, "units": []},
        )

    def is_enumerated(self, course_id: str) -> bool:
        return bool(self.course(course_id).get("enumerated"))

    def units(self, course_id: str) -> list[dict]:
        return self.course(course_id).get("units", [])

    def _scrape_unit_links(self, driver: WebDriver) -> list[dict]:
        scraped: list[dict] = []
        seen: set[str] = set()
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='unit=']")
        except Exception as e:
            logger.warning(f"Could not scrape unit links: {e}")
            return scraped

        for element in elements:
            try:
                href = element.get_attribute("href") or ""
            except Exception:
                continue
            match = UNIT_HREF_RE.search(href)
            if not match:
                continue
            unit_id = match.group(1)
            if unit_id in seen:
                continue
            seen.add(unit_id)
            try:
                unit_title = (element.text or "").strip()[:120]
            except Exception:
                unit_title = ""
            scraped.append({"id": unit_id, "title": unit_title, "url": href.split("#")[0]})
        return scraped

    def _scrape_sidebar(self, driver: WebDriver) -> list[dict]:
        try:
            items = driver.execute_script(
                """
                var out = [];
                var lis = document.querySelectorAll(
                    "[id^='lrn-sec-units-'] li.lrn-path-cont"
                );
                lis.forEach(li => {
                    var main = li.querySelector('.lrn-path-cont-main');
                    if (!main) { return; }
                    var nameEl = li.querySelector('.lrn-path-cont-name');
                    var circle = li.querySelector('.lrn-path-completion-circle');
                    var label = main.getAttribute('aria-label') || '';
                    var done = (circle && circle.classList.contains('completed')) ||
                               /,\\s*completed\\s*$/i.test(label);
                    var title = ((nameEl && nameEl.textContent) || label)
                        .trim().substring(0, 120);
                    out.push({index: out.length, title: title, done: !!done});
                });
                return out;
                """
            )
        except Exception as e:
            logger.warning(f"Sidebar scrape failed: {e}")
            return []
        return list(items or [])

    def _resolve_unit_ids(self, driver: WebDriver, items: list[dict]) -> dict[int, str]:
        resolved: dict[int, str] = {}
        match = UNIT_HREF_RE.search(driver.current_url or "")
        previous = match.group(1) if match else ""
        for item in items:
            try:
                clicked = driver.execute_script(
                    """
                    var lis = document.querySelectorAll(
                        "[id^='lrn-sec-units-'] li.lrn-path-cont"
                    );
                    var li = lis[arguments[0]];
                    if (!li) { return false; }
                    var main = li.querySelector('.lrn-path-cont-main') || li;
                    main.click();
                    return true;
                    """,
                    item["index"],
                )
            except Exception:
                clicked = False
            if not clicked:
                continue
            unit_id = ""
            for _ in range(12):
                time.sleep(0.2)
                current_match = UNIT_HREF_RE.search(driver.current_url or "")
                current = current_match.group(1) if current_match else ""
                if current and current != previous:
                    unit_id = current
                    previous = current
                    break
            if unit_id:
                resolved[item["index"]] = unit_id
            if len(resolved) % 10 == 0 and resolved:
                logger.info(f"Resolved {len(resolved)}/{len(items)} unit ids")
        return resolved

    def build_from_driver(self, driver: WebDriver, course_id: str, title: str = "") -> dict:
        entry = self.course(course_id)
        if title:
            entry["title"] = title
        if entry.get("enumerated") and entry.get("units"):
            logger.info("Course map already enumerated, reusing cached units")
            return entry

        existing = {u["id"]: u for u in self.units(course_id)}

        scraped_units: list[dict] = []
        sidebar = self._scrape_sidebar(driver)
        if sidebar:
            logger.info(f"Enumerating {len(sidebar)} sidebar items via clicks")
            ids = self._resolve_unit_ids(driver, sidebar)
            try:
                parsed = urlparse(driver.current_url)
                origin = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                origin = ""
            for item in sidebar:
                unit_id = ids.get(item["index"])
                if not unit_id:
                    continue
                scraped_units.append(
                    {
                        "id": unit_id,
                        "title": item["title"],
                        "url": f"{origin}/path-player?courseid={course_id}&unit={unit_id}",
                        "site_done": item["done"],
                    }
                )

        if not scraped_units:
            for unit in self._scrape_unit_links(driver):
                unit["site_done"] = False
                scraped_units.append(unit)

        if not scraped_units:
            logger.warning("No unit links found in the player sidebar")
            entry["enumerated"] = False
            self.save()
            return entry

        merged: list[dict] = []
        seen: set[str] = set()
        for unit in scraped_units:
            if unit["id"] in seen:
                continue
            seen.add(unit["id"])
            old = existing.get(unit["id"])
            if old:
                unit["status"] = old.get("status", STATUS_PENDING)
            else:
                unit["status"] = STATUS_PENDING
            if unit.pop("site_done", False):
                unit["status"] = STATUS_DONE
            merged.append(unit)

        for unit in existing.values():
            if unit["id"] not in seen:
                merged.append(unit)

        entry["units"] = merged
        entry["built_at"] = datetime.now().isoformat()
        entry["enumerated"] = True
        self.save()

        done = sum(1 for u in merged if u["status"] == STATUS_DONE)
        logger.info(f"Course map built: {len(merged)} units ({done} already done)")
        return entry

    def ensure_unit(self, course_id: str, unit_id: str, url: str = "") -> None:
        if not unit_id:
            return
        for unit in self.units(course_id):
            if unit["id"] == unit_id:
                return
        self.units(course_id).append(
            {"id": unit_id, "title": "", "url": url, "status": STATUS_PENDING}
        )
        self.save()

    def mark_done(self, course_id: str, unit_id: str) -> None:
        for unit in self.units(course_id):
            if unit["id"] == unit_id and unit["status"] != STATUS_DONE:
                unit["status"] = STATUS_DONE
                self.save()
                logger.info(f"Unit marked done: {unit_id}")
                return

    def mark_skipped(self, course_id: str, unit_id: str) -> None:
        for unit in self.units(course_id):
            if unit["id"] == unit_id and unit["status"] == STATUS_PENDING:
                unit["status"] = STATUS_SKIPPED
                self.save()
                logger.warning(f"Unit marked skipped: {unit_id}")
                return

    def mark_pending(self, course_id: str, unit_id: str) -> None:
        for unit in self.units(course_id):
            if unit["id"] == unit_id and unit["status"] != STATUS_PENDING:
                unit["status"] = STATUS_PENDING
                self.save()
                logger.info(f"Unit reverted to pending: {unit_id}")
                return

    def sync_from_outline(self, course_id: str, outline: list[dict]) -> dict:
        units = self.units(course_id)
        to_done, to_pending = reconcile_outline(units, outline)
        done_set = set(to_done)
        pending_set = set(to_pending)
        changed = False
        for unit in units:
            if unit["id"] in done_set and unit["status"] != STATUS_DONE:
                unit["status"] = STATUS_DONE
                changed = True
            elif unit["id"] in pending_set and unit["status"] != STATUS_PENDING:
                unit["status"] = STATUS_PENDING
                changed = True
        if changed:
            self.save()
        return {"marked_done": len(to_done), "reverted_pending": len(to_pending)}

    def next_pending(self, course_id: str) -> dict | None:
        for unit in self.units(course_id):
            if unit["status"] == STATUS_PENDING:
                return unit
        return None

    def is_complete(self, course_id: str) -> bool:
        units = self.units(course_id)
        if not units:
            return False
        return all(u["status"] != STATUS_PENDING for u in units)

    def counts(self, course_id: str) -> tuple[int, int]:
        units = self.units(course_id)
        total = len(units)
        resolved = sum(1 for u in units if u["status"] != STATUS_PENDING)
        return resolved, total

    def progress_label(self, course_id: str) -> str:
        resolved, total = self.counts(course_id)
        return f"{resolved}/{total}"
