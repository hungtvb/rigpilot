# RigPilot Hybrid Knowledge Retrieval & Read-only MCP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingest locally curated technical documents into a source-traceable hybrid index and expose **four read-only local MCP tools** backed by the existing RigPilot catalog and retrieved evidence.

**Architecture:** Files on disk are curated **offline**, parsed into provenance-rich chunks, indexed in SQLite FTS5 and in local ChromaDB using explicitly supplied OpenAI embeddings. Retrieval combines exact model filters, FTS5 and semantic passages, and returns verifiable source references; a single local MCP stdio server exposes this and existing structured catalog lookups. Existing compatibility/optimizer code stays directly callable; no autonomous agent is added.

**Tech Stack:** Python 3.12, existing Pydantic 2 and SQLite catalog, SQLite FTS5, ChromaDB PersistentClient, OpenAI Embeddings API, official `mcp` Python SDK **v2** with `MCPServer` and `Client`, `pypdf`, BeautifulSoup, pytest. Confirm and pin package ranges on first execution; **do not copy deprecated v1 `FastMCP` imports**. Prefer no LangChain loader if direct libraries suffice.

**Spec:** [Approved AI Architecture & Evaluation](../specs/2026-11-04-rigpilot-ai-architecture-design.md) §§3–5, 8–10; [Product & UX](../specs/2026-11-04-rigpilot-product-design.md); [Decision Log](../../DECISIONS.md) D-045–D-051, D-055, D-058–D-060. Code dependency: Recommendation Core PR #4, pinned baseline **`81b9fe23d2019f051cb1179cdb4250781b825e1f`** as of this plan. Recheck interfaces if its SHA changes.

**Status:** PROPOSED. Spec approved, **this plan needs separate stakeholder review before implementation**. It is a docs-only follow-up; PR #4's independent review and merge gate remain unresolved.

## Global Constraints

- Before each repo task reread the **latest** branch-specific `AGENTS.md` and any nested rules; develop on a new feature branch only after plan approval.
- Product technical facts come from curated, identifiable source documents; **synthetic shop prices and stock remain authoritative only in SQLite catalog snapshots**, never RAG.
- Chat runtime must not browse the internet or mutate ingestion/indexes. Source files are added by an operator's separate local ingestion command; do not create an admin UI or automatic crawler.
- **Exact model/revision identity is a correctness gate**: RTX 4060, RTX 4060 Ti, and OC/non-OC variants cannot be merged by fuzzy search. Ambiguous shorthand yields explicit alternatives and may withhold a product-specific claim.
- Neither vector distance nor FTS rank proves a factual claim; every displayed passage has `document_id`, `chunk_id`, `source_url`, page/section, indexed source version, and effective product/revision identity.
- Missing/failed PDF text extraction or tables must be reported as `UNPARSEABLE`, not silently treated as complete. No OCR in V1.
- Source docs are untrusted text, not instructions. Do not grant access to filesystem, SQL, or other tools based on document content; do not embed account data or secrets.
- No real-time price/inventory via a document; no benchmark FPS inference, quantified performance claims, or compatibility PASS from narrative RAG passages.
- Tool surface is **one local read-only MCP server**: `search_products`, `get_product_specs`, `check_inventory`, `search_knowledge`. No `optimize_build`, `check_compatibility`, `approve`, `write`, `ingest`, or arbitrary SQL tool.
- Real OpenAI embeddings are used for a genuine build, with `text-embedding-3-small` as default. Deterministic CI injects a **fake embedding adapter**; **do not imply a real-API E2E passed unless it actually ran**. The configured embedding model and dimensions are bound to each index generation; model changes require reindexing.
- Staged index rebuild must not corrupt or expose a partially indexed generation. SQLite and Chroma have no shared transaction; publish only an entirely completed generation.
- Keep modules focused, TDD and review per task; do not introduce agent orchestration, auth, video, UI, a search cluster, dynamic multi-provider framework or cross-conversation memory in this plan.

## Review Focus — five failure classes

