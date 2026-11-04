# RigPilot — Decision Log

**Updated:** 2026-11-04  
**Source:** stakeholder brainstorming for RigPilot Agentic AI  
**Status:** decisions below are **ACCEPTED at product/UX level**. They are **not** a claim of implemented or tested functionality.

> This is the single source of truth for confirmed choices. Future proposed changes must not silently replace accepted decisions. Add a dated entry or supersede an older ID explicitly.

## Product and scope

| ID | Accepted decision |
|---|---|
| D-001 | Product name: **RigPilot Agentic AI**; customer-facing brand: **RigPilot**. |
| D-002 | Primary user: **customer of a PC-components shop**, not an internal salesperson. |
| D-003 | Main job: conversationally recommend **one best-fit PC configuration** from that shop's catalog, for the customer's use case and budget. |
| D-004 | Store is **simulated**, with simulated prices and inventory. |
| D-005 | Support gaming, office, programming, 2D design, video editing, 3D and local AI/ML from the business-scope perspective; depth of benchmarks varies by available evidence. |
| D-006 | Default build is a **tower**; include monitor, keyboard, mouse and peripherals when the customer asks. Requested accessories count against the same budget unless the customer specifies otherwise. |
| D-007 | Customer decides whether to accept an over-budget option. Disclose trade-offs instead of silently exceeding the budget. |
| D-008 | Where several use cases compete, **ask which matters most** before optimizing. Ask which games for a vague gaming request; then recommend promptly instead of forcing a long questionnaire. |
| D-009 | Prefer **one recommended configuration**, not multiple default alternatives. Customer can refine it in conversation. |
| D-010 | **Only benchmark-supported FPS/performance claims** with relevant game/app, conditions and source. Never invent exact FPS. |
| D-011 | When a requirement cannot be fully met, propose the closest reasonable configuration and **warn explicitly** about unmet requirements. |
| D-012 | Consider future upgrades when the customer expresses upgrade plans; explain costs/constraints and avoid speculative compatibility claims. |

## Configuration and customer control

| ID | Accepted decision |
|---|---|
| D-013 | Customer can ask AI to **automatically re-optimize the whole build** following a changed budget or goal; document component and performance trade-offs. |
| D-014 | When the customer expressly changes one component (e.g. AMD CPU to Intel), AI may automatically adapt **dependent components** for compatibility and must annotate each change. |
| D-015 | Preserve **hard customer constraints**. Change flexible preferences when permitted; if intent is unclear, keep the part and ask before breaking a constraint. If infeasible, warn. |
| D-016 | If a best-fit part is **out of stock**, inform the customer and **ask permission before substituting** it. Distinguish out-of-stock from unknown stock. |
| D-017 | Support **reuse of customer-owned components**; include them in the build assessment but exclude them from the future purchase list and purchasing budget. |
| D-018 | Ask for the exact model of an owned component if possible. If unknown, allow a **provisional build** with clearly identified unverified constraints. |
| D-019 | Distinguish **compatible**, **unverified**, and **known incompatible**; users may preserve or later purchase a known-incompatible parts list, but warnings must remain explicit and must not imply the PC will function. |
| D-020 | Separate warnings for compatibility, stock, budget/performance and unmet requirements. Persist them with the version that generated them. |
| D-021 | Save every **applied configuration version** with its conversation; selecting an old version is read-only and restoring it creates a new version (no destructive overwrite). |

## Identity, checkout boundary and data

