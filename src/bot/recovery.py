from collections.abc import Callable

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RecoveryManager:
    def __init__(self, tracker=None, max_rounds: int = 3):
        self.tracker = tracker
        self.max_rounds = max_rounds
        self.attempts: dict[str, int] = {}
        self.recoveries: dict[str, int] = {}

    def attempt_count(self, symptom: str) -> int:
        return self.attempts.get(symptom, 0)

    def recovery_count(self, symptom: str) -> int:
        return self.recoveries.get(symptom, 0)

    def _record(self, symptom: str, action: str, success: bool, detail: str = "") -> None:
        if self.tracker is None:
            return
        try:
            self.tracker.record_event(
                "recovery",
                unit=symptom,
                detail=f"{action} -> {'ok' if success else 'falhou'} {detail}".strip(),
            )
        except Exception as e:
            logger.warning(f"Failed to record recovery event: {e}")

    def recover(
        self,
        symptom: str,
        actions: list[tuple[str, Callable[[], bool]]],
        detail: str = "",
    ) -> bool:

        self.attempts[symptom] = self.attempt_count(symptom) + 1
        logger.warning(f"Symptom '{symptom}' detected ({detail}) - starting recovery")

        for description, action in actions:
            try:
                success = bool(action())
            except Exception as e:
                logger.error(f"Recovery action '{description}' raised: {e}")
                success = False

            self._record(symptom, description, success, detail)

            if success:
                self.recoveries[symptom] = self.recovery_count(symptom) + 1
                logger.info(f"Recovery for '{symptom}' succeeded with: {description}")
                return True

            logger.warning(f"Recovery action '{description}' did not work")

        logger.error(f"Recovery for '{symptom}' exhausted all {len(actions)} actions")
        return False

    def reset(self, symptom: str) -> None:
        self.attempts[symptom] = 0
