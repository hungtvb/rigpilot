# RigPilot Recommendation Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and test a usable **local, deterministic recommendation core**: import a small curated PC-parts catalog into SQLite, assess hardware/budget/stock constraints, recommend one justified build, and exercise it via a CLI. This first slice is **not** the final conversational app.

**Architecture:** File-based catalog ingestion creates a versioned SQLite snapshot. Pure domain modules evaluate compatibility, inventory, approvals and explainable value-first candidate ranking. The CLI supplies a non-LLM entrypoint and outputs structured results, enabling independent correctness tests before wiring the same functions to MCP and LangGraph.

**Tech Stack:** Python 3.12, Pydantic 2, stdlib `sqlite3` / `argparse` / `json`, pytest, GitHub Actions; no OpenAI calls or secrets in this slice.

**Spec:** [AI Architecture & Evaluation](../specs/2026-11-04-rigpilot-ai-architecture-design.md), [Product & UX Design](../specs/2026-11-04-rigpilot-product-design.md), [Decision Log](../../DECISIONS.md), especially D-003, D-007, D-010, D-013–D-021, D-026–D-029, D-042–D-044, D-047, D-052, D-058–D-060.

**Plan status:** PROPOSED — stakeholder plan approval required before coding. Design baseline approved 2026-11-04. Target branch for code execution will be a **fresh feature branch** after approval; do not write application code in the documentation branches.

## Global Constraints

- Read latest `AGENTS.md` (and nested instructions) from the target branch **before each independent repository task**.
- Only a simulated shop: **real verified manufacturer hardware specs**, **synthetic price/stock**, no live internet search during customer chat; test-only fixture products must be clearly marked synthetic.
- OpenAI is the chosen future LLM/embedding provider, but **do not add LLM, LangGraph, MCP, ChromaDB or a UI to this plan**. This is a bounded prerequisite core with an independent CLI.
- Never silently replace a locked part or substitute an out-of-stock selected part without **pair-specific customer approval**. Never treat unknown stock or missing price as available/in-budget.
- **COMPATIBLE / UNVERIFIED / INCOMPATIBLE** must remain distinct. A known incompatible list can be returned as **warned/non-operational**, never silently certified functional.
- Owned components count toward fit checks, not the purchase budget. A provisional owned component has **unverified** dimensions/connectors unless its exact model is known.
- Quantitative FPS/performance claims require sourced comparable benchmarks; this slice **must not produce FPS**. Its workload-fit annotations are qualitative, reviewable catalog metadata, not benchmark results.
- Do not invent a universal "5% improvement" threshold. Pick cheaper builds **when verified usefulness is equal or indistinguishable**; show uncertainty rather than unsupported precision.
- Use TDD for domain logic, run focused tests before each task commit, and record observed results. No documentation-only CI gate. No direct commits to `main` and no merge without user authorization.
- Inspect ShopMate source/license/security **before reusing any code** in later feature plans. This core has zero mandatory ShopMate dependency.

## Review Focus

Five high-risk classes must be explicitly pinned in the owning tests:

1. **[Task 3]** An offer missing a price must **not** be declared within budget; unknown stock must not be presented as in stock.
2. **[Task 3]** A locked, out-of-stock GPU in an existing build must **not** be silently replaced even when an available cheaper GPU exists.
3. **[Task 2 + Task 3]** An owned GPU with only an approximate label must cost zero in the purchase total **but** leave physical/power compatibility `UNVERIFIED`.
4. **[Task 2 + Task 5]** A CPU/motherboard socket conflict must stay `INCOMPATIBLE`, including in CLI JSON; recommendations must not be marked "working PC".
5. **[Task 4 + Task 5]** If an enumeration cap is hit or benchmark/fit evidence is insufficient, result must say **selection is provisional**, never proven globally optimal.

