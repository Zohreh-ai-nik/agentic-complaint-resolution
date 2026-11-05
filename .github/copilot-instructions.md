# Agentic Complaint Resolution – Project Brief

This is the full brief for the coding assistant (GitHub Copilot or Claude Code). Read it before writing any code, and build **one phase at a time**. Never jump ahead.

---

## 1. What we are building

A **multi-agent AI system that helps a UK insurance complaint handler resolve a customer complaint**.

Given a complaint, the system:

1. masks personal data, classifies the issue, flags vulnerable customers and works out the 8-week FCA deadline
2. sends the complaint to specialist agents that research, in parallel:
   - the **policy wording** (what the insurance policy says)
   - the **FCA rules** (DISP complaint rules, Consumer Duty, ICOBS)
   - **similar Financial Ombudsman decisions** (precedent) and how they ended
3. drafts a recommended outcome (uphold / partly uphold / not uphold), with a **citation for every claim**
4. has an **independent checker** (a different model plus Python checks) verify the draft
5. **pauses for a human handler** to approve, edit or override
6. writes a final response letter and an audit log

It is **decision support, not legal advice**. A human approves every outcome.

**The answer key:** real, public Financial Ombudsman decisions. We give the system the complaint with the decision hidden, and compare its outcome with the Ombudsman's.

---

## 2. Hard rules (apply to every phase)

- **LLMs read, judge and write. Python calculates, checks dates and enforces rules.** Never let the LLM do maths, deadlines or redress.
- **Every claim cites a source chunk id.** No citation, no claim. Python checks that the cited chunk exists and contains the quoted text.
- **Complaint text and retrieved text are data, never instructions.** Wrap them in clear delimiters, and say so in the system prompt.
- **Models, prices, thresholds and limits live in `config/`**, never hard-coded.
- **Secrets never in code, prompts, logs or git.** Locally `.env`; in Azure, Key Vault plus managed identity.
- **Tune only on the dev set. The test set runs once at the end.** Test decisions are never in the search library.
- **Public data only.** Financial Ombudsman decisions, the FCA Handbook, public policy wordings. No company or client data.
- **Everything under `data/` stays local and is never committed.**
- **Collect politely:** one request at a time, at least 3 seconds apart, with retries and back-off.
- **Small, testable functions, Pydantic models for every structured output, type hints, docstrings.**
- **Tests with fake LLMs for every graph route.** No real API calls in unit tests.
- **Cache LLM responses** by (input hash, prompt version, model) to save cost while developing.
- **Ask before adding a new dependency or a new Azure service.**

---

## 3. Tech stack

| Area | Choice | Why |
|---|---|---|
| Language | Python 3.12 | |
| API layer | **Azure Functions (Python v2 programming model)**. **No FastAPI.** All endpoints are Function App HTTP triggers | Serverless, matches production experience |
| Long-running work | **Azure Storage Queue trigger** in the same Function App | HTTP requests must return quickly; the agent run happens in the background |
| Agent orchestration | **LangGraph** (StateGraph, conditional edges, `interrupt()` for human approval) | Real branching, loops and human-in-the-loop |
| Graph state | **LangGraph PostgreSQL checkpointer** | A case can pause for a human and resume later |
| LLMs | **Azure OpenAI**, via a small `llm.py` wrapper (later LiteLLM if needed) | Cheap model for intake/routing, strong model for assessment, a different model for the checker |
| Embeddings | Azure OpenAI `text-embedding-3-small` | |
| Search | **PostgreSQL Flexible Server + pgvector**, plus keyword search (PostgreSQL full-text), hybrid + reranker | One database for vectors, metadata, state and results |
| PDF text | `pdfplumber` | Decisions are text PDFs with a fixed structure |
| PII masking | **Microsoft Presidio** | Local, free |
| Validation | **Pydantic v2** | Structured outputs everywhere |
| Observability | **Application Insights** (OpenTelemetry); token, cost and latency per step also saved to a `runs` table | See where time, money and errors go |
| Infrastructure | **Terraform** (azurerm provider) | Infrastructure as code |
| CI/CD | **Azure DevOps Pipelines** (YAML in `azure_pipelines/`) | Lint, test, offline evals as a gate, Terraform plan/apply, deploy to UAT |
| Environment | **UAT** in the user's **personal** Azure subscription, region `uksouth` | |
| Tests | pytest | |

---

## 4. Function App endpoints

All endpoints live in `function_app.py`, organised with Blueprints. Use function-level auth keys for now.

