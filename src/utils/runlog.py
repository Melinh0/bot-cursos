import json
from datetime import datetime
from pathlib import Path

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RunLog:
    def __init__(self, base_dir: str = "data/runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"

    def event(self, kind: str, **fields) -> None:
        record = {"ts": datetime.now().isoformat(timespec="seconds"), "event": kind, **fields}
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"RunLog write failed: {e}")


class NullRunLog:
    path = None

    def event(self, kind: str, **fields) -> None:
        return