## Boundaries and file map

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Python 3.12 packaging, runtime and test dependencies |
| `src/rigpilot/catalog/models.py` | Pydantic catalog/specs/offer/snapshot contracts |
| `src/rigpilot/catalog/store.py` | SQLite schema, atomic importer, snapshot read API |
| `src/rigpilot/domain/models.py` | Typed request, owned part, selected build, issues, approvals and result contracts |
| `src/rigpilot/domain/compatibility.py` | Pure hardware compatibility evaluation |
| `src/rigpilot/domain/constraints.py` | Prices, owned parts, stock, hard locks and explicit consent |
| `src/rigpilot/domain/optimizer.py` | Bounded candidate search, transparent workload-fit ranking |
| `src/rigpilot/application/recommend.py` | Orchestrate catalog → candidate → validation → result, with no LLM |
| `src/rigpilot/cli.py` | `import` and `recommend` CLI, stable JSON output/exit codes |
| `data/catalog/curated.json` | Small real-model curated inventory with provenance; must be researched and checked at implementation |
| `tests/fixtures/catalog_test.json` | **Synthetic test-only** parts with controlled conflicts, stock and missing data |
| `tests/test_catalog.py` | Import/schema/snapshot correctness |
| `tests/test_compatibility.py` | Compatibility rules and uncertainty |
| `tests/test_constraints.py` | Budget, ownership, stock and consent |
| `tests/test_optimizer.py` | Value-first ranking, fixed locks and bounded search |
| `tests/test_recommend_cli.py` | CLI integration with test-only fixture and status propagation |
| `.github/workflows/python-checks.yml` | Deterministic CI on code/data changes; no OpenAI calls |

File ownership is deliberate. No premature `agents/`, `services/` factory, plugin abstraction, UI scaffold or generalized event bus.

## Data and interface contract (frozen for this plan)

Use Pydantic 2 models. Exact Python interface names below must match call sites and tests; adjust only through an explicit plan review.

- `ComponentKind`: `Literal["cpu","motherboard","ram","gpu","storage","psu","case","cooler"]`. V1 core selects at most **one item / kit per kind**; bundles/additional units require another plan.
- `StockState`: `Literal["IN_STOCK","OUT_OF_STOCK","UNKNOWN"]`.
- `CatalogItem` fields: `product_id: str`, `kind: ComponentKind`, `brand: str`, `model: str`, `specs: dict[str, str | int | bool | list[str]]`, `spec_source_url: str | None`, `spec_checked_at: str | None`, `workload_fit_tier: dict[str, int]` (curated, qualitative 0–3), `fit_evidence_ids: dict[str, list[str]]`; never label tiers as measured FPS.
- `CatalogOffer` fields: `product_id: str`, `price_vnd: int | None`, `stock: StockState`, `snapshot_at: str`. An unknown price stays `None`; numeric prices must be nonnegative integers. Synthetic offers remain explicitly identified as simulated.
- `CatalogSnapshot` fields: `snapshot_id: str`, `products: tuple[CatalogItem, ...]`, `offers: dict[str, CatalogOffer]`. A deterministic hash of canonical validated input provides a stable snapshot ID. Import of duplicate identical data is idempotent; malformed imports have **zero partial writes**.
- Typed keys in `specs` per `kind`: CPU `socket` / `memory_type` / `tdp_w`; motherboard `socket` / `memory_type` / `form_factor` / `m2_slots`; RAM `memory_type`; GPU `length_mm` / `board_power_w` / `power_connectors`; PSU `rated_w` / `connectors`; case `supported_form_factors` / `max_gpu_length_mm` / `max_cooler_height_mm`; cooler `supported_sockets` / `height_mm`; storage `interface`. Missing/unknown measurements may be explicitly absent and must produce `UNVERIFIED` when needed for a check, not importer fabrication. Validate keys/types/units at import, reject nonsensical negative dimensions and impossible enum values.
- `OwnedComponent`: `kind: ComponentKind`, `product_id: str | None`, `label: str | None`; unknown model is provisional and not a verified source. Define this model in **Task 2**, along with `BuildSelection`, before implementing `BuildRequest` in Task 3.
- `BuildRequest`: `budget_vnd: int`, `primary_workload: str`, `secondary_workloads: tuple[str, ...]`, `locked_parts: dict[str, str]`, `owned_components: tuple[OwnedComponent, ...]`, `previous_parts: dict[str, str] | None`, `approved_replacements: tuple[tuple[str, str], ...]`. Each approval pair is `(previous_product_id, replacement_product_id)`, never blanket approval by component kind.
- `BuildSelection`: `part_ids: dict[str, str]`, `owned_components: tuple[OwnedComponent, ...]`. For an unknown owned part, include it under `owned_components` with `product_id=None` and **do not** invent a catalog product ID in `part_ids`.; `ValidationIssue`: `code`, `severity`, `affected_part_ids`, `message`; `CompatibilityReport`: `status: "COMPATIBLE" | "UNVERIFIED" | "INCOMPATIBLE"`, `issues`; `ConstraintReport`: `total_purchase_vnd: int | None`, `budget_verified: bool`, `stock_status`, `approval_required`, `issues`.
- `RecommendationResult`: `status: "RECOMMENDED" | "PROVISIONAL" | "APPROVAL_REQUIRED" | "NO_CANDIDATE"`, `selected: BuildSelection | None`, `compatibility: CompatibilityReport | None`, `constraints: ConstraintReport | None`, `evidence_ids: tuple[str, ...]`, `selection_limited: bool`, `explanation: tuple[str, ...]`. `RECOMMENDED` is only possible with complete budget proof, verified compatibility and no pending approval; otherwise warnings and provisional state are explicit.