1. **Task 4:** Query `RTX 4060 Ti` must not cite `RTX 4060` chunks as exact-model evidence; ambiguous `RTX 4060` family requests must say what exact model is known.
2. **Tasks 2–3:** Crash after SQLite FTS commit but before Chroma vectors finish must **preserve the last active complete generation**; retry must not duplicate chunks.
3. **Task 5:** MCP tools must have no write side effects; invalid `product_id`, huge `top_k` and attempted SQL/path injections must return bounded validation errors.
4. **Tasks 1–4:** Truncated PDF tables or missing source metadata must not produce fact-like citations, `source_verified` flags, or fabricated FPS.
5. **Task 4:** Chroma unavailable or no OpenAI key: retrieval may return clearly labeled **FTS-only** evidence when a valid SQLite index exists; never claim hybrid retrieval executed or silently use a different embedding model.

## Shared file map and interfaces

| File | Single responsibility |
|---|---|
| `pyproject.toml` | Add an optional `knowledge` extra; pin tested major versions and Python 3.12 compatibility; CI installs `.[knowledge,dev]` only for affected code |
| `src/rigpilot/knowledge/models.py` | Pydantic models: SourceRecord, Chunk, SearchQuery, EvidenceHit, RetrievalResult, active IndexGeneration |
| `src/rigpilot/knowledge/parsers.py` | Curated TXT/MD/HTML/PDF text + section/table extraction, no network/OCR |
| `src/rigpilot/knowledge/chunking.py` | Structure-aware stable chunk splitting and provenance |
| `src/rigpilot/knowledge/registry.py` | SQLite `knowledge_documents`, `knowledge_chunks`, FTS5 + generation staging / publishing |
| `src/rigpilot/knowledge/vectors.py` | Embedding adapter, Chroma generation-scoped vector storage and metadata |
| `src/rigpilot/knowledge/ingest.py` | Orchestrated staged ingest, partial-failure rollback/cleanup and idempotent reindex |
| `src/rigpilot/knowledge/retrieval.py` | Exact-model disambiguation, FTS + Chroma merge, citations and fallback |
| `src/rigpilot/mcp_tools.py` | Pure, bounded read-only typed functions calling catalog/knowledge repositories |
| `src/rigpilot/mcp_server.py` | Official MCP v2 server composition and stdio entry point; stderr only for logs |
| `src/rigpilot/knowledge_cli.py` | Local operator `ingest`, `query`, `status` commands; not exposed via MCP |
| `data/knowledge/manifest.example.json` | Small sample curated source manifest; no author/invented URLs |
| `tests/fixtures/knowledge/` | Verified-looking but **explicitly synthetic test documents** for formatting and disambiguation, plus small text PDF |
| `tests/test_knowledge_parse.py` | Parsing, structure and provenance edge cases |
| `tests/test_knowledge_index.py` | FTS, atomic promotion and Chroma idempotency/failure injection |
| `tests/test_knowledge_retrieval.py` | Exact-model queries, evidence/citation, fallback and ranking |
| `tests/test_mcp_tools.py` | Pure tool validation, read-only semantics and catalog snapshot accuracy |
| `tests/test_mcp_stdio.py` | Real SDK Client ↔ MCPServer integration, JSON output and tool allowlist |
| `.github/workflows/python-checks.yml` | Run knowledge tests on relevant code/data changes; no OpenAI secret needed for default CI |

**Contracts (use exactly, refine only by reviewed plan revision):**

- `SourceRecord`: `document_id: str`, `path: Path` (import only), `source_url: str`, `publisher: str`, `source_type: Literal["manufacturer","software_requirements","benchmark_context","review"]`, `product_id: str | None`, `revision: str | None`, `publication_date: str | None`, `license_note: str | None`. Ingest validates local file existence, root confinement and HTTPS source URL; do not store local filesystem paths in user-visible evidence.
- `Chunk`: `chunk_id: str` (stable hash of document ID + version hash + structural locator + normalized content), `document_id: str`, `text: str`, `page: int | None`, `section: str | None`, `product_id: str | None`, `source_hash: str`. Keep heading and table header/units in split sections.
- `IndexGeneration`: `generation_id: str` (hash of complete manifest content + parser/chunker/schema version + embedding model/dimensions), `catalog_snapshot_id: str`, `embedding_model: str`, `dimension: int`, `status: Literal["STAGING","ACTIVE","FAILED"]`.
- `EvidenceHit`: `chunk_id`, `document_id`, `product_id`, `source_url`, `publisher`, `source_type`, `page`, `section`, `excerpt`, `evidence_kind: "DOCUMENT_PASSAGE"`, `rank` (display order only). Never expose raw vector distance as confidence probability.
- `RetrievalResult`: `hits: tuple[EvidenceHit, ...]`, `mode: Literal["HYBRID","FTS_ONLY","UNAVAILABLE"]`, `generation_id: str | None`, `warnings: tuple[str, ...]`, `ambiguous_product_ids: tuple[str, ...]`. Missing requested generation/model must be an explicit error or fallback status.

