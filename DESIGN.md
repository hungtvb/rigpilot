# RigPilot — Visual Design System

**Status:** Design-token baseline for the **approved UI mockup v0.5** (2026-11-05); formalized in a documentation PR for review. **Design only — not application CSS or an implementation approval.**  
**Reference:** [Product & UX Design](docs/superpowers/specs/2026-11-04-rigpilot-product-design.md) §6 / v0.5 sign-off; [Decision Log](docs/DECISIONS.md) D-032–D-041 and D-062.  
**Visual source:** `rigpilot-ui-concept-v0.5.html`, standalone conversation artifact, SHA-256 `dda9e123fa20741d30cfd7ee210ad36cfcc9ddbcfa142f1d498be517d8b08aa9`. Not stored in this repo.

## 1. Ownership and guardrails

This file is the **single reference for visual tokens and reusable component appearance** across RigPilot mockups and future UI screens. Product flows, consent, warnings semantics and data truth remain owned by the **Product & UX Design**, **AI Architecture Design** and **Decision Log**. Do not repeat their functional requirements here.

- **Style direction:** restrained **Modern SaaS + Premium Hardware**; calm, precise, hardware-centric rather than gaming-themed or generic AI-dashboard decoration.
- **Layout is already signed off:** desktop Chat left / read-only PC Builder right; mobile Chat / PC Build tabs. Do not redesign it in a design-token task.
- **No competing background colors**, saturated gradients, oversized hero cards, random pills, excessive shadows, decorative emoji, or icon families mixed at the same level.
- **Use semantic tokens**, not scattered hex codes. Avoid inventing new colors and radii for individual screens; propose a change to this file for review.
- The v0.5 HTML contains accumulated overrides from v0.2–v0.5. The values below reflect the **effective final visual direction**, not the initial `:root` block or a copy of its cascading CSS.
- **Light theme only is evidenced.** Dark mode and full production-scale typography are not signed off; do not invent a dark palette and call it approved.

## 2. Color tokens

The `--rp-*` names below are **canonical design-token names**, independent of the eventual UI framework. Values are hex in sRGB. Where the v0.5 prototype used different one-off CSS selectors, use the semantic value for new design work.

| Token | Value | Role |
|---|---|---|
| `--rp-color-brand` | `#354F9A` | Primary controls, purposeful highlights |
| `--rp-color-brand-hover` | `#263C78` | Primary hover / pressed direction |
| `--rp-color-brand-subtle` | `#F1F4FA` | Low-emphasis selected/supportive surfaces |
| `--rp-color-brand-mark` | `#263B58` | Square RigPilot brand mark in v0.5 |
| `--rp-color-text-strong` | `#1B2732` | Page titles, important models and totals |
| `--rp-color-text` | `#354456` | Main body text |
| `--rp-color-text-muted` | `#647386` | Secondary text **on white surfaces** |
| `--rp-color-text-muted-canvas` | `#617080` | Safer secondary text **on canvas**; contrast-reviewed adjustment |
| `--rp-color-canvas` | `#F5F6F7` | Builder/workspace background |
| `--rp-color-surface` | `#FFFFFF` | Chat, cards, list rows, dialogs |
| `--rp-color-border` | `#E1E5E9` | Structural edges |
| `--rp-color-border-subtle` | `#E9EDEF` | Row/section dividers |
| `--rp-color-success` | `#047857` | Confirmed positive state |
| `--rp-color-success-bg` | `#ECFDF5` | Positive feedback surface |
| `--rp-color-warning` | `#925824` | Unresolved issues and caution |
| `--rp-color-warning-bg` | `#FFFAF3` | Soft caution surface |
| `--rp-color-danger` | `#B42318` | Known blockers/failures |
| `--rp-color-danger-bg` | `#FEF3F2` | Critical feedback surface |
| `--rp-color-focus` | `#3C61B9` | Visible keyboard focus ring |

**Contrast checkpoint:** sampled WCAG contrast, not a comprehensive rendered audit: brand-on-white about **7.67:1**, body-on-white **9.94:1**, warning-on-warning-bg **5.55:1**. The mockup's muted `#647386` on canvas `#F5F6F7` is approximately **4.47:1**, just below 4.5:1 for normal text; use the proposed canvas-safe `#617080` (about **4.69:1**) in that context, or validate a stronger token. Very pale metadata seen in the mockup must be audited before shipping. Do not use color alone to indicate state.

**Intended mapping (not production stylesheet):**

```css
:root {
  --rp-color-brand: #354F9A;
  --rp-color-brand-hover: #263C78;
  --rp-color-brand-subtle: #F1F4FA;
  --rp-color-brand-mark: #263B58;
  --rp-color-text-strong: #1B2732;
  --rp-color-text: #354456;
  --rp-color-text-muted: #647386;
  --rp-color-text-muted-canvas: #617080;
  --rp-color-canvas: #F5F6F7;
  --rp-color-surface: #FFFFFF;
  --rp-color-border: #E1E5E9;
  --rp-color-border-subtle: #E9EDEF;
  --rp-color-success: #047857;
  --rp-color-success-bg: #ECFDF5;
  --rp-color-warning: #925824;
  --rp-color-warning-bg: #FFFAF3;
  --rp-color-danger: #B42318;
  --rp-color-danger-bg: #FEF3F2;
  --rp-color-focus: #3C61B9;
}
```

## 3. Typography and numeric data

