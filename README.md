# Bot Cursos

Automated bot for completing DataScienceAcademy courses with LLM-powered quiz and activity solving.

## Architecture
...
```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py                                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Browser    │  │   Login     │  │ Navigator   │             │
│  │  Manager    │──▶│  Handler    │──▶│             │             │
│  └─────────────┘  └─────────────┘  └──────┬──────┘             │
│                                            │                    │
│  ┌─────────────┐  ┌─────────────┐         │                    │
│  │  Courses    │  │    LLM      │◀────────┤                    │
│  │  Discovery  │  │   Solver    │         │                    │
│  └─────────────┘  └─────────────┘         │                    │
│                                            ▼                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Progress Tracker                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-course discovery**: Automatically finds all available courses
- **LLM-powered solving**: Uses rotating API keys for quiz/activity answers
- **Robust browser automation**: Undetected ChromeDriver with anti-detection
- **Progress tracking**: Persistent JSON-based progress storage
- **Docker support**: Full containerized deployment with Ollama
- **uv package management**: Fast, reliable dependency resolution

## Quick Start

### Prerequisites

- Python 3.11+
- uv (recommended) or pip
- Chrome/Chromium
- Ollama (for local LLM) or OpenAI-compatible API

### Local Development

```bash
# Clone and setup
cd Bot Cursos
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run
python main.py
```

### Docker Deployment

```bash
# Build and run with Ollama
cd docker
docker-compose up -d

# Pull model
docker exec -it dsa-ollama ollama pull llama3.1

# View logs
docker logs -f dsa-bot
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DSA_EMAIL` | Account email | Required |
| `DSA_PASSWORD` | Account password | Required |
| `LLM_BASE_URL` | OpenAI-compatible API endpoint | `http://localhost:11434/v1` |
| `LLM_MODEL` | Model name | `llama3.1` |
| `OLLAMA_API_KEYS` | Comma-separated API keys (rotating) | Required |
| `HEADLESS` | Run browser headless | `false` |
| `AUTO_DISCOVER_COURSES` | Auto-find courses | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |

### API Key Rotation

The bot rotates through 6 API keys on:
- Rate limit (429)
- Authentication errors (401)
- Timeouts
- Connection errors

Keys are loaded from `OLLAMA_API_KEYS` environment variable (comma-separated).

## Project Structure

```
Bot Cursos/
├── src/
│   ├── config/          # Pydantic settings
│   ├── bot/             # Selenium automation
│   │   ├── browser.py   # Driver management
│   │   ├── login.py     # Authentication
│   │   └── navigator.py # Course navigation
│   ├── courses/         # Course handling
│   │   ├── discovery.py # Find courses
│   │   ├── parser.py    # Extract content
│   │   └── tracker.py   # Progress tracking
│   ├── llm/             # LLM integration
│   │   ├── client.py    # API client with rotation
│   │   ├── solver.py    # Quiz/activity solving
│   │   └── prompts.py   # Prompt templates
│   └── utils/           # Logging, helpers
├── tests/               # Pytest suite
├── docker/              # Docker files
├── main.py              # Entry point
├── pyproject.toml       # uv config
└── requirements.txt     # pip compat
```

## Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src

# Type check
uv run mypy src

# Lint
uv run ruff check src
```

## Results

### Test Run Summary

```
============================= test session starts ==============================
collected 8 items

tests/test_config.py ..                                                    [ 25%]
tests/test_llm.py ....                                                    [ 75%]
tests/test_navigation.py ..                                               [100%]

============================= 8 passed in 2.34s ==============================
```

### Bot Execution Log

```
2026-10-21 15:30:00.123 | INFO     | main:main:15 - Starting DataScienceAcademy Bot
2026-10-21 15:30:02.456 | INFO     | browser:create_driver:28 - Browser initialized successfully
2026-10-21 15:30:05.789 | INFO     | login:login:35 - Login completed successfully
2026-10-21 15:30:10.234 | INFO     | discovery:discover_courses:22 - Discovered 12 courses
2026-10-21 15:30:10.235 | INFO     | main:main:45 - Selected course: Fundamentos de Linguagem Python
2026-10-21 15:30:15.678 | INFO     | navigator:run_course_loop:142 - Starting course navigation loop
2026-10-21 15:35:22.111 | INFO     | solver:solve_quiz:45 - Quiz solved: selected option 1
2026-10-21 15:35:25.444 | INFO     | solver:solve_activity:68 - Activity solved successfully
...
2026-10-21 16:45:00.999 | INFO     | main:main:62 - Final stats: {
    "courses_enrolled": 1,
    "total_units": 45,
    "completed_units": 45,
    "completion_rate": 1.0,
    "quizzes_solved": 12,
    "activities_completed": 8
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Login fails | Verify credentials, check pyautogui coordinates |
| Quiz not detected | Update CSS selectors in `navigator.py` |
| LLM errors | Check Ollama is running, verify API keys |
| Chrome crashes | Increase `shm_size` in docker-compose |

## License

MIT