**Index publication policy:** Build a `STAGING` generation with SQLite content + FTS5 rows + Chroma vectors under generation-scoped IDs; test counts, IDs and embedding dimensions; **then** atomically change the SQLite active-generation pointer. Readers filter by the active pointer from the outset. On failure, leave old active pointer unchanged and mark staging generation `FAILED`; subsequent reindex may delete/rebuild only the failed generation. An idempotent import of identical sources/model returns the existing active generation. Only prune old generations after successful promotion and a safe grace period. Snapshot changes may require reevaluating document associations, never silently rebind a source to a different SKU.

## Task 1: Curated document parsing and structure-aware chunking

**Files:** Create `knowledge/models.py`, `parsers.py`, `chunking.py`, `__init__.py`; `tests/test_knowledge_parse.py`, `tests/fixtures/knowledge/`, `data/knowledge/manifest.example.json`; modify `pyproject.toml` only for parser extras.

**Interfaces:** `parse_source(record: SourceRecord, allowed_root: Path) -> tuple[ParsedSection, ...]`; `chunk_source(record: SourceRecord, sections: tuple[ParsedSection, ...]) -> tuple[Chunk, ...]`. Define `ParsedSection(text: str, heading: str | None, page: int | None, table_header: str | None)` in `models.py`.

- [ ] **RED:** Write `test_markdown_headings_and_tables_preserved`, `test_pdf_page_numbers_and_table_header_remain_attached`, `test_html_script_text_is_excluded`, `test_txt_source_section_is_traceable`, `test_empty_scanned_pdf_fails_as_unparseable`, `test_source_path_traversal_rejected`, `test_same_input_produces_same_chunk_ids`. Use clearly synthetic fixture docs, not fictitious official URLs.
- [ ] **Verify RED:** `pytest tests/test_knowledge_parse.py -q` → expected missing parser functions.
- [ ] **Implement:** parse only supported file extensions; avoid implicit internet fetching or OCR; split on headings/table boundaries before length caps; reject blank extraction and untrusted/out-of-root paths; preserve publisher, URL, page/section and source hash.
- [ ] **Verify GREEN + commit:** `pytest tests/test_knowledge_parse.py -q` then `pytest -q`; commit `feat: parse curated technical sources with provenance`.

## Task 2: SQLite knowledge registry, FTS5 and generation pointer

**Files:** Create `knowledge/registry.py`, `tests/test_knowledge_index.py`.

**Interfaces:** `stage_chunks(db_path: Path, generation: IndexGeneration, documents: tuple[SourceRecord, ...], chunks: tuple[Chunk, ...]) -> None`; `publish_generation(db_path: Path, generation_id: str, expected_chunks: tuple[str, ...]) -> None`; `get_active_generation(db_path: Path) -> IndexGeneration | None`; `fts_search(db_path: Path, generation_id: str, terms: str, product_id: str | None, limit: int) -> tuple[str, ...]` (ordered chunk IDs).

- [ ] **RED:** `test_fts_exact_model_tokens`, `test_fts_query_escaping_prevents_syntax_injection`, `test_staging_not_visible_to_readers`, `test_atomic_publish_fails_when_chunk_ids_missing`, `test_old_generation_survives_failed_publish`, `test_repeated_stage_has_no_duplicate_chunk_ids`, `test_registry_cannot_corrupt_catalog_tables`.
- [ ] **Verify RED:** `pytest tests/test_knowledge_index.py -q`.
- [ ] **Implement:** own knowledge tables and SQLite FTS5 (availability checked at startup); parameterize all SQL, escape/normalize FTS5 user tokens, join metadata by `generation_id` and exact `product_id`. Do **not** add new fields to existing catalog models or change product offers.
- [ ] **Verify GREEN + commit:** `pytest tests/test_knowledge_index.py -q && pytest tests/test_catalog.py -q`; commit `feat: add staged local knowledge registry and FTS5`.

