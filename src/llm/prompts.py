QUIZ_PROMPT = """You are an expert in Data Science and Python programming. Answer the following multiple choice question.

Question: {question}

Options:
{options}

Rules:
1. Respond ONLY with the index of the correct answer (0, 1, 2, 3, etc.)
2. Do not include any explanation, reasoning, or additional text
3. The first option is index 0, second is index 1, etc.

Answer:"""

ACTIVITY_PROMPT = """You are an expert Data Science instructor. Complete the following coding exercise/activity.

Activity Prompt:
{prompt}

Requirements:
1. Provide a complete, working Python solution
2. Include necessary imports
3. Add brief comments explaining key steps
4. Follow Python best practices and PEP 8
5. Output ONLY the code block, no markdown formatting, no explanations

Solution:"""

CODE_REVIEW_PROMPT = """Review the following code for correctness, efficiency, and best practices.

Code:
{code}

Identify any issues and suggest improvements. Be concise."""