| Role | v0.5 visual reference | Application |
|---|---|---|
| Font | `Inter`, then system sans-serif | One family throughout; no decorative display font |
| Body baseline | 14 px / line-height ~1.5 | Mockup reference, **not a waiver** of readable production text |
| Chat messages | 13 px / line-height ~1.65 | Distinguish customer bubble vs assistant explanation |
| Primary screen title | 21–23 px / weight ~760–790 | Compact, strong hierarchy; tracking ~-0.035em |
| Budget total | 31–33 px / weight ~780 | Dominant numerical anchor; tabular digits |
| Part name / price | ~13.5 px / weight ~750 | Stronger than specs and captions |
| Part specs | ~11.5 px | Secondary information; verify contrast/readability |
| Eyebrow / metadata | ~10.5–11 px | Sparse contextual labels; do not build whole screens from tiny copy |

Prefer sentence case in Vietnamese and **clear hardware terminology**. Avoid loud uppercase tags and template-like marketing slogans. Format VND with grouped digits and a consistent `₫` suffix; use `font-variant-numeric: tabular-nums` for aligned amounts. Avoid displaying precision (e.g. FPS) without credible evidence; mock values must be labeled.

**Production adaptation:** Validate default readability, 200% zoom and long Vietnamese text before freezing implementation font sizes. Increase small labels when needed without altering the accepted hierarchy.

## 4. Spacing, shape, icon and motion tokens

| Category | Baseline / rule |
|---|---|
| Spacing rhythm | 4 px unit; prefer **4 / 8 / 12 / 16 / 20 / 24 / 32 px** |
| Surface radius | ~10–11 px for primary summary/list containers |
| Button / input radius | ~7–9 px; avoid oversized capsules by default |
| Brand mark | 36 px desktop, ~35 px mobile; square with ~9 px radius |
| Product thumb | ~54 px desktop; ~42–46 px compact mobile; consistent bounding box |
| Borders | 1 px structural, subtle dividers within the parts list |
| Shadow | None by default; minimal elevation only for true overlays |
| Icons | Single outlined SVG language, typically 17–18 px, consistent stroke |
| Focus | Visible ~3 px ring with offset; preserve native keyboard semantics |
| Touch | ≥44 × 44 px on mobile for primary interactive hit areas |
| Motion | Subtle 150–250 ms state transitions; respect `prefers-reduced-motion` |

## 5. Responsive layout contract

These are **visual breakpoints taken from v0.5**, not a prescribed future framework:

| Width | Visual behavior |
|---|---|
| **> 1100 px** | Desktop split Chat **39%** / Builder **61%**; 64 px header |
| **781–1100 px** | Compact split ~**43% / 57%**; reduced inner gutters |
| **≤ 780 px** | One visible pane at a time; **Chat / PC Build** tabs, ~58 px header; scenario selector hidden |
| **≤ 480 px** | Budget total and meter stack vertically; hardware row details wrap |
| **≤ 410 px** | Tighter brand and action spacing; visible `Lịch sử` and `Phiên mới` captions remain |
| **~320 px** | Minimum illustrated compact review width; no accidental document-wide horizontal overflow |

Maintain desktop Chat/Builder information order, independent pane scrolling and a fixed Chat composer without obscuring messages. Never auto-switch the mobile tab when a build publishes; a visible contextual action can guide the customer to PC Build. Treat mobile safe areas and large text as later production QA.

## 6. Reusable component appearance

- **App header:** one quiet horizontal bar; compact dark-blue mark + RigPilot wordmark; neutral account/action controls. No second navigation rail or hero.
- **Chat:** white primary surface, low-contrast *surface* bubble for customers, mostly plain-text assistant responses. Keep execution status to one small expandable line; illustrative steps are allowed **in the prototype only**.
- **PC Builder:** pale canvas with a single clear budget/validation panel. Components render as a **dense white list separated by dividers**, not eight floating cards.
- **Product row:** category illustration or verified photo, category, precise model label, primary spec, state/stock text and right-aligned simulated price. Illustration is not evidence of exact SKU.
- **Warnings:** whole-build summary remains visible; detailed list may be a quieter `Xem chi tiết` disclosure; relevant inline warnings stay alongside affected parts. Do not disguise a known blocking issue as success.
- **History:** timeline drawer, compact version labels and read-only preview; Restore is a separately confirmed action. No side-by-side comparison in V1.
- **Buttons:** one dominant primary action per decision point; secondary as outlined/quiet. Disabled `Đưa vào giỏ hàng` must not appear functional.
- **Status semantics:** success / warning / error / unverified require **text and/or icon** in addition to hue. Avoid using a decorative green badge as proof that a mock build is fully compatible.

## 7. Usage and change policy

1. **Design new screens:** read `AGENTS.md` and this `DESIGN.md` first; use existing color/spacing/type/component tokens.
2. **Design intent vs functional truth:** for mockups, staged Chat, history, price/stock and compatibility examples are illustrative. The real product must follow Product/AI design sources of truth and independent acceptance tests.
3. **No per-feature token forks:** when an existing token cannot serve a need, document the new role, proposed value, contrast context and screenshots in a design PR. Change this file once rather than hardcoding component-local values.
4. **Accessibility gate:** check text and non-text contrast, focus, keyboard order, mobile tap size, screen reader labeling, zoom and reduced motion. The original prototype QA is **not** full accessibility certification.
5. **Decision boundary:** the v0.5 *visual mockup* is approved (D-062). This token inventory is a faithful baseline with a small accessibility adjustment, **proposed for documentation review**, not authorization to build/merge code. Future CSS/Tailwind/React token export is an implementation concern.