## Task 3: Embeddings and Chroma generation-scoped indexing

**Files:** Create `knowledge/vectors.py`, `knowledge/ingest.py`; extend `tests/test_knowledge_index.py`, `pyproject.toml`.

**Interfaces:** `EmbeddingProvider.embed(texts: list[str]) -> list[list[float]]` (protocol). `OpenAIEmbeddingProvider(model: str = "text-embedding-3-small")` uses explicit OpenAI API key/config and returns dimensions checked against index. `index_generation(manifest: Path, catalog_db: Path, chroma_dir: Path, embedder: EmbeddingProvider) -> IndexGeneration`. `vector_search(chroma_dir: Path, generation: IndexGeneration, query_vector: list[float], product_id: str | None, limit: int) -> tuple[str, ...]`.

- [ ] **RED:** `test_chroma_persisted_vectors_roundtrip`, `test_mid_vector_failure_keeps_old_active_generation`, `test_reindex_same_generation_is_idempotent`, `test_embedding_dimension_mismatch_rejected`, `test_embedding_model_change_requires_new_generation`, `test_no_implicit_chroma_embedding_download`.
- [ ] **Verify RED:** `pytest tests/test_knowledge_index.py -q` with deterministic in-memory fake embedder; no API calls.
- [ ] **Implement:** embed explicitly (no implicit Chroma default model), save vectors to local persisted collection with `generation_id` metadata and stable chunk ID; validate counts before pointer promotion; catch retriable network failures with bounded retry in the **operator** command, not a chat tool.
- [ ] **Verify GREEN + commit:** `pytest tests/test_knowledge_index.py -q && pytest -q`; commit `feat: index vetted chunks using OpenAI and Chroma`. A separately labeled **opt-in** real OpenAI smoke test is allowed only when credentials are present and must report its exact model, costs and result.

## Task 4: Hybrid search, exact-model identity and cited evidence

**Files:** Create `knowledge/retrieval.py`, `tests/test_knowledge_retrieval.py`.

**Interfaces:** `search_knowledge(db_path: Path, chroma_dir: Path, query: str, embedder: EmbeddingProvider | None, product_id: str | None = None, top_k: int = 5) -> RetrievalResult`. Consult active generation and full `CatalogSnapshot` to validate `product_id`; if no safe exact match, return `ambiguous_product_ids` rather than silently infer a SKU.

- [ ] **RED:** `test_4060_ti_cannot_use_4060_as_exact_model_evidence`, `test_ambiguous_shorthand_returns_disambiguation`, `test_fts_only_fallback_reports_mode`, `test_generation_filter_excludes_stale_chroma_vectors`, `test_citations_include_origin_and_page`, `test_fts_and_chroma_merge_deduplicates_by_chunk_id`, `test_invalid_product_id_rejected`, `test_no_fabricated_fps_or_confidence_probability`.
- [ ] **Verify RED:** `pytest tests/test_knowledge_retrieval.py -q`.
- [ ] **Implement:** exact catalog ID aliases first; FTS5 + Chroma ranks independently, merge stable IDs via RRF (`k=60` proposal) then deduplicate and enforce product/revision filters **after** merging. If Chroma fails, return explicit `FTS_ONLY` with warning; if active SQLite generation absent, return `UNAVAILABLE`, never stale Chroma content.
- [ ] **Verify GREEN + commit:** `pytest tests/test_knowledge_retrieval.py -q && pytest -q`; commit `feat: retrieve source-grounded hybrid evidence with exact SKU filter`.

## Task 5: Read-only MCP tools, stdio contract, CLI and CI

**Files:** Create `mcp_tools.py`, `mcp_server.py`, `knowledge_cli.py`, `tests/test_mcp_tools.py`, `tests/test_mcp_stdio.py`; modify `pyproject.toml`, `.github/workflows/python-checks.yml`, `README.md` (only verified commands).

