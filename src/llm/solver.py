from src.llm.client import LLMClient
from src.llm.prompts import ACTIVITY_PROMPT, QUIZ_PROMPT
from src.utils.logging import get_logger

logger = get_logger(__name__)


class QuizSolver:
    def __init__(self):
        self.client = LLMClient()

    def solve_quiz(self, quiz_data: dict) -> int | None:
        question = quiz_data.get("question", "")
        options = quiz_data.get("options", [])

        if not question or not options:
            logger.warning("Invalid quiz data")
            return None

        options_text = "\n".join(f"{i}: {opt}" for i, opt in enumerate(options))
        prompt = QUIZ_PROMPT.format(question=question, options=options_text)

        messages = [
            {"role": "system", "content": "You are a Data Science expert. Answer with only the option index."},
            {"role": "user", "content": prompt},
        ]

        response = self.client.chat_completion(messages, temperature=0.0, max_tokens=10)

        if response:
            try:
                answer_index = int(response.strip())
                if 0 <= answer_index < len(options):
                    logger.info(f"Quiz solved: selected option {answer_index}")
                    return answer_index
            except ValueError:
                logger.warning(f"Invalid LLM response for quiz: {response}")

        return None

    def solve_activity(self, activity_data: dict) -> str | None:
        prompt = activity_data.get("prompt", "")

        if not prompt:
            logger.warning("Invalid activity data")
            return None

        formatted_prompt = ACTIVITY_PROMPT.format(prompt=prompt)

        messages = [
            {"role": "system", "content": "You are a Data Science expert. Provide only the code solution."},
            {"role": "user", "content": formatted_prompt},
        ]

        response = self.client.chat_completion(messages, temperature=0.1, max_tokens=2048)

        if response:
            logger.info("Activity solved successfully")
            return response.strip()

        return None

    def solve_code_challenge(self, challenge: str) -> str | None:
        messages = [
            {"role": "system", "content": "Solve the coding challenge. Output only the solution code."},
            {"role": "user", "content": challenge},
        ]
        return self.client.chat_completion(messages, temperature=0.1, max_tokens=2048)
