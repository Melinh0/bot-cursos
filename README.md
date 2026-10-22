# Bot Cursos

Bot automatizado para conclusão de cursos DataScienceAcademy (LearnWorlds) com
resolução de quizzes e atividades via LLM.

## Arquitetura

```
main.py                           ponto de entrada: login → seleção de curso → loop de unidades → código de saída
  │
  ▼
src/bot                           automação Selenium
  ├── browser.py                  ChromeDriver não detectado + restart
  ├── login.py                    login, checagem de sessão, re-login
  ├── navigator.py                loop de unidades: vídeo, quiz, atividade, próximo
  ├── recovery.py                 recuperação escalonada (reload → re-login → restart)
  ├── scanner.py                  varredura da página, sugestões de seletores CSS
  └── selectors.py                memória de seletores (aprendidos)
  │
  ▼
src/courses                       domínio de cursos
  ├── discovery.py                curso matriculado com menor progresso
  ├── course_map.py               mapa de unidades (pendente/concluído/pulado)
  ├── tracker.py                  estatísticas de progresso
  └── parser.py                   extração de conteúdo HTML
  │
  ▼
src/llm                           resolução de quiz/atividade
  ├── client.py                   cliente compatível com OpenAI, rotação de keys/modelos
  ├── solver.py                   resolução via LLM + fallback heurístico
  └── prompts.py                  templates de prompt
  │
  ▼
data/                             estado persistente (gitignored)
  ├── courses.json                mapa de unidades por curso
  ├── progress.json               contadores de progresso
  ├── selector_memory.json        seletores aprendidos
  └── runs/<timestamp>.jsonl      um evento JSON por passo
```

Transversal: `src/config` (settings pydantic a partir do `.env`) e `src/utils`
(helpers WebDriver/JS, logging, run log).

## Como funciona

1. Faz login e descobre os cursos matriculados, escolhendo o de menor progresso.
2. Monta (ou reaproveita) o mapa de unidades do curso e salta para a primeira
   unidade pendente.
3. Percorre as unidades: busca vídeos até o final, resolve quizzes/atividades
   com a LLM, clica em Próximo e marca a unidade como concluída.
4. Persiste o estado a cada passo, então uma execução interrompida retoma de
   onde parou.

## Recursos

- **Retomar quando quiser** — mapa de unidades e progresso persistidos em
  `data/*.json`
- **Sondagens JS ultrarrápidas** — detecção de quiz/atividade/próximo em uma
  única ida e volta do `execute_script`
- **Recuperação escalonada** — reload → re-login → restart do navegador, além
  de recuperação de página errada e watchdog por unidade
- **Resolução via LLM** — cliente compatível com OpenAI com rotação opcional
  de keys/modelos e fallback heurístico
- **Ritmo humanizado** — delays aleatórios entre ações
- **Modo smoke** — processa no máximo 1 unidade para validar todo o pipeline
  rapidamente
- **Janela em meia tela** — navegador ocupa metade da tela por padrão
  (`BROWSER_HALF_SCREEN=true`)

## Início rápido

### Pré-requisitos

- Python 3.11+ e [uv](https://docs.astral.sh/uv/) (recomendado) ou pip
- Chrome/Chromium
- Ollama (LLM local) ou qualquer API compatível com OpenAI

### Local

```bash
uv venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
uv pip install pytest ruff      # ferramentas de dev

cp .env.example .env            # preencha DSA_EMAIL e DSA_PASSWORD

python main.py                  # execução completa
```

Teste smoke (processa no máximo 1 unidade por tentativa):

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

## Configuração

Variáveis principais (veja `.env.example` para a lista completa):

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DSA_EMAIL` | E-mail da conta | Obrigatório |
| `DSA_PASSWORD` | Senha da conta | Obrigatório |
| `LLM_BASE_URL` | Endpoint compatível com OpenAI | `http://localhost:11434/v1` |
| `LLM_MODEL` | Nome do modelo | `llama3.1` |
| `LLM_FALLBACK_MODELS` | Modelos de fallback (separados por vírgula) | — |
| `OLLAMA_API_KEYS` | API keys (separadas por vírgula, com rotação) | — |
| `HEADLESS` | Rodar navegador sem interface | `false` |
| `BROWSER_HALF_SCREEN` | Navegador em meia tela | `true` |
| `AUTO_DISCOVER_COURSES` | Selecionar automaticamente o curso | `true` |
| `MAX_UNITS_PER_RUN` | Limite de unidades (0 = ilimitado) | `0` |
| `MAX_RUN_ATTEMPTS` | Tentativas por execução | `3` |
| `UNIT_TIMEOUT_SECONDS` | Watchdog por unidade | `180` |
| `UNIT_MIN_DWELL_SECONDS` | Tempo mínimo de permanência no unit antes do Next (a plataforma só marca `completed:true` com ~10s+ de tempo ativo) | `15` |
| `UNIT_ACTIVITY_FLUSH_SECONDS` | Espera após o Next para o POST `update-path-player-activity` ser enviado | `10` |
| `SMOKE_MODE` | Processar no máximo 1 unidade | `false` |
| `LOG_LEVEL` | Nível de logging | `INFO` |

### LLM

O bot conversa com qualquer API compatível com OpenAI (`LLM_BASE_URL`). Para
provedores hospedados, configure `OLLAMA_API_KEYS` (separadas por vírgula) e,
opcionalmente, `LLM_FALLBACK_MODELS` — keys e modelos rotacionam em 429, 401 e
timeouts. O Ollama local não precisa de keys.

## Códigos de saída

| Código | Significado |
|--------|-------------|
| `0` | Curso concluído |
| `1` | Progresso salvo, curso incompleto — rode novamente para retomar |
| `2` | Falhou após todas as tentativas |

## Estrutura do projeto

```
bot-cursos/
├── main.py                  # Ponto de entrada
├── src/
│   ├── bot/                 # Automação Selenium
│   ├── courses/             # Domínio de cursos (mapa, descoberta, progresso)
│   ├── llm/                 # Cliente LLM, solver, prompts
│   ├── utils/               # helpers, logging, runlog
│   └── config/              # settings pydantic
├── tests/                   # Suíte pytest
├── docker/                  # Dockerfile + docker-compose
└── data/                    # Estado em runtime (gitignored)
```

## Monitoramento

Cada execução grava `data/runs/<timestamp>.jsonl` com um evento JSON por passo
(`login_ok`, `unit_done`, `quiz_solved`, `session_lost`, `wrong_page`, ...).

## Testes

```bash
uv run pytest
uv run ruff check main.py src tests
uv run ruff format main.py src tests
```

## Solução de problemas

| Problema | Solução |
|----------|---------|
| Login falha | Confira `DSA_EMAIL`/`DSA_PASSWORD` no `.env` |
| Quiz/atividade não detectado | Seletores são auto-aprendidos em `data/selector_memory.json`; apague o arquivo para resetar |
| Primeira resposta LLM lenta | Cold start do modelo Ollama — aqueça com `ollama run llama3.1` |
| Execução lenta | Valide com `SMOKE_MODE=true`, ajuste `HUMANIZE_DELAY_MIN/MAX` |

## Licença

MIT — veja o arquivo [LICENSE](LICENSE).
