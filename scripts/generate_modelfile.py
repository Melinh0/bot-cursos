import json
import glob
import os
from pathlib import Path

RUNS_DIR = Path("data/runs")
MODELFILE_PATH = Path("Modelfile.moodle-activity")
OUTPUT_MODEL = "moodle-activity-assistant:0.5b"


def load_events():
    events = []
    for path in sorted(RUNS_DIR.glob("*.jsonl")):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def build_training_examples(events):
    examples = []
    for ev in events:
        if ev.get("event") != "llm_activity_analysis":
            continue
        reasoning = ev.get("reasoning", "")
        activity_type = ev.get("type", "desconhecido")
        action = ev.get("acao", "navegar")
        url = ev.get("url", "")
        if not reasoning or reasoning.startswith("```"):
            continue
        prompt = (
            f"Página Moodle: {url}\n"
            f"Conteúdo: [conteúdo extraído da página durante a execução]\n"
            f"Determine o tipo de atividade (quiz/assignment/feedback/resource/page/forum/desconhecido) "
            f"e a ação necessária (responder/ler/enviar/marcar_concluido/navegar)."
        )
        completion = json.dumps(
            {
                "tipo": activity_type,
                "acao": action,
                "motivo": reasoning,
            },
            ensure_ascii=False,
        )
        examples.append((prompt, completion))
    return examples


def generate_modelfile(examples):
    system_prompt = """Você analisa páginas de atividades do Moodle e responde APENAS com JSON válido.
Campos obrigatórios: tipo, acao, motivo.
Valores de tipo: quiz, assignment, feedback, resource, page, forum, desconhecido.
Valores de acao: responder, ler, enviar, marcar_concluido, navegar.
Responda em português, sem markdown, sem texto fora do JSON."""

    lines = []
    lines.append(f"FROM qwen2.5:0.5b")
    lines.append("")
    lines.append(f"SYSTEM \"\"\"{system_prompt}\"\"\"")
    lines.append("")
    lines.append(f"PARAMETER temperature 0.0")
    lines.append(f"PARAMETER num_predict 200")
    lines.append("")

    for i, (prompt, completion) in enumerate(examples):
        lines.append(f"MESSAGE user \"\"\"{prompt}\"\"\"")
        lines.append(f"MESSAGE assistant \"\"\"{completion}\"\"\"")
        lines.append("")

    return "\n".join(lines)


def main():
    events = load_events()
    examples = build_training_examples(events)
    modelfile = generate_modelfile(examples)
    MODELFILE_PATH.write_text(modelfile, encoding="utf-8")
    print(f"Eventos lidos: {len(events)}")
    print(f"Exemplos de treinamento gerados: {len(examples)}")
    print(f"Modelfile escrito em: {MODELFILE_PATH}")
    print("")
    print("Para criar o modelo no Ollama:")
    print(f"  ollama create {OUTPUT_MODEL} -f {MODELFILE_PATH}")
    print(f"  Depois defina LLM_MODEL={OUTPUT_MODEL} no .env")


if __name__ == "__main__":
    main()
