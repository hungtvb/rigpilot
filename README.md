# RigPilot Agentic AI

Conversational PC-build advisor for a simulated PC parts store. Local-first with OpenAI for language models and embeddings.

**Status:** Product and AI architecture design approved on 2026-11-04. A deterministic recommendation core is implemented on the feature branch; chat, RAG, MCP, authentication and UI are not implemented yet. No functional application, imported dataset, evaluation PASS or cart/checkout exists in this repository.

## Read first

- [Product & UX design — approved](docs/superpowers/specs/2026-11-04-rigpilot-product-design.md)
- [AI architecture & evaluation — approved](docs/superpowers/specs/2026-11-04-rigpilot-ai-architecture-design.md)
- [Accepted stakeholder decision log](docs/DECISIONS.md)
- [Contributor and Superpowers workflow rules](AGENTS.md)
- [Recommendation core implementation plan — proposed](docs/superpowers/plans/2026-11-04-rigpilot-recommendation-core.md)

Implementation plans live in `docs/superpowers/plans/` **after the corresponding spec is approved**; a separate plan review must precede coding. No direct commits to `main`.

## Local deterministic recommendation core

```bash
python -m pip install -e '.[dev]'
python -m rigpilot.cli import --source data/catalog/curated.json --db rigpilot.db
python -m rigpilot.cli recommend --db rigpilot.db --budget-vnd 30000000 --workload gaming --json
python -m pytest -q
```

The catalog uses real-model manufacturer specifications with **simulated** shop prices and stock. Build recommendations remain **PROVISIONAL** without reviewed workload-fit/benchmark evidence; this CLI does **not** call OpenAI or run an agent.
