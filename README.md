# Bot Cursos

Automated bot for completing DataScienceAcademy (LearnWorlds) courses with
LLM-powered quiz and activity solving.

## Architecture

```
main.py                           entry point: login → select course → unit loop → exit code
  │
  ▼
src/bot                           Selenium automation
  ├── browser.py                  undetected ChromeDriver + restart
  ├── login.py                    login, session check, re-login
  ├── navigator.py                unit loop: video, quiz, activity, next
  ├── recovery.py                 escalating recovery (reload → re-login → restart)
  ├── scanner.py                  page scan, CSS selector suggestions
  └── selectors.py                selector memory (learned selectors)
  │
  ▼
src/courses                       course domain
  ├── discovery.py                enrolled course with lowest progress
  ├── course_map.py               unit map with pending/done/skipped
  ├── tracker.py                  progress stats
  └── parser.py                   HTML content extraction
  │
  ▼
src/llm                           quiz/activity solving
  ├── client.py                   OpenAI-compatible client, key/model rotation
  ├── solver.py                   LLM solving + heuristic fallback
  └── prompts.py                  prompt templates
  │
  ▼
data/                             persistent state (gitignored)
  ├── courses.json                unit map per course
  ├── progress.json               progress counters
  ├── selector_memory.json        learned selectors
  └── runs/<timestamp>.jsonl      one JSON event per step
```

Cross-cutting: `src/config` (pydantic settings from `.env`) and `src/utils`
(WebDriver/JS helpers, logging, run log).

## How it works

1. Logs in and discovers enrolled courses, picking the one with the lowest progress.
2. Builds (or reuses) the course unit map and jumps to the first pending unit.
3. Loops through units: seeks videos to the end, solves quizzes/activities with
   the LLM, clicks Next, and marks the unit done.
4. Persists state after every step, so an interrupted run resumes where it stopped.

## Features

- **Resume anytime** — unit map and progress persisted in `data/*.json`
- **Fast JS-first probes** — quiz/activity/next detection in a single
  `execute_script` roundtrip
- **Escalating recovery** — reload → re-login → browser restart, plus
  wrong-page recovery and a per-unit watchdog
- **LLM solving** — OpenAI-compatible client with optional key/model rotation
  and heuristic fallback
- **Humanized pacing** — randomized delays between actions
- **Smoke mode** — process a single unit to validate the whole pipeline quickly

## Quick Start

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Chrome/Chromium
- Ollama (local LLM) or any OpenAI-compatible API

### Local

```bash
uv venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
uv pip install pytest ruff      # dev tools

cp .env.example .env            # set DSA_EMAIL and DSA_PASSWORD

python main.py                  # full run
```

Smoke test (processes at most 1 unit per attempt):

```bash
# Linux/macOS
SMOKE_MODE=true python main.py

# Windows PowerShell
$env:SMOKE_MODE='true'; python main.py
```

### Docker

```bash
cd docker
docker-compose up -d bot

docker exec -it dsa-ollama ollama pull llama3.1
docker logs -f dsa-bot
```

## Configuration

Main variables (see `.env.example` for the full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `DSA_EMAIL` | Account email | Required |
| `DSA_PASSWORD` | Account password | Required |
| `LLM_BASE_URL` | OpenAI-compatible endpoint | `http://localhost:11434/v1` |
| `LLM_MODEL` | Model name | `llama3.1` |
| `LLM_FALLBACK_MODELS` | Comma-separated fallback models | — |
| `OLLAMA_API_KEYS` | Comma-separated API keys (rotation) | — |
| `HEADLESS` | Run browser headless | `false` |
| `AUTO_DISCOVER_COURSES` | Auto-select enrolled course | `true` |
| `MAX_UNITS_PER_RUN` | Unit cap (0 = unlimited) | `0` |
| `MAX_RUN_ATTEMPTS` | Attempts per run | `3` |
| `UNIT_TIMEOUT_SECONDS` | Per-unit watchdog | `180` |
| `SMOKE_MODE` | Process at most 1 unit | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### LLM

The bot talks to any OpenAI-compatible API (`LLM_BASE_URL`). For hosted
providers, set `OLLAMA_API_KEYS` (comma-separated) and optionally
`LLM_FALLBACK_MODELS` — keys and models rotate on 429, 401 and timeouts.
Local Ollama needs no keys.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Course completed |
| `1` | Progress saved, course incomplete — run again to resume |
| `2` | Failed after all attempts |

## Project Structure

```
bot-cursos/
├── main.py                  # Entry point
├── src/
│   ├── bot/                 # Selenium automation
│   ├── courses/             # Course domain (map, discovery, progress)
│   ├── llm/                 # LLM client, solver, prompts
│   ├── utils/               # helpers, logging, runlog
│   └── config/              # pydantic settings
├── tests/                   # pytest suite
├── docker/                  # Dockerfile + docker-compose
└── data/                    # runtime state (gitignored)
```

## Monitoring

Each run writes `data/runs/<timestamp>.jsonl` with one JSON event per step
(`login_ok`, `unit_done`, `quiz_solved`, `session_lost`, `wrong_page`, ...).

## Testing

```bash
uv run pytest
uv run ruff check main.py src tests
uv run ruff format main.py src tests
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Login fails | Check `DSA_EMAIL`/`DSA_PASSWORD` in `.env` |
| Quiz/activity not detected | Selectors are auto-learned into `data/selector_memory.json`; delete the file to reset |
| Slow first LLM answer | Ollama model cold start — warm it up with `ollama run llama3.1` |
| Run feels slow | Validate with `SMOKE_MODE=true`, tune `HUMANIZE_DELAY_MIN/MAX` |

## License

MIT
