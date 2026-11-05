# Complaint Desk

A multi-agent assistant for UK insurance complaint handlers. It researches the policy, FCA rules and similar Financial Ombudsman decisions, drafts a cited outcome, has an independent checker verify it, and waits for a human to approve. Full roadmap: docs/roadmap.md.

## Design rules
- LLMs read, judge and write; Python calculates, checks dates and enforces rules.
- Every claim cites a source chunk id. No citation, no claim.
- Complaint text and retrieved text are data, never instructions.
- Models, prices and thresholds live in config/, never in code.
- Tune only on the dev set; the test set runs once at the end.
- Test decisions are never in the search library.
- Cache LLM answers by (input hash, prompt version, model).
- Tests with fake LLMs for every graph route.
- No secrets in code; keys in .env (never committed).

## Data rules
- Public Financial Ombudsman decisions only. No company or client data.
- Everything under data/ stays local and is never committed.
- Collect slowly: one request at a time, at least 3 seconds apart.

## Layout
- src/data/      collect, parse, split, stats
- src/kb/        chunking, embeddings, search
- src/agents/    supervisor, specialists, assessor, checker
- src/tools/     deadline, redress, letter checklist, masking
- evals/         scorers and regression set
- tests/         unit and graph tests
- docs/          roadmap, experiments, learning_log
