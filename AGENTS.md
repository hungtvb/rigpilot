# AGENTS.md — RigPilot Agentic AI

This file governs work in this repository. Read the **latest AGENTS.md on the target branch** before every independent repository task (including review, documentation, implementation, testing, PR, and merge). Also read any nested AGENTS.md within the affected paths. Do not rely on a copy from an earlier task.

## Current phase
- **Discovery / brainstorming. No approved implementation design or working application yet.**
- Product: RigPilot Agentic AI, a local-first conversational PC configuration advisor for customers of a simulated PC parts retailer.
- Decisions already confirmed by the stakeholder belong in [docs/DECISIONS.md](docs/DECISIONS.md).
- Active draft specs: [Product & UX](docs/superpowers/specs/2026-11-04-rigpilot-product-design.md) and [AI Architecture & Evaluation](docs/superpowers/specs/2026-11-04-rigpilot-ai-architecture-design.md). A *draft* is not implementation authorization.

## Development workflow
1. **Problem first.** Confirm user value, scenarios, boundaries, and acceptance criteria before proposing agents/frameworks.
2. **Documentation before code.** For small changes, describe scope and checks before editing; for significant changes, present and obtain approval of an implementation design and plan first.
3. **No direct commits to `main`.** Work on isolated branches and submit PRs for review. Do not merge without authorization.
4. **Do not rewrite accepted decisions silently.** Update the canonical decision log only when the stakeholder explicitly changes or confirms a decision; mark unconfirmed ideas as `PROPOSED`.
5. **Keep docs lean.** README is navigation; design spec owns product/UX intent; decision log owns accepted choices. Do not add overlapping numbered documents or empty scaffolding.
6. **Evidence over claims.** Distinguish requirement, proposed design, implemented feature, mock test, real LLM E2E, and measured business value. Never invent PASS status, numbers, benchmark FPS, prices, stock, or external citations.
7. **After work, synchronize status.** Reference changes, review outcomes, tests, and decisions in the relevant PR/issue and canonical docs; link to tested SHA when evidence exists.
8. **Safety and domain correctness.** LLM recommendations do not prove compatibility. Structured compatibility checks, source-backed performance evidence, accurate inventory status, account isolation, and explicit user choice take precedence.
9. **Source strategy.** Existing ShopMate is owned by the stakeholder and may be selectively reused **after** license/dependency and security review; unrelated refund/order/A2A paths are not automatically in scope.

## Documentation ownership — Superpowers workflow

| Location | Owns | Rules |
|---|---|---|
| `README.md` | Short project identity and navigation | No duplicated specs, implementation claims or lengthy setup that does not exist |
| `docs/DECISIONS.md` | One authoritative log of stakeholder-confirmed decisions | Record explicit approvals, dates, alternatives and scope; avoid marking designer suggestions as accepted |
| `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` | What/why, constraints, alternatives, behavior, technical design and evidence plan | Status `DRAFT` until stakeholder signs off; only one canonical owner per subject; cross-link product and technical designs |
| `docs/superpowers/plans/YYYY-MM-DD-<feature>.md` | Task-by-task implementation plans with exact files/interfaces/tests | **Create only after corresponding design spec approval**, using `superpowers:writing-plans`; do not create placeholder plans |
| PR / issue / CI evidence | Actual implementation changes, review findings and test results | Link exact revision, dataset/mode/date; no invented `PASS` |

**Workflow:** Brainstorm options → choose approach → write/review draft design spec → stakeholder approval → Superpowers implementation plan → stakeholder review → isolated branch implementation/test → evidence-backed PR review → approved merge.

Keep specs focused: the product spec owns customer/business/UX intent; the AI spec owns LLM, RAG, MCP, workflow, state, privacy and evaluation. Do not replicate the same detail across both. If a user makes a new accepted decision, update the decision log and the relevant spec in one docs PR; no standalone note per conversational turn.

**Design delegation:** a stakeholder delegating architecture choices authorizes designer recommendations in a draft spec; it does not imply those recommendations were explicitly confirmed or that code may start without reviewing the spec.

## Phase gates
- Do not add implementation frameworks, agents, schema, APIs, or new runtime code until the stakeholder reviews the product/design specification and approves a concrete implementation plan.
- `Proceed to Cart` is a future integration point, not a working cart or checkout feature.
