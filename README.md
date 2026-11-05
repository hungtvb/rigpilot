# RigPilot Agentic AI

Conversational PC-build advisor for a simulated PC parts store. Local-first with OpenAI for language models and embeddings.

**Status:** Approved design; deterministic recommendation core in feature development. This is **not** the final conversational AI app. MCP, RAG, LangGraph, accounts, history and checkout are not implemented.

## Read first

- [Product & UX design — approved](docs/superpowers/specs/2026-11-04-rigpilot-product-design.md)
- [Shared visual design tokens — v0.5 mockup](DESIGN.md)
- [AI architecture & evaluation — approved](docs/superpowers/specs/2026-11-04-rigpilot-ai-architecture-design.md)
- [Accepted stakeholder decision log](docs/DECISIONS.md)
- [Contributor and Superpowers workflow rules](AGENTS.md)
- [Recommendation core implementation plan — proposed](docs/superpowers/plans/2026-11-04-rigpilot-recommendation-core.md)

Implementation plans live in `docs/superpowers/plans/` **after the corresponding spec is approved**; a separate plan review must precede coding. No direct commits to `main`.

## Local deterministic core (feature branch)

The current implementation can import a **fourteen-item curated real-model PC catalog**, with **simulated VND prices and inventory**, and output one reviewed-by-rules configuration with explicit warnings. It does **not** call OpenAI or make measured FPS claims.

```bash
python -m pip install -e '.[dev]'
python -m rigpilot.cli import --source data/catalog/curated.json --db rigpilot.db
python -m rigpilot.cli recommend --db rigpilot.db --budget-vnd 26000000 --workload gaming --json
pytest -q
```

The sample may return **PROVISIONAL** because workload performance evidence is not yet populated. It must not be presented as a verified optimized PC for purchase. A known hardware mismatch is surfaced as **INCOMPATIBLE**, not hidden.
