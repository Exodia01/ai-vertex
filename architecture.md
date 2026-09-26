# iASPIRE — Anchor 1: Financial Journal / Customer Adversary

Status: **P0 complete (contracts + fixtures). J1–J10 built; J11 not yet built.**
Spec of record: `anchor/00_MASTER_ARCHITECTURE.md` + `anchor/01_FINANCIAL_JOURNAL.md`.
Run: `python3 app.py` → http://127.0.0.1:8848
Gate: `python3 tools/gate_p0.py` · Tests: `test_mvp.py`, `test_pipeline.py`

## 0. Where we are against the master

Master §5 sprint plan, Anchor 1 column:

| Sprint | Modules | State |
|---|---|---|
| 1 | J1, J2 | built |
| 2 | J3, J4 (+J11 in parallel) | J3/J4 built · **J11 not built** |
| 3 | J5, J6 | built |
| 4 | J7, J8 | built |
| 5 | J9 | built |
| 6 | J10 + integration | J10 built · **IM-1 not met** |

P0 added what Master Sprint 1 requires of *every* anchor: shared contracts with schema
validation, a `fixtures/` package, a CI-gated synthetic-data linter, and the shared audit
envelope. Anchors 2–4 have had none of this.

## 1. What it is
A financial journal that is also an adversary. The customer says what they want in their
own words; the system infers the objective behind it, translates it into a financial
mechanism, tests that mechanism against the customer's *actual* behaviour with
deterministic math, and pushes back when it does not serve them. Nothing is stabilized
until the customer confirms it. The journal remembers everything, versioned, and
re-analyses when life changes the numbers.

## 2. The hard rule
**The LLM never does arithmetic and never states a number.** All figures come from
`j6_feasibility.py`. `narrate.py` only re-reads engine output into friend-voice Hinglish.
This makes hallucinated financial advice structurally impossible and keeps the demo
offline and instant. (Master §9 names this exact risk: J4 drifting into being the
calculator rather than the reasoner.)

## 3. Module map
| Module | File | Anchor 1 |
|---|---|---|
| Ingest, consent tags, quarantine | `j1_ingest.py` | J1 |
| Canonical snapshot, income smoothing | `j2_snapshot.py` | J2 |
| State machine + data-class tags | `j3_state.py` | J3 |
| Intent + **stated mechanism** extraction | `j4_intent.py` | J4 |
| Mechanism candidates, stated ranked first | `j5_mechanism.py` | J5 |
| Deterministic feasibility | `j6_feasibility.py` | J6 |
| Challenge + nudge cap (5) | `j7_challenge.py` | J7 |
| Stabilization + §21 event | `j8_stabilize.py` | J8 |
| Append-only versioned memory + revisions | `j9_memory.py` | J9 |
| Material-change triggers | `j10_monitor.py` | J10 |
| **Sentiment analysis** | — | **J11 (missing)** |
| Orchestrator | `pipeline.py` | §9 |
| Friend-voice narration | `narrate.py` | UX layer |
| HTTP + UI | `app.py` | §14 |

## 4. Shared contracts (P0)
`contracts/iaspire-contracts/` — `registry.json` pins v1.1 and the additive-only policy
with the N/N-1 deprecation window. Schemas for all six contracts, validated by
`tools/schema_validator.py` (stdlib draft-2020-12 subset, since `jsonschema` is absent).

Two version axes, deliberately **not** conflated:
- `state_version` — the record revision of a goal (v1, v2, v3…). Threaded from J9 into
  J8 so the emitted event can never disagree with stored memory.
- `contract_version` — the schema shape (v1 / v1.1), pinned by the registry.

`STABILIZED_JOURNAL_STATE` v1 rejects the v1.1 sentiment fields outright, which is what
makes the additive claim testable rather than aspirational.

## 5. Fixtures (P0, Master §4)
`fixtures/generate.py` emits 6 deterministic personas × 18 months (~2,300 transactions)
covering the edge cases J2/J6 name: irregular income, zero savings, negative cash flow,
windfall, debt spiral. Plus `aspirations.json` (labeled, incl. 3 ambiguous and 3
contradictory), `sentiment.json` (calm/urgent/anxious/unsure pairs + accept-vs-anxiety
contradiction), `journal_states.json` (one per §8 stage), `stabilized_goals.json`.

`tools/synthetic_linter.py` gates all of it in CI. It caught real contamination in our own
data: `mock_aa.json` named a real bank and `soul.json` a real person and city. Both are now
synthetic. Deny-lists and negative tests are exempt by explicit filename, never by
incidental substring.

## 6. UX flow — the ritual
Single column, one decision at a time. No dashboards.

1. **Raat ka Hisaab** — one free-text box, no form; greeting carries the diya streak.
2. **Maine sunha** — aspiration restated in the customer's words + confidence + `ai_hypothesis`.
3. **Maine dekha** — real numbers, collapsed: income, cash, investments, *household
   obligations*, the biggest leak, emergency months.
4. **Mera faisla** — `GO AHEAD` / `YE HO NHI SAKTA AS IS` (exact shortfall) /
   `EK GALTI MILI` (stated mechanism is wrong).
5. **Rasta ye bhi hai** → **Tera faisla** (3 buttons) → **Locked in** → **Yaad rakh liya**.
6. **Jab kuch badle** — material change re-tests every stabilized goal.

## 7. Why the adversary is not a yes-machine
`j4_intent` extracts the customer's **stated** mechanism, not just their objective.
`j5_mechanism` ranks it **first**. `j6_feasibility` judges it on its own merits, so "I will
save 3L for medical emergencies" is challenged even though a feasible alternative exists.
Without this the system would silently substitute its own answer and call it the customer's.

## 8. Known gaps (honest)
- **J11 sentiment is not built.** J7 tone, J8 `contradiction_note`, J10 `priority.raised`
  and contract v1.1's sentiment bands are all specified and wired as *hooks* only.
- **J2 does not model irregular income.** The 3-month window excludes the off-season dip,
  so `income_min_month` reads 198k instead of ~110k. Persona 1's defining risk is invisible
  to the engine. `obligations_monthly` is still hardcoded, not derived from records.
- **J6 thresholds are unjustified.** `0.4 × income` and the 4-month emergency floor are
  invented, undocumented, and untested against edge personas.
- **J4 has no accuracy measurement** and contradictory inputs still resolve by keyword
  count rather than a clarifying question.
- **J5 has no rubric.** J7 has no property test and its challenge string is still English
  inside a Hinglish UX. J10 has no threshold boundary tests.
- **Audit envelope is emitted but not yet queryable as one store**; `pipeline.audit` still
  keeps a second flat view for the UI.
- `banking_map.json` is dead config — the mechanism table lives in `j5_mechanism.py`.
- Society/segment comparison is Anchor 2 and intentionally absent. No fabricated aggregates.
- No auth, single-tenant, in-memory session streak.

