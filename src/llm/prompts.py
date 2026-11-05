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

ACTIVITY_ANALYSIS_PROMPT = """Analise a página de atividade de um curso Moodle exibida abaixo.

TÍTULO E URL:
{title}

CONTEÚDO DA PÁGINA:
{content}

Tarefa: determine o que esta atividade exige do aluno para ser concluída e qual ação o bot deve executar.

Responda APENAS com um JSON válido, sem texto fora do JSON:
{{"tipo": "quiz|assignment|feedback|resource|page|forum|desconhecido", "acao": "responder|ler|enviar|marcar_concluido|navegar", "motivo": "explicação curta em português do que a página pede e como concluir", "resposta": "texto pronto para colar em campo aberto da atividade, ou string vazia se não houver"}}

Se a página contiver perguntas, inclua no motivo a resposta correta de cada uma."""

COURSE_REVIEW_PROMPT = """Você é um tutor que avalia o andamento de um aluno em um curso online.

Curso: {course}

Atividades detectadas na página do curso:
{activities}

Escreva em português, em até 4 linhas: quantas atividades já estão concluídas, quais ainda faltam e o que o aluno precisa fazer para chegar a 100% do curso. Seja específico citando os títulos das atividades pendentes."""