### Task 1: Catalog contracts, atomic SQLite import and verified seed

**Files:**
- Create: `pyproject.toml`, `src/rigpilot/__init__.py`, `src/rigpilot/catalog/__init__.py`, `src/rigpilot/catalog/models.py`, `src/rigpilot/catalog/store.py`, `data/catalog/curated.json`, `tests/fixtures/catalog_test.json`, `tests/test_catalog.py`.
- No modifications to accepted design docs.

**Interfaces:**
- Produces `import_catalog(source_path: Path, db_path: Path) -> str` returning `snapshot_id`.
- Produces `load_catalog(db_path: Path, snapshot_id: str | None = None) -> CatalogSnapshot`.
- Model contracts as frozen above. SQLite tables `catalog_snapshots`, `products`, `offers` keyed by snapshot; the last two keyed by composite `(snapshot_id, product_id)`.

- [ ] **Step 1 — failing tests:** create `tests/test_catalog.py` with `test_import_roundtrip_preserves_price_stock_and_model_id`, `test_import_rejects_duplicate_product_ids_atomically`, `test_import_rejects_negative_spec_values`, `test_missing_price_preserves_none` and `test_same_input_is_idempotent`. Assert exact snapshot equality and unchanged row counts after an invalid import.
- [ ] **Step 2 — RED:** run `pytest tests/test_catalog.py -q`; expected failure before importer/contracts exist.
- [ ] **Step 3 — implementation:** add Pydantic schemas, typed category validators, SQLite transaction, deterministic canonical source hash, foreign keys and parameterized queries. Reject duplicate IDs and offers referencing missing parts; do not change live snapshot when import fails. A schema migration framework is unnecessary for this first slice.
- [ ] **Step 4 — data curation:** supply the **smallest scenario-complete** actual-model `data/catalog/curated.json`; verify each model/spec against a manufacturer source and record its URL/date. Simulated offers should permit testable price changes and stockouts. No made-up manufacturer URLs, invented FPS or generic "RTX" identifiers with missing exact revisions. Keep synthetic/unit fixtures separately in `tests/fixtures/`.
- [ ] **Step 5 — GREEN + review:** run `pytest tests/test_catalog.py -q` and `python -m pip check`; expected zero failures. Review import idempotency, atomic rollback and real-model sources.
- [ ] **Step 6 — commit:** `git add pyproject.toml src/rigpilot/catalog src/rigpilot/__init__.py data/catalog/curated.json tests/fixtures/catalog_test.json tests/test_catalog.py && git commit -m "feat: add versioned SQLite PC catalog import"`.

### Task 2: Deterministic hardware compatibility

**Files:**
- Create: `src/rigpilot/domain/__init__.py`, `src/rigpilot/domain/models.py`, `src/rigpilot/domain/compatibility.py`, `tests/test_compatibility.py`.