| ID | Accepted decision |
|---|---|
| D-022 | Users must **sign in**; initial auth method: **email + password**. Persist conversations and build-version histories by account, with isolation. |
| D-023 | **Proceed to Cart** is a **future integration point only**. No functional shopping cart, payment, checkout or order fulfillment in the initial scope. |
| D-024 | Future cart will hold **one PC configuration** at a time. Replacing it with a different build needs explicit customer confirmation. |
| D-025 | For future cart integration, include only parts being purchased; carry warnings along even if compatibility is unverified or known incompatible. |
| D-026 | Real hardware models and manufacturer specifications, real games/software and official system requirements, sourced real benchmarks. **Shop prices and stock are simulated.** |
| D-027 | Use **curated, verified datasets** in the first release; no live web research during customer conversations. |
| D-028 | Start with a **small, sufficient** catalog, covering replacements, stockouts, incompatible combinations and varied use cases. Exact item counts are not approved. |
| D-029 | Manage catalog and knowledge using **files plus import/validation scripts**, not an Admin UI. |
| D-030 | **Local-first** deployment. No cloud deployment requirement at this stage; LLM API use remains an open technical choice. |
| D-031 | **Selective Reuse (Option B)** from stakeholder-owned ShopMate; reuse infrastructure only after an audit, and build PC-specific domain logic separately. |

## Experience and interface

| ID | Accepted decision |
|---|---|
| D-032 | Visual direction: **Modern SaaS + Premium Hardware**; clarity and hardware presentation take priority over gaming decoration. |
| D-033 | **Chat-first**: after login, land directly in AI Chat + read-only Visual PC Builder; no guided-start/marketing hero required. |
| D-034 | **Desktop-first**, responsive on mobile. Mobile has **two tabs: Chat / PC Build**. |
| D-035 | After a completed build on mobile, **stay on Chat** and show a contextual action to view the updated PC Build tab. |
| D-036 | PC Builder is **read-only** initially; all changes are requested via Chat. |
| D-037 | Show components as a **Compact List** with quality product images, specific model, key specs, price and relevant state; not large marketing product cards. |
| D-038 | Warnings use **Summary + Inline**: whole-build state summary plus detailed notices alongside affected components. |
| D-039 | Version history uses a **timeline History Drawer**; preview and restore versions, but **no side-by-side version comparison** in initial scope. |
| D-040 | Execution progress is based on **actual execution events**, shown as one compact Chat status line with expandable details; never fake graph progress. |
| D-041 | **Publish the PC Builder update only after processing and validation complete**. On failure keep the prior saved version, show an error; validation may complete with explicit warnings. |

## Recommendation architecture direction

| ID | Accepted decision |
|---|---|
| D-042 | **Hybrid Agentic (Option C)**: LLM interprets and clarifies customer requirements, coordinates recommendation/refinement and explains results; **deterministic structured logic** filters products, checks hardware compatibility, budget and inventory constraints, and performs explainable optimization. LLM judgments alone cannot establish compatibility, FPS, price or inventory facts. Exact agent count, ranking method and integration design are still open. |
| D-043 | **Within-budget priority:** choose the configuration with the strongest fit/performance for the customer's prioritized workloads **within the stated budget**, rather than selecting a cheaper option solely to save money. The customer-approved budget is a ceiling; never auto-exceed it. Do not assume that every unit of budget must be spent. How to evaluate marginal performance gains versus additional price remains open. |

## Deferred / open, NOT accepted implementation decisions

- **Architecture:** exact agent count, orchestration, LangGraph/MCP/RAG integration, constraint representation, optimizer/ranking algorithm and service boundaries are still open; D-042 establishes only the division of responsibility.
- **Storage/auth technology:** DB, session/security implementation, hosting model and secret handling.
- **Data contracts:** exact hardware coverage, provenance and benchmark schema, freshness and import strategy.
- **UX detail:** design tokens, error details, keyboard/accessibility QA, status copy, exact mobile history drawer behavior.
- **Integration:** `Proceed to Cart` contract, any eventual cart service/CTA states.
- **Evidence:** acceptance scenarios, deterministic or provider-backed test strategy, performance target and business baseline.

## Change procedure

1. Record a proposed change separately; discuss its impact on earlier choices.
2. Stakeholder confirms or rejects the change.
3. Update the existing ID or mark it superseded with a date, preserving rationale and history.
4. Align the active product design and later acceptance tests; do not claim code is updated until verified.
