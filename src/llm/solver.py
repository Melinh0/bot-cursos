import json
import re

from src.llm.client import LLMClient
from src.llm.prompts import (
    ACTIVITY_ANALYSIS_PROMPT,
    ACTIVITY_PROMPT,
    COURSE_REVIEW_PROMPT,
    QUIZ_PROMPT,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class QuizSolver:
    def __init__(self):
        self.client = LLMClient()

    def _parse_index(self, response: str, total: int) -> int | None:
        if not response:
            return None

        match = re.search(r"\d+", response)
        if not match:
            return None

        index = int(match.group())
        if 0 <= index < total:
            return index

        if 1 <= index <= total:
            logger.info(f"LLM answered with a 1-based index, converting {index} to {index - 1}")
            return index - 1

        logger.warning(f"LLM answered {index}, which is out of range ({total} options)")
        return None

    def solve_quiz(self, quiz_data: dict) -> int | None:
        question = quiz_data.get("question", "")
        options = quiz_data.get("options", [])

        if not question or not options:
            logger.warning("Invalid quiz data")
            return None

        options_text = "\n".join(f"{i}: {opt}" for i, opt in enumerate(options))
        prompt = QUIZ_PROMPT.format(question=question, options=options_text)

        system_messages = [
            "You are a Data Science expert. Answer with only the option index.",
            "You are a Data Science expert. Reply strictly with a single number: the index of the correct option.",
        ]

        for attempt, system_message in enumerate(system_messages):
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ]

            response = self.client.chat_completion(
                messages,
                temperature=0.0 if attempt == 0 else 0.4,
                max_tokens=16,
            )

            index = self._parse_index(response, len(options))
            if index is not None:
                logger.info(f"Quiz solved: selected option {index}")
                return index

            logger.warning(f"Invalid LLM response for quiz (attempt {attempt + 1}): {response}")

        return None

    def solve_activity(self, activity_data: dict) -> str | None:
        prompt = activity_data.get("prompt", "")

        if not prompt:
            logger.warning("Invalid activity data")
            return None

        formatted_prompt = ACTIVITY_PROMPT.format(prompt=prompt)

        messages = [
            {
                "role": "system",
                "content": "You are a Data Science expert. Provide only the code solution.",
            },
            {"role": "user", "content": formatted_prompt},
        ]

        response = self.client.chat_completion(messages, temperature=0.1, max_tokens=2048)

        if response:
            logger.info("Activity solved successfully")
            return response.strip()

        return None

    def solve_code_challenge(self, challenge: str) -> str | None:
        messages = [
            {
                "role": "system",
                "content": "Solve the coding challenge. Output only the solution code.",
            },
            {"role": "user", "content": challenge},
        ]
        return self.client.chat_completion(messages, temperature=0.1, max_tokens=2048)

    VALID_TYPES = ("quiz", "assignment", "feedback", "resource", "page", "forum", "desconhecido")
    VALID_ACTIONS = ("responder", "ler", "enviar", "marcar_concluido", "navegar")
    PLACEHOLDER_RE = re.compile(r"quiz\|assignment\|feedback\|resource\|page\|forum\|desconhecido")
    ACTION_PLACEHOLDER_RE = re.compile(r"responder\|ler\|enviar\|marcar_concluido\|navegar")

    def _parse_analysis(self, response: str | None) -> dict:
        if not response:
            return {}
        cleaned = self._strip_placeholders(response)
        parsed = self._try_json(cleaned)
        if parsed:
            return parsed
        return self._from_free_text(cleaned)

    def _strip_placeholders(self, text: str) -> str:
        text = self.PLACEHOLDER_RE.sub("desconhecido", text)
        text = self.ACTION_PLACEHOLDER_RE.sub("navegar", text)
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        return text.strip()

    def _try_json(self, text: str) -> dict | None:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                parsed["tipo"] = self._normalize(
                    parsed.get("tipo", ""), self.VALID_TYPES, "desconhecido"
                )
                parsed["acao"] = self._normalize(
                    parsed.get("acao", ""), self.VALID_ACTIONS, "navegar"
                )
                return parsed
        except json.JSONDecodeError:
            pass
        return None

    def _from_free_text(self, text: str) -> dict:
        tipo = "desconhecido"
        acao = "navegar"
        for t in self.VALID_TYPES:
            if t in text.lower():
                tipo = t
                break
        for a in self.VALID_ACTIONS:
            if a in text.lower():
                acao = a
                break
        motivo = self._clean_motivo(text)
        return {"tipo": tipo, "acao": acao, "motivo": motivo}

    def _normalize(self, value: str, valid: tuple[str, ...], default: str) -> str:
        if not value:
            return default
        value = str(value).strip().lower()
        for v in valid:
            if v in value:
                return v
        return default

    def _clean_motivo(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        return text[:300]

    def analyze_activity(self, title: str, content: str) -> dict:
        prompt = ACTIVITY_ANALYSIS_PROMPT.format(title=title, content=content[:3500])
        messages = [
            {
                "role": "system",
                "content": (
                    "Você analisa páginas de atividades do Moodle e responde "
                    "APENAS com JSON válido, sem texto adicional."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        response = self.client.chat_completion(messages, temperature=0.0, max_tokens=400)
        return self._parse_analysis(response)

    def review_progress(self, course_title: str, activities: list[dict]) -> str | None:
        lines = []
        for activity in activities[:40]:
            status = "concluída" if activity.get("done") else "pendente"
            lines.append(
                f"- [{status}] {activity.get('title', '')} ({activity.get('type', 'atividade')})"
            )
        if not lines:
            return None
        prompt = COURSE_REVIEW_PROMPT.format(course=course_title, activities="\n".join(lines))
        messages = [
            {"role": "system", "content": "Você é um tutor objetivo. Responda em português."},
            {"role": "user", "content": prompt},
        ]
        response = self.client.chat_completion(messages, temperature=0.2, max_tokens=300)
        if response:
            return response.strip()
        return None