**Interfaces:**
- Consumes Task 1 `CatalogSnapshot` and Task 2 `BuildSelection`, which includes `owned_components`; the latter carries provisional owned-part data even when no catalog ID is known.
- Produces `evaluate_compatibility(build: BuildSelection, snapshot: CatalogSnapshot) -> CompatibilityReport`.
- Reports each failed/unknown rule with stable `code`, relevant part IDs and technical reason. Combine statuses with precedence `INCOMPATIBLE > UNVERIFIED > COMPATIBLE`; a known incompatibility is not erased by independent unknowns.

- [ ] **Step 1 — failing tests:** add `test_socket_conflict_is_incompatible`, `test_ram_generation_conflict_is_incompatible`, `test_case_form_factor_or_gpu_clearance_conflict_is_incompatible`, `test_unknown_owned_gpu_dimensions_are_unverified`, `test_missing_psu_connector_is_unverified_not_pass` and `test_valid_fixture_build_is_compatible`. Include exact issue-code assertions (e.g. `CPU_SOCKET_MISMATCH`, `GPU_CLEARANCE_UNKNOWN`).
- [ ] **Step 2 — RED:** `pytest tests/test_compatibility.py -q` must fail before implementing the engine.
- [ ] **Step 3 — implementation:** check socket, RAM generation, board-to-case form factor, GPU-to-case clearance, cooler-to-case clearance and socket, storage-to-board slot, GPU/PSU connectors and power feasibility. For power, use a separately named `PowerPolicy` with documented conservative system overhead rather than treating CPU TDP plus GPU board power as a certified PSU recommendation; if a required measurement is missing, use an unknown issue instead of a guessed PASS.
- [ ] **Step 4 — GREEN + negative coverage:** `pytest tests/test_compatibility.py -q` expected zero failures, including unknown and known-conflict examples.
- [ ] **Step 5 — commit:** `git add src/rigpilot/domain tests/test_compatibility.py && git commit -m "feat: add explainable deterministic compatibility checks"`.

### Task 3: Budget, stock, ownership, locks and substitution consent

**Files:**
- Create: `src/rigpilot/domain/constraints.py`, `tests/test_constraints.py`.
- Modify: `src/rigpilot/domain/models.py` (define `BuildRequest` and `ConstraintReport` according to frozen contract).

**Interfaces:**
- Consumes `BuildRequest`, `BuildSelection` and `CatalogSnapshot`.
- Produces `evaluate_constraints(request: BuildRequest, build: BuildSelection, snapshot: CatalogSnapshot) -> ConstraintReport`.
- Approval is exact `(old_id, new_id)`. There is **no persisted approval database** in this core; the future LangGraph plan owns durable interrupts and audit.

- [ ] **Step 1 — failing tests:** `test_owned_part_excluded_from_purchase_total`; `test_unknown_owned_part_does_not_prove_compatibility` (integration with Task 2); `test_missing_price_sets_budget_verified_false`; `test_unknown_stock_never_becomes_in_stock`; `test_unapproved_substitute_requires_specific_consent`; `test_approval_for_different_gpu_not_accepted`; `test_locked_product_cannot_be_replaced`; `test_over_budget_requires_explicit_decision`.
- [ ] **Step 2 — RED:** run `pytest tests/test_constraints.py -q`; expected failure before evaluator exists.
- [ ] **Step 3 — implementation:** calculate only components the customer would purchase; preserve exact money as integer VND; distinguish zero-stock vs unknown; compare requested locked parts to selected IDs; flag a replacement of the exact previous product (especially stockout) unless the exact replacement pair was approved; do not infer consent from a chat-like string. A known incompatible selected list can be reported with warning, not certified.
- [ ] **Step 4 — GREEN:** `pytest tests/test_constraints.py -q`; expected zero failures. Additionally rerun `pytest tests/test_compatibility.py -q` to catch ownership/unknown regressions.
- [ ] **Step 5 — commit:** `git add src/rigpilot/domain tests/test_constraints.py && git commit -m "feat: enforce budget inventory and customer consent constraints"`.

### Task 4: Bounded, explainable candidate optimizer

**Files:**
- Create: `src/rigpilot/domain/optimizer.py`, `tests/test_optimizer.py`.
- Modify: `src/rigpilot/domain/models.py` for `RecommendationResult` if not already declared.

