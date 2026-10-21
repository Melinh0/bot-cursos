import json
from datetime import datetime
from pathlib import Path

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    def __init__(self, storage_path: str = "data/progress.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.progress = self.load_progress()

    def load_progress(self) -> dict:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load progress: {e}")
        return {
            "courses": {},
            "quizzes_solved": 0,
            "activities_completed": 0,
            "last_updated": None,
        }

    def save_progress(self) -> None:
        self.progress["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    def update_course_progress(self, course_url: str, unit: str, completed: bool = True) -> None:
        if course_url not in self.progress["courses"]:
            self.progress["courses"][course_url] = {"units": {}, "completed_units": 0}

        self.progress["courses"][course_url]["units"][unit] = {
            "completed": completed,
            "timestamp": datetime.now().isoformat(),
        }

        if completed:
            self.progress["courses"][course_url]["completed_units"] = len(
                [u for u in self.progress["courses"][course_url]["units"].values() if u["completed"]]
            )

        self.save_progress()

    def increment_quiz_count(self) -> None:
        self.progress["quizzes_solved"] += 1
        self.save_progress()

    def increment_activity_count(self) -> None:
        self.progress["activities_completed"] += 1
        self.save_progress()

    def get_stats(self) -> dict:
        total_units = sum(
            len(course["units"]) for course in self.progress["courses"].values()
        )
        completed_units = sum(
            course["completed_units"] for course in self.progress["courses"].values()
        )

        return {
            "courses_enrolled": len(self.progress["courses"]),
            "total_units": total_units,
            "completed_units": completed_units,
            "completion_rate": completed_units / total_units if total_units > 0 else 0,
            "quizzes_solved": self.progress["quizzes_solved"],
            "activities_completed": self.progress["activities_completed"],
        }
