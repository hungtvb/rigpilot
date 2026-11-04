# AGENTS.md — RigPilot Agentic AI

This file governs work in this repository. Read the **latest AGENTS.md on the target branch** before every independent repository task (including review, documentation, implementation, testing, PR, and merge). Also read any nested AGENTS.md within the affected paths. Do not rely on a copy from an earlier task.

## Current phase
- **Discovery / brainstorming. No approved implementation design or working application yet.**
- Product: RigPilot Agentic AI, a local-first conversational PC configuration advisor for customers of a simulated PC parts retailer.
- Decisions already confirmed by the stakeholder belong in [docs/DECISIONS.md](docs/DECISIONS.md).
- Active draft product and UX specification: [docs/superpowers/specs/2026-11-04-rigpilot-product-design.md](docs/superpowers/specs/2026-11-04-rigpilot-product-design.md). A *draft* is not implementation authorization.

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

## Phase gates
- Do not add implementation frameworks, agents, schema, APIs, or new runtime code until the stakeholder reviews the product/design specification and approves a concrete implementation plan.
- `Proceed to Cart` is a future integration point, not a working cart or checkout feature.