**Interfaces:**
- Consumes `BuildRequest`, `CatalogSnapshot` and Task 2/3 evaluator functions.
- Produces `optimize_build(request: BuildRequest, snapshot: CatalogSnapshot, max_evaluations: int = 5000) -> RecommendationResult`.
- Candidate generation prunes known hard conflicts and uses deterministic sorted product IDs, not LLM scoring. The cap is an **engineering limit**, not a promise that 5,000 cases suffice for optimality.

- [ ] **Step 1 — failing tests:** `test_primary_workload_beats_secondary_when_constraints_equal`, `test_same_fit_tier_prefers_lower_price`, `test_owned_gpu_remains_in_candidate`, `test_locked_cpu_never_changes`, `test_missing_price_cannot_yield_recommended`, `test_unapproved_stockout_replacement_requires_approval`, `test_evaluation_cap_marks_selection_limited`, `test_no_viable_candidate_is_explicit`.
- [ ] **Step 2 — RED:** `pytest tests/test_optimizer.py -q` must fail before optimizer exists.
- [ ] **Step 3 — implementation:** enumerate deterministic combinations; prune by locked/owned constraints and known compatibility failures for normal candidates, while retaining the selected locked-in conflict as a **warned non-operational** outcome when the customer insists. Rank feasible candidates by primary workload qualitative evidence tier first, then secondary need satisfaction; for effectively equivalent evidence prefer lower total purchase price, and record which trade-off decided the outcome. Do not invent measured FPS or apply the anecdotal 5% as a constant. If no complete budget/compatibility evidence exists, output `PROVISIONAL` or `NO_CANDIDATE`, not `RECOMMENDED`. Distinguish consent-required substitution from ordinary new-build in-stock selection.
- [ ] **Step 4 — GREEN:** `pytest tests/test_optimizer.py -q` plus `pytest tests/test_compatibility.py tests/test_constraints.py -q`; expected zero failures.
- [ ] **Step 5 — commit:** `git add src/rigpilot/domain/optimizer.py src/rigpilot/domain/models.py tests/test_optimizer.py && git commit -m "feat: add bounded value-first PC build recommendation engine"`.

### Task 5: CLI end-to-end entrypoint and deterministic CI

**Files:**
- Create: `src/rigpilot/application/__init__.py`, `src/rigpilot/application/recommend.py`, `src/rigpilot/cli.py`, `tests/test_recommend_cli.py`, `.github/workflows/python-checks.yml`.
- Modify: `pyproject.toml` only for an entrypoint if needed; `README.md` only for minimal **now-verified** local run instructions.

**Interfaces:**
- Produces `recommend_from_db(request: BuildRequest, db_path: Path, snapshot_id: str | None = None) -> RecommendationResult`; it loads Task 1 snapshot and invokes Task 4 engine.
- CLI `python -m rigpilot.cli import --source <catalog.json> --db <db.sqlite>` and `python -m rigpilot.cli recommend --db <db.sqlite> --budget-vnd 25000000 --workload gaming --json`. JSON uses the frozen `RecommendationResult` names. Exit 0 for a successfully evaluated result, 2 for invalid arguments, nonzero for importer/data/runtime error; `NO_CANDIDATE` is a successful evaluation with explicit status, not a fake successful build.

