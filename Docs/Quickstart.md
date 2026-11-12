# Quickstart

## Prerequisites
* macOS/Linux, Python 3.10+ and [`uv`](https://docs.astral.sh/uv/)
* [Ollama](https://ollama.com) running locally with the model pulled:

```bash
ollama pull nemotron-3.5-lightning:30b-a3b-mlx   # ~19 GB, Apple-silicon MLX build
ollama list                                       # verify
```

## Setup and run

```bash
cp .env.example .env                              # adjust if Ollama is not on localhost:11434
bash .bob/skills/python-env/scripts/setup_env.sh . # creates .venv with uv, installs requirements.txt
scripts/start.sh                                  # prints: URL: http://localhost:8501
```

Open the printed URL. Stop with `scripts/stop.sh`; remove the venv and caches with `scripts/cleanup.sh`.

Without the helper script: `uv venv .venv && uv pip install -r requirements.txt && .venv/bin/streamlit run app.py`.

## Using the app
1. **Sidebar** – check *Ollama online* and the model status. The first request loads ~19 GB and can take
   about a minute (use **Load now** to warm it up).
2. **Demo tab** – click any pre-loaded example (5 task types × 3 prompts), or type your own question.
3. Watch **Inference metrics** (tokens/s, time to first token, response time, load time, token counts)
   and the **Expert panel** (which expert groups are likely involved, and why).
4. Change **Temperature / Top-p / Context window / Max tokens / Reasoning mode** in the sidebar; the next
   message uses the new values.
5. **Compare tasks** tab – side-by-side routing profiles and your measured speed per task type.
6. **MoE guide** tab – concepts, and what is measured vs. illustrative.

## Tests

```bash
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest -q          # or: bash .bob/skills/test-gate/scripts/run_tests.sh .
```

## Documentation page

`Docs/MoE_Application_Documentation.html` is generated, self-contained and opens directly from disk.

```bash
.venv/bin/python -m docs_tools.build_docs       # rebuild from the existing captures and benchmark.json
.venv/bin/python -m docs_tools.benchmark        # re-measure (Ollama + model running; use --quick for a short run)
scripts/capture_evidence.sh                     # re-run tests/audit, store their output, rebuild the page
```

Screenshots live in `Docs/assets/screenshots/`. To replace one, capture the new image under the same file name;
if UI elements moved, adjust the pin coordinates (x%, y%) of that figure in `docs_tools/chapters_core.py`.
The build is strict: a cross-reference to a missing figure or section fails the build instead of leaving a dead link.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Ollama offline" | Start Ollama (`ollama serve` or the app); check `OLLAMA_BASE_URL` in `.env` |
| "Model not installed" | `ollama pull nemotron-3.5-lightning:30b-a3b-mlx` |
| Empty answer + warning about token limit | The reasoning trace used all tokens: raise *Max new tokens* or set *Reasoning mode* to Off |
| First answer very slow | Cold model load; later requests reuse the loaded model (keep-alive) |
| Port busy | Change `APP_PORT` and the `--server.port` in `APP_START_CMD` (never 5000 on macOS) |