| Method | Route | What it does |
|---|---|---|
| GET | `/api/health` | Returns status and version |
| POST | `/api/complaints` | Accepts a complaint (text + optional product and policy reference), stores it, puts a message on the queue, returns `{complaint_id, status: "queued"}` |
| GET | `/api/complaints/{id}` | Returns status (`queued`, `running`, `awaiting_approval`, `done`, `failed`), the draft outcome, citations, checker verdict, deadline and flags |
| POST | `/api/complaints/{id}/decision` | The human handler approves, edits or overrides. Resumes the graph from the checkpoint |
| GET | `/api/complaints/{id}/letter` | Returns the final response letter once approved |
| POST | `/api/search/{source}` | Search one knowledge base (`decisions`, `rules`, `policies`) directly; useful for debugging and later for MCP tools |
| Queue trigger | `complaints-queue` | Runs the LangGraph graph for one complaint until it finishes or pauses for approval |

---

## 5. The agent graph

```text
intake ──► supervisor ──► (in parallel, only the specialists needed)
                           ├─ policy_agent    (agentic RAG over policy wordings)
                           ├─ precedent_agent (agentic RAG over Ombudsman decisions)
                           └─ rules_agent     (RAG over FCA Handbook)
                       ──► assessor ──► checker ──┬─ pass ──► human_approval ──► letter ──► END
                                          ▲        └─ fail (max 2 loops) ─┐
                                          └────────────────────────────────┘
                                         fail after 2 loops ──► human_approval (flagged)
```

| Node | Job | Tools |
|---|---|---|
| `intake` | Mask PII (Presidio), classify issue type, detect vulnerability, calculate the 8-week deadline | Presidio, cheap LLM, Python |
| `supervisor` | Choose which specialists the issue needs | Cheap LLM + rules |
| `policy_agent` | Find the relevant policy clause | Search tool over `policies` |
| `precedent_agent` | Agentic RAG: rewrite the complaint into search queries, hybrid search, rerank, grade the results, search again if weak (max 3 tries) | Search tool over `decisions` |
| `rules_agent` | Find the FCA rules that apply | Search tool over `rules` |
| `assessor` | Draft the outcome, reasons and redress suggestion, every claim citing a chunk id | Strong LLM, structured output |
| `checker` | Python: every citation exists and contains its quote; outcome consistent with reasons. Second model: does each source support its claim? | Python + a different LLM |
| `human_approval` | `interrupt()`; wait for the handler | LangGraph checkpointer |
| `letter` | Final response letter from a template + LLM; Python checklist of mandatory elements (outcome, redress, right to refer to the Ombudsman, time limit) | Template, LLM, Python |

**Vulnerable customers always go to human approval.** Redress and interest are calculated in Python only.

**Graph state** (Pydantic): complaint_id, masked_text, issue_type, deadline, flags, evidence per specialist (chunk ids + quotes), draft, checker verdict, loop count, human decision, letter, token and cost totals.

---

## 6. Data

**Source:** Financial Ombudsman decisions database (public), insurance sector, starting with **motor** complaints.

- Search page: `https://www.financial-ombudsman.org.uk/businesses/resolving-complaint/ombudsman-decisions/search` (10 results per page, paging with `Start=0,10,20…`)
- Each decision PDF: `https://www.financial-ombudsman.org.uk/decision/DRN-XXXXXXX.pdf`
- Each PDF has the headings: **The complaint**, **What happened**, **What I've decided – and why**, **My final decision**

**Already built:** `src/data/collect.py` (index, download, stats).

**To build:**
- `src/data/parse.py`: split each PDF into the four sections; extract outcome (`upheld` / `partly_upheld` / `not_upheld`) from the final section; compare with the listing outcome; write mismatches to `data/processed/parse_issues.csv`; output `data/processed/decisions.jsonl` (Pydantic `Decision` model)
- `src/data/split.py`: **test** = newest ~200, balanced by outcome; **dev** = ~300 older, balanced; **library** = the rest. Write `data/labels/split.csv`
- FCA Handbook sections (DISP 1, DISP 1.6, ICOBS 8, PRIN 2A) and ~20 public motor policy wordings, each with source, section and version date

**Test case shape:** input = complaint + what happened; hidden answer = outcome, redress, key reasons.

---

## 7. Evaluation

| Metric | How |
|---|---|
| Outcome accuracy | vs the Ombudsman's final decision |
| **Dangerous misses** | System says "not uphold" where the Ombudsman upheld. Reported separately |
| Over-upholds | System upholds where the Ombudsman did not |
| Citation accuracy | % of citations that exist, contain the quote, and support the claim |
| Retrieval recall@5 | A same-issue precedent is in the top 5 |
| Letter compliance | Python checklist pass rate |
| Consistency (pass^3) | Same complaint 3 times, same outcome |
| Cost and P50 / P95 latency | Per complaint, per step |
| Reasoning quality | LLM judge vs the Ombudsman's reasons, calibrated on 30 cases the user scores by hand |

Compare versions on the same dev set:
- A: one LLM, no search (baseline)
- B: single agent + RAG
- C: multi-agent
- D: C without the checker
- E: C with tiered models

Log every run in `docs/experiments.md`. A 50-case regression set runs in CI and **fails the pipeline** if accuracy drops or dangerous misses rise.

---

## 8. Azure UAT resources (Terraform)