- [ ] **Step 1 — failing integration tests:** `test_cli_import_then_recommend_emits_one_structured_build` (uses test-only fixture), `test_cli_known_cpu_socket_conflict_keeps_incompatible_issue`, `test_cli_missing_price_is_provisional`, `test_cli_reimport_is_idempotent`, `test_cli_rejects_bad_budget_without_creating_db` and `test_cli_output_contains_no_unsourced_fps_claim`. Execute through `subprocess.run` and parse JSON, not mocks of the optimizer.
- [ ] **Step 2 — RED:** `pytest tests/test_recommend_cli.py -q` before CLI implementation must fail.
- [ ] **Step 3 — implementation:** wire the CLI into application service, output explicit warnings/unknowns and snapshot IDs; never print secrets, misleading "compatible" summaries or pretend an agent ran. README run instructions must use commands actually exercised. Add code-only GitHub Actions Python 3.12 job that installs `.[dev]` and runs `pytest -q`. Trigger on code, test, catalog and workflow edits; avoid spending CI on docs-only PRs.
- [ ] **Step 4 — GREEN:** run `pytest -q`; expected zero failures. In fresh env run `python -m rigpilot.cli import --source tests/fixtures/catalog_test.json --db /tmp/rigpilot-plan-smoke.db` and `python -m rigpilot.cli recommend --db /tmp/rigpilot-plan-smoke.db --budget-vnd 25000000 --workload gaming --json`; parse output and verify statuses, warnings and nonzero/zero return codes. Delete the temporary DB. Confirm GitHub Actions result **only after** real run evidence.
- [ ] **Step 5 — commit:** `git add src/rigpilot/application src/rigpilot/cli.py tests/test_recommend_cli.py .github/workflows/python-checks.yml pyproject.toml README.md && git commit -m "feat: ship testable local recommendation CLI and CI"`.
- [ ] **Step 6 — PR evidence:** create a feature PR (not `main` commit), include commit SHA, imported catalog snapshot hash, source review checklist, actual tests/CI mode and any uncovered compatibility category. Do not claim OpenAI/MCP/LLM E2E has passed.

## Completion acceptance for this plan

**The first slice can be marked complete only if**, at the reviewed revision: catalog import is atomic; each fixture produces the expected compatibility, budget, stock and approval state; one deterministic build is emitted when feasible; warnings remain visible; no FPS claims are fabricated; CLI integration exercises the real SQLite reader and optimizer; and code CI is observed passing. Business/UX readiness, true optimality, live model quality and deployment readiness are **not** implied.

## Subsequent plans (separate design-driven work, not implemented here)

| Order | Next independent plan | Testable result / dependency |
|---|---|---|
| 2 | `YYYY-MM-DD-rigpilot-knowledge-mcp-plan.md` | Local ingestion: structure-aware parsing, SQLite FTS5/ChromaDB hybrid retrieval and **read-only MCP** product/stock/knowledge tools; tests for exact-model identity and source attribution. Depends on core contracts. |
| 3 | `YYYY-MM-DD-rigpilot-conversation-workflow-plan.md` | OpenAI + LangGraph typed context, consent interrupt/resume, checkpoints, bounded tools, versioned saved results, privacy-aware traces; tests for multi-turn budget/locks, stale publication and recovery. Depends on core + MCP. |
| 4 | `YYYY-MM-DD-rigpilot-customer-workspace-plan.md` | Account auth/isolation, chat and read-only PC Builder, history/restore and mobile tabs; browser E2E. Depends on conversation/version APIs. |
| 5 | `YYYY-MM-DD-rigpilot-evaluation-hardening-plan.md` | Reviewed golden cases, RAG retrieval metrics, true OpenAI CI smoke, staged E2E, concurrency/security/failure gates and measured cost/latency. Incrementally maintain deterministic tests from Plan 1 onward. |

**Do not create empty placeholder plan files.** Author each next plan under Superpowers only when its immediate prior interfaces/evidence are available for concrete planning. A specialized ShopMate reuse audit is required before copying any of its modules into those later tasks.

## Self-review / handoff

- **Spec scope:** this plan intentionally implements the independent recommendation core, *not* all V1 promises. Subsequent plans have named ownership for retrieval, agent state, UI, security and evaluation. This prevents conflating a CLI PASS with an Agentic system PASS.
- **Interface consistency:** `CatalogSnapshot` is the shared immutable input; `BuildRequest`, `BuildSelection`, `CompatibilityReport`, `ConstraintReport` and `RecommendationResult` are the only cross-task domain contracts. No agent-specific implementation details leak into the core.
- **Review Focus mapping:** critical unknown price/stock (Task 3), consent (Task 3/4), owned part (Task 2/3), conflict (Task 2/5), evidence and search cap (Task 4/5) each have explicit negative tests.
- **No execution evidence yet:** this plan was authored before any source, fixture, CLI, CI or real LLM tests were created. All expected PASS outcomes above are **future acceptance criteria**.

**Stakeholder review required:** approve or amend this plan and choose execution method. For a high-correctness domain engine, prefer Superpowers subagent-driven task implementation and independent review. Do not start Task 1 before approval.
