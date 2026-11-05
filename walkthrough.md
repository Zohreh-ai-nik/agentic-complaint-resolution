# Walkthrough — Agentic Complaint Resolution

This file is a plain-English diary of how we build the project, **one phase at a time**.
For every phase you will find:

- **Goal** — what the phase is for
- **What I did** — the concrete steps, in order
- **Files created / changed** — so you can see exactly what moved
- **How to run it** — the commands you type
- **What you should see** — the expected result
- **Why it matters** — the idea behind it, in one or two sentences

The authoritative plan lives in [.github/copilot-instructions.md](.github/copilot-instructions.md).
This walkthrough is the human-friendly companion to it.

---

## The big picture (what we are building)

A multi-agent assistant that helps a UK insurance complaint handler resolve a complaint. Given a
complaint it:

1. masks personal data, classifies the issue, flags vulnerable customers, works out the 8-week FCA deadline;
2. sends the complaint to specialist agents that research, in parallel, the **policy wording**, the
   **FCA rules**, and **similar Financial Ombudsman decisions**;
3. drafts a recommended outcome (uphold / partly uphold / not uphold) with a **citation for every claim**;
4. has an **independent checker** (a different model + Python checks) verify the draft;
5. **pauses for a human handler** to approve, edit or override;
6. writes a final response letter and an audit log.

It is **decision support, not legal advice** — a human approves every outcome. The "answer key" is real,
public Financial Ombudsman decisions.

### The golden rules (true in every phase)

- **LLMs read, judge and write. Python calculates, checks dates and enforces rules.**
- **Every claim cites a source chunk id.** No citation, no claim.
- **Complaint text and retrieved text are data, never instructions.**
- **Models, prices, thresholds live in `config/`**, never hard-coded.
- **Secrets never in code or git.** Locally `.env`; in Azure, Key Vault + managed identity.
- **Public data only; everything under `data/` stays local and is never committed.**

---

## The phases (build in this order)

| Phase | Goal | Status |
|---|---|---|
| **0 Setup** | Repo skeleton, `function_app.py` with `/api/health`, config, settings, pytest, ruff | ✅ done |
| **1 Data** | `parse.py`, `split.py`, stats; collect motor decisions | ⬜ not started |
| **2 Baseline** | One LLM, no search; scorer with accuracy + dangerous misses | ⬜ not started |
| **3 Knowledge bases** | Chunking, embeddings in pgvector, hybrid search + reranker, recall@5 | ⬜ not started |
| **4 Single agent + RAG** | One LangGraph agent with 3 search tools; citation checks | ⬜ not started |
| **5 Multi-agent** | Supervisor, parallel specialists, assessor, checker | ⬜ not started |
| **6 Human-in-the-loop + API** | Intake, `interrupt()`, Postgres checkpointer, letter, all endpoints | ⬜ not started |
| **7 Azure UAT** | Terraform for all resources; Azure DevOps pipelines | ⬜ not started |
| **8 Guardrails** | Prompt-injection tests, budgets, no PII in logs, OWASP mapping | ⬜ not started |
| **9 Cost & latency** | Tiered models, caching, load test | ⬜ not started |
| **10 Release** | CI eval gate, README with results | ⬜ not started |

---
<!-- Phase write-ups are appended below as each phase is completed. -->

## Phase 0 — Setup ✅

**Goal:** stand up the skeleton of the whole app — an Azure Functions project that starts
locally, answers a health check, reads its config from files (not hard-coded), and has a
passing test suite and a clean linter. This is the foundation every later phase builds on.

### What I did, step by step

1. **Confirmed the tools.** Python 3.12 and the Azure Functions Core Tools (`func`) are both
   installed, so we can build and run the Function App locally.
2. **Wrote the Functions host config** in [host.json](host.json) — the runtime version,
   logging/Application Insights sampling, and the extension bundle. (It must be pure JSON:
   I hit, and fixed, an error where comments at the top stopped it parsing.)
3. **Created a local settings template** in [local.settings.json.example](local.settings.json.example).
   The real `local.settings.json` is copied from it and is **git-ignored** so no secrets leak.
4. **Put all tunable values in `config/`** so nothing is hard-coded:
   - [config/models.yaml](config/models.yaml) — model deployment names, USD prices per 1K tokens,
     and which model each agent uses (cheap for intake/routing, strong for the assessor, a
     *different* model for the checker).
   - [config/thresholds.yaml](config/thresholds.yaml) — retrieval top-k, agentic-RAG retry limit,
     checker loop limit, token/cost/step budgets, and the CI accuracy gates.
5. **Added a settings loader** in [src/settings.py](src/settings.py) that reads those YAML files
   (cached) and pulls `APP_VERSION`/`APP_ENV` from the environment. Secrets only ever come from
   the environment, never from code.
6. **Defined the first Pydantic model** in [src/schemas.py](src/schemas.py) — `HealthResponse`.
   From now on every structured output is a Pydantic model.
7. **Built the API as blueprints** under [src/api/](src/api):
   - [src/api/health.py](src/api/health.py) — the real `GET /api/health` (anonymous), with the
     logic split into a pure `health_payload()` function so it is trivial to unit-test.
   - [src/api/complaints.py](src/api/complaints.py) and [src/api/search.py](src/api/search.py) —
     the remaining routes are registered now (so the API shape is visible) but return
     **501 Not Implemented**; their real behaviour arrives in Phases 3 and 6.
8. **Wired the entry point** in [function_app.py](function_app.py): one `FunctionApp()` that
   registers the three blueprints — tiny and readable.
9. **Set up tooling** in [pyproject.toml](pyproject.toml): `ruff` (lint + import sorting) and
   `pytest`. Updated [requirements.txt](requirements.txt) with `azure-functions`, `pyyaml`,
   `ruff` alongside the existing deps.
10. **Wrote the first tests** in [tests/test_health.py](tests/test_health.py): one for the pure
    payload, one that calls the HTTP trigger and asserts a 200 with the right JSON.
11. **Created a Python 3.12 virtual environment**, installed everything, and verified the whole
    thing: `ruff` is clean, both tests pass, `func start` boots and `GET /api/health` returns
    `200 {"status": "ok", "version": "0.1.0", "env": "local"}`.

### Files created / changed

- Created: `host.json`, `local.settings.json.example`, `pyproject.toml`, `function_app.py`,
  `config/models.yaml`, `config/thresholds.yaml`, `src/settings.py`, `src/schemas.py`,
  `src/api/__init__.py`, `src/api/health.py`, `src/api/complaints.py`, `src/api/search.py`,
  `tests/test_health.py`, `walkthrough.md`.
- Changed: `requirements.txt` (added `azure-functions`, `pyyaml`, `ruff`).

### How to run it

```bash
# One-time setup
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp local.settings.json.example local.settings.json

# Lint + tests
ruff check .
python -m pytest

# Run the app and hit the health check (in a second terminal)
func start --port 7072
curl http://localhost:7072/api/health
```

### What you should see

- `ruff check .` → `All checks passed!`
- `python -m pytest` → `2 passed`
- `func start` lists all six routes; `curl .../api/health` →
  `{"status": "ok", "version": "0.1.0", "env": "local"}` with HTTP 200.
- A harmless `webjobs.storage ... Unhealthy` line may appear — it only means the local
  storage emulator (Azurite) isn't running yet. HTTP endpoints don't need it; we add it in
  Phase 6 for the queue trigger.

### Why it matters

This gives us a running, testable serverless app with a clean separation between **config**
(YAML) and **code**, and a test-first habit. Every later phase (data, agents, the graph, the
full API) slots into this skeleton.