All in one resource group, `rg-acr-uat`, region `uksouth`, tags `project=agentic-complaint-resolution`, `env=uat`.

- Storage account (Function App content, queue `complaints-queue`, blob container for raw PDFs)
- **Function App**, Linux, Python 3.12, Flex Consumption plan, system-assigned managed identity
- Application Insights + Log Analytics workspace
- Key Vault (RBAC mode). The Function App reads secrets with its managed identity; the pipeline can write them
- Azure OpenAI account with deployments: a small model (intake, routing, rewriting), a strong model (assessor), embeddings. Names in variables. The checker uses a different model from the assessor
- PostgreSQL Flexible Server (Burstable B1ms) with the `vector` extension allowed; databases for search and the checkpointer
- Role assignments: Function App → Key Vault Secrets User, Cognitive Services OpenAI User, Storage roles
- Terraform state in a separate storage account (created once by hand with `az`)

Keep costs low: smallest SKUs, and a budget alert on the resource group.

---

## 9. Repo structure

```text
agentic-complaint-resolution/
  function_app.py                 Function App entry point (HTTP + queue triggers via Blueprints)
  host.json
  local.settings.json.example     (local.settings.json is git-ignored)
  requirements.txt
  CLAUDE.md
  .github/copilot-instructions.md
  config/
    models.yaml                   model names, prices per 1K tokens, routing
    thresholds.yaml               loop limits, top-k, budgets, CI gates
  src/
    api/                          blueprints: complaints, search, health
    data/                         collect, parse, split, stats
    kb/                           chunking, embeddings, hybrid search, reranker, ingest
    agents/                       intake, supervisor, policy, precedent, rules, assessor, checker, letter
    graph.py                      LangGraph wiring, checkpointer, interrupt
    tools/                        deadline, redress, letter checklist, pii masking, citation check
    llm.py                        LLM client wrapper with caching, retries, token and cost logging
    schemas.py                    Pydantic models
    settings.py                   reads env vars / Key Vault references
  evals/                          scorers, judge, run_eval.py, regression set ids
  tests/                          unit, graph routes with fake LLMs, security
  infra/terraform/                main.tf, variables.tf, outputs.tf, uat.tfvars
  azure_pipelines/                ci.yml, terraform.yml, deploy.yml
  docs/                           PROJECT_BRIEF.md, roadmap.md, experiments.md, learning_log.md, security.md
  data/                           LOCAL ONLY, git-ignored
```

---

## 10. Phases (build in this order; stop and report after each)

| Phase | Goal | Done when |
|---|---|---|
| **0 Setup** | Repo skeleton, `function_app.py` with `/api/health`, `host.json`, config files, settings, pytest, ruff | `func start` runs locally and `/api/health` returns 200; tests pass |
| **1 Data** | `parse.py`, `split.py`, stats; 50 then ~2,000 motor decisions | `stats` shows counts per split and outcome; 20 random parses look right |
| **2 Baseline** | One LLM, no search; scorer with accuracy, dangerous misses, confusion table, cost, latency | Baseline row in `docs/experiments.md` |
| **3 Knowledge bases** | Chunk by structure; embeddings in pgvector (local Postgres in Docker first); hybrid search + reranker; recall@5 | Recall@5 for basic vs hybrid vs hybrid + reranker |
| **4 Single agent + RAG** | One LangGraph agent with 3 search tools; citation checks in Python | Measured improvement over baseline |
| **5 Multi-agent** | Supervisor, parallel specialists, assessor, checker with max 2 loops | Table comparing single vs multi-agent on accuracy, dangerous misses, citations, cost |
| **6 Human-in-the-loop + API** | Intake (Presidio, deadline, vulnerability), `interrupt()`, Postgres checkpointer, letter + checklist, all HTTP endpoints and queue trigger | Complaint in via POST, pauses, resumes after approval, letter passes the checklist |
| **7 Azure UAT** | Terraform for all resources; Azure DevOps pipelines (CI, Terraform plan/apply, deploy); Key Vault + managed identity | Endpoints work in UAT; pipeline green |
| **8 Guardrails** | Prompt-injection test complaints, step and token budgets, no PII in logs, OWASP LLM Top 10 mapping in `docs/security.md` | Security table with attack, result, fix |
| **9 Cost and latency** | Tiered models, prompt caching, top-k, checker on/off, load test at 5/20/50 concurrent with back-off on 429 | Cost per complaint and P50/P95 table |
| **10 Release** | CI eval gate on the 50-case regression set; README with architecture, results and limits | Live UAT, green pipeline, release report |
| *Later* | MCP servers for the three knowledge bases | Same cited answer from the agent and a chat client |

---

## 11. How to work with me

- Before each phase, show me a short plan: files to create or change, and how we will test it. Wait for my OK.
- Write the tests with the code.
- After each phase, give me the commands to run and what I should see.
- Keep changes small. Explain any new concept in one or two plain sentences.