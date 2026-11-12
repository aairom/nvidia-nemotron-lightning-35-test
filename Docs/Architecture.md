# Architecture

The app is a local Streamlit GUI. All inference runs in the local Ollama server; nothing leaves the machine.

```mermaid
flowchart LR
    U[User / browser] --> APP[app.py - Streamlit GUI]
    APP --> ENG[engine.py - options, think mode, streaming]
    APP --> CAT[categories.py - 5 task types, examples, classifier]
    APP --> SIM[router_sim.py - simulated top-6-of-128 routing]
    APP --> UIC[ui_components.py - metric cards, expert heatmap]
    ENG --> CLI[ollama_client.py - REST client]
    ENG --> MET[metrics.py - tok/s, TTFT, load, tokens]
    CLI -->|HTTP /api/chat /api/ps /api/tags| OLL[(Ollama :11434)]
    OLL --> MODEL[[Nemotron 3.5 Lightning 30B-A3B<br/>Mamba-2 + MoE + attention]]
    CFG[.env / config.py] --> APP
    CFG --> CLI
```

## Request flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as app.py
    participant C as categories.classify
    participant E as engine.stream_answer
    participant O as Ollama
    U->>A: click example / type prompt
    A->>C: pick task type (example > panel choice > keywords)
    A->>A: router_sim.simulate(prompt, category) -> expert heatmap
    A->>E: messages + options (temperature, top_p, num_ctx) + think
    E->>O: POST /api/chat (stream)
    O-->>E: thinking / content chunks
    E-->>A: LiveUpdate (live tok/s, TTFT)
    O-->>E: final chunk (eval_count, durations)
    E-->>A: exact RunMetrics
    A-->>U: answer + metrics + expert explanation
```

## Measured vs. illustrative

| Data | Origin |
|---|---|
| Connection state, loaded model, memory, context | Ollama `/api/version`, `/api/tags`, `/api/ps` (**measured**) |
| tokens/s, load time, token counts | Ollama final chunk (**measured**); TTFT and wall time by the app timer (**measured**) |
| Expert activation | `router_sim.py` (**illustrative**): Ollama does not expose router decisions. A deterministic top-6-of-128 simulation biased by per-category *expert affinity* in `categories.py`. Specialisation is soft, so several groups always share the work. |

## Modules

| File | Responsibility |
|---|---|
| `app.py` | Streamlit layout, session state, error display |
| `moe_demo/ollama_client.py` | REST client, typed errors (offline, model missing, timeout) |
| `moe_demo/engine.py` | Parameter validation, reasoning mode, message building, streaming + live metrics |
| `moe_demo/metrics.py` | Convert Ollama timings (ns) to tok/s etc. |
| `moe_demo/categories.py` | Task types, examples, system prompts, keyword classifier |
| `moe_demo/router_sim.py` | Deterministic MoE routing simulation |
| `moe_demo/ui_components.py` | HTML renderers (escaped) |
| `moe_demo/help_text.py` | Tooltips and in-app MoE guide |
| `tests/` | Unit tests incl. a stub Ollama HTTP server and Streamlit `AppTest` smoke tests |
| `docs_tools/` | Generator for `Docs/MoE_Application_Documentation.html` (see below); not imported by the app |

## Documentation generator

`docs_tools` turns measurements, captures and the live source code into one self-contained HTML page. It reads the
app packages but the app never imports it.

```mermaid
flowchart LR
    BM[benchmark.py<br/>real runs via moe_demo.engine] --> J[(benchmark.json)]
    SMP[sampling.py<br/>CPU / memory samples] --> BM
    SHOT[(screenshots/*.png)] --> D
    EV[(data/*.txt<br/>captured command output)] --> D
    SRC[moe_demo/*.py<br/>code, router_sim, categories] --> D
    J --> D[data.py]
    D --> CH[chapters_core.py / chapters_ops.py<br/>8 chapters]
    CH --> CTX[context.py<br/>figure numbers, strict cross-refs]
    CH --> TH[theme.py + charts.py<br/>figures, SVG charts, CSS]
    CTX --> B[build_docs.py<br/>two-pass render]
    TH --> B
    B --> HTML[[Docs/MoE_Application_Documentation.html]]
```

Nothing in the page is typed in by hand if it can be derived: line counts, test counts, code listings, simulated
shares and benchmark figures all come from the sources above. `scripts/capture_evidence.sh` regenerates the
terminal captures (pytest with coverage, test-gate, project-audit, secret scan, git-hygiene) and rebuilds the page.