**Interfaces:** Pure functions `search_products(db: Path, query: str, kind: ComponentKind | None = None, limit: int = 10) -> dict`; `get_product_specs(db: Path, product_id: str) -> dict`; `check_inventory(db: Path, product_ids: list[str]) -> dict`; `search_knowledge_tool(db: Path, chroma_dir: Path, query: str, product_id: str | None, top_k: int = 5) -> dict`. SDK `MCPServer("RigPilot")` exposes **exactly** those four names with typed arguments and bounded limits. Local `Client` integration test exercises actual calls (in-process and stdio transport when practical); no LLM orchestrator.

- [ ] **RED:** `test_tool_allowlist_exactly_four`, `test_search_products_uses_exact_catalog_snapshot`, `test_get_product_specs_returns_provenance`, `test_check_inventory_synthetic_and_unknown_are_distinct`, `test_search_knowledge_returns_citation_metadata`, `test_read_only_calls_preserve_catalog_hash_and_active_generation`, `test_oversized_limits_and_sql_injection_are_rejected`, `test_sdk_stdio_client_calls_real_server`, `test_cli_ingest_query_status_roundtrip`. Verify tool responses carry declared state, source and snapshot identifiers.
- [ ] **Verify RED:** `pytest tests/test_mcp_tools.py tests/test_mcp_stdio.py -q`.
- [ ] **Implement:** SQLite read connections for MCP, bounded typed queries, no mutating tools, optional `RIGPILOT_DB_PATH` and `RIGPILOT_INDEX_DIR` environment config, no API key/credential in MCP response/log; send only JSON-RPC to stdout (logs to stderr). Operator CLI supports `python -m rigpilot.knowledge_cli ingest --manifest <manifest> --db <catalog.sqlite> --index-dir <chroma_dir>`, `query`, `status`. Update workflow to install `.[knowledge,dev]` and run full pytest for code/data changes.
- [ ] **Verify GREEN + commit:** `pytest tests/test_mcp_tools.py tests/test_mcp_stdio.py -q && pytest -q`, run a real local CLI import/query against known fixture files, then inspect the actual GitHub Actions run; commit `feat: expose local read-only RigPilot MCP search tools`.

## Acceptance and continuation

**Do not call this slice complete** until the reviewed head SHA demonstrates: structured document provenance, safe exact model identification, SQLite FTS5 + Chroma lookup, correct active generation under interrupted rebuild, four MCP read-only tools through SDK client, no route for customer-driven writes, and full deterministic CI. An explicit opt-in OpenAI smoke (if configured) must be recorded separately from fixture-only tests.

**Not delivered:** full LangGraph conversational workflow, compatibility writes via MCP, persistent customer memory/accounts, chat UI, production-ready search relevance or expert-reviewed benchmark judgments.

**Later:** after this plan and code are accepted, use the already approved AI design to author the separate **OpenAI/LangGraph Conversation Workflow** implementation plan. Do not merge this plan before its parent PRs or start its code without stakeholder sign-off.

## Self-review / reviewer handoff

- **Spec coverage:** data authority, multi-format source metadata, structured chunks, local Chroma/FTS hybrid, RAG evidence attribution, read-only MCP and failure behavior all have owning tasks. Actual benchmark measurement registry, customer sessions/auth and LangGraph are intentionally **separate implementation plans**.
- **Interface check:** Task 1 `SourceRecord/Chunk` → Task 2 registry → Task 3 generation-scoped vectors → Task 4 `RetrievalResult` → Task 5 MCP tools; every tool either reads the source catalog or the active knowledge generation.
- **Review focus mapped:** model disambiguation (Task 4); partial build (Tasks 2–3); MCP injections and unauthorized writes (Task 5); provenance/PDF extraction (Task 1); degraded retrieval (Task 4).
- **No execution claimed:** code, data, tests, Chroma index, MCP server and OpenAI calls in this plan are **TO-BE**. PR #4 and the approved design are its only existing code/design dependencies.
- **Technical docs checked during planning (2026-11-04):** [MCP Python SDK v2](https://py.sdk.modelcontextprotocol.io/v2/), [MCP v1→v2 migration](https://py.sdk.modelcontextprotocol.io/migration/), [Chroma Python client](https://docs.trychroma.com/reference/python), [SQLite FTS5](https://www.sqlite.org/fts5.html), [OpenAI Embeddings](https://developers.openai.com/api/docs/guides/embeddings). Pin exact tested package version in Task 1 or 3 as appropriate; no untested dependency version is asserted here.
