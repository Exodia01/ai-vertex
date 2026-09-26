# Anchor 1 — Financial Journal / Customer Adversary

## 1. Purpose
Be the customer's financial memory and the customer-side adversarial intelligence layer:
understand what a customer actually wants, translate it into its banking/financial
equivalent, test it against reality, and only stabilize an interpretation once the customer
has accepted, rejected, or modified it. This anchor is the sole system of record for
individually identifiable customer financial data.

## 2. Scope
- Ingesting permissioned customer financial data (accounts, transactions, balances).
- Understanding natural-language aspirations and classifying underlying intent.
- Converting aspirations into banking/financial equivalents.
- Deterministic feasibility analysis using historical behavior.
- Generating a bounded number of severity-governed nudges and deeper analysis on request.
- Recording customer acceptance/rejection/modification and producing a stabilized state.
- Maintaining financial memory and re-triggering analysis on material change.

## 3. Non-Goals
- Not a general-purpose chatbot; conversation is always anchored to a specific aspiration
  or financial state change.
- Not the source of aggregate/segment intelligence (that is Anchor 2).
- Not a policy or product design system (Anchors 3–4).
- Not a replacement for licensed financial advice; recommendations are informational and
  always customer-confirmable, never auto-executed.

## 4. Core Concepts
- **Aspiration**: a customer's expressed want, in their own words.
- **Objective**: the underlying need the AI infers behind the aspiration (e.g., "healthcare
  protection" behind "₹3L saved for emergencies").
- **Banking Equivalent**: the financial mechanism that could serve the objective (savings
  goal, insurance, EMI, reserve fund, etc.).
- **Feasibility Analysis**: deterministic evaluation of whether a mechanism achieves the
  objective given the customer's actual financial behavior.
- **Challenge**: a structured, evidence-backed pushback when the customer's stated
  mechanism is unrealistic or suboptimal.
- **Alternative**: a concretely specified other path to the same objective.
- **Stabilized State**: the customer-confirmed version of an aspiration, eligible for
  downstream aggregation.
- **Financial Memory**: the durable, versioned record of how aspirations evolved over time.
- **Nudge**: a proactive, severity-gated notification; capped at ~4–5 per aspiration/event
  unless the customer asks for more.
- **Sentiment Signal**: an AI-derived, always-hypothesis-tagged read of stress, urgency,
  frustration, and confidence around an aspiration or journal event. An annotation on top
  of existing entries, not a gate on any state transition.

## 5. Actors
- **Customer** — the source of aspirations and the sole authority on stabilization.
- **Journal AI (reasoning layer)** — classifies intent, drafts banking equivalents,
  generates challenges/alternatives, writes explanations.
- **Deterministic Finance Engine** — owns all numeric calculations (feasibility, projections,
  gap sizing). Never delegated to the LLM.
- **Nudge Governor** — enforces the nudge-count and severity policy.
- **Consent & Access Layer** — enforces what data may be read and what may later leave the
  Journal boundary.

## 6. Inputs
- Permissioned account/transaction feeds (balances, income, recurring obligations).
- Customer natural-language statements (aspirations, responses to challenges).
- Customer decisions (accept / reject / modify).
- General/external knowledge needed for feasibility context (e.g., typical costs), sourced
  through a controlled retrieval layer, not open-ended browsing.
- Material-event triggers (large transaction, income change, new dependent, etc.).

## 7. Outputs
- `STABILIZED_JOURNAL_STATE` events (to Anchor 2).
- Customer-facing nudges and analysis responses.
- Financial memory records (internal, versioned, queryable by the customer only).
- Audit events (internal).

## 8. State Model

```
raw_observation
   → interpreted_expectation
      → banking_equivalent
         → analysis (deterministic feasibility run)
            → challenge (if gap/risk found)
               → alternative(s) offered
                  → customer_response (accept | reject | modify)
                     → stabilized_state
                        → monitoring
                           → re_analysis (on material change) → back to analysis
         → [no gap found] → stabilized_state directly
```

Additional lifecycle tags applied orthogonally to any node above:
- **observed_data** vs **inferred_data** vs **ai_hypothesis** vs **customer_confirmed_data**
  vs **customer_rejected_interpretation**
- Aspiration status: **active** / **completed** / **abandoned**
- State scope: **current_financial_state** vs **historical_state** (append-only history,
  never overwritten)

## 9. Detailed Functional Flow
1. Ingest and normalize account/transaction data (J1, J2).
2. Customer expresses an aspiration in natural language; Journal AI extracts intent (J4).
3. Intent is mapped to one or more banking equivalents (J5).
4. Deterministic Finance Engine runs feasibility against real behavior (J6).
5. If a gap, risk, or better mechanism exists, generate a challenge with 1+ concrete
   alternatives (J7); if not, proceed straight to stabilization.
6. Customer accepts, rejects, or modifies; loop back to step 3/4 if modified.
7. On acceptance, write a stabilized state and emit `STABILIZED_JOURNAL_STATE` (J8).
8. Persist to financial memory, versioned (J9).
9. Monitor for material changes; re-trigger analysis when they occur (J10).
10. Nudge Governor caps proactive interventions per aspiration; customer can always request
    deeper analysis on demand, uncapped.
11. In parallel with step 2 onward, Sentiment Analysis (J11) tags each aspiration/response
    with a `SentimentSignal`. It runs alongside J4, not inside the state machine — it never
    blocks or reorders steps 1–10; it only feeds them as an input signal (nudge tone in J7,
    a contradiction check in J8, priority weighting in J10).

## 10. Data Model (key entities)
- `Customer { customer_id, consent_scope[], risk_profile }`
- `FinancialSnapshot { customer_id, as_of, balances[], recurring_obligations[], income_profile }`
- `Aspiration { aspiration_id, customer_id, raw_text, created_at, status }`
- `JournalEntry { entry_id, aspiration_id, state, data_class(observed|inferred|hypothesis|
  confirmed|rejected), payload, evidence_ref, created_at }`
- `FeasibilityResult { aspiration_id, mechanism, feasible(bool), gap_amount, risk_notes,
  computed_by: "deterministic_engine", version }`
- `Alternative { aspiration_id, description, mechanism, tradeoffs }`
- `StabilizedGoal { goal_id, aspiration_id, customer_id, objective, mechanism, target,
  timeline, confirmed_at, version }`
- `NudgeLog { aspiration_id, nudge_count, last_severity, last_sent_at }`
- `SentimentSignal { entry_id, aspiration_id, stress, urgency, frustration, confidence,
  evidence_snippet, data_class: "ai_hypothesis", detected_at }` — attached to a
  `JournalEntry` or customer response; append-only alongside the entry it annotates, so it
  inherits J9's existing versioned history with no new storage system.

## 11. AI Responsibilities
- Natural-language understanding of aspirations and customer responses.
- Intent classification (objective vs. stated mechanism).
- Drafting banking-equivalent candidates.
- Composing challenge/alternative explanations in plain language.
- Summarizing financial memory on request.
- Detecting sentiment (stress/urgency/frustration/confidence) from aspiration text and
  customer responses, always as a read-only annotation, never a gate on a transition.
AI output is always tagged `ai_hypothesis` until customer-confirmed.

## 12. Deterministic Computation Responsibilities
- All numeric feasibility math (gap sizing, projections, affordability checks).
- All historical aggregation used as evidence (spend totals, cash-flow trends).
- Threshold checks that trigger a challenge vs. silent stabilization.
LLMs read these outputs as evidence; they never recompute or override them.

## 13. Privacy/Security Requirements
- All individually identifiable data stays within the Journal boundary by default.
- Consent scope enforced per data field, not just per customer.
- Only `STABILIZED_JOURNAL_STATE` (defined in §21) may cross the boundary, and only through
  the Anchor 2 contract.
- Encryption at rest and in transit; per-tenant key isolation.
- Full audit trail on every read of raw financial data.

## 14. API/Event Contracts
- `POST /aspirations` (customer statement in)
- `POST /aspirations/{id}/response` (accept/reject/modify)
- `GET /journal/memory` (customer-facing history)
- Emitted event: `STABILIZED_JOURNAL_STATE` (see Anchor 2 contract in §21) — versioned,
  schema-validated, published to the shared `iaspire-contracts` topic.

## 15. Failure Modes
- Feasibility engine unavailable → challenge generation is deferred, aspiration stays in
  `analysis_pending`, customer is informed rather than shown a silent or guessed result.
- Ambiguous intent extraction → Journal asks a single clarifying question rather than
  guessing an objective.
- Consent withdrawal mid-flow → immediate purge of downstream-eligible flags; any already
  emitted `STABILIZED_JOURNAL_STATE` is retracted via a tombstone event to Anchor 2.
- Nudge governor failure → fails closed (no nudge sent) rather than failing open (spam).

## 16. Observability
- Per-stage funnel metrics (raw → interpreted → challenged → stabilized → abandoned).
- Nudge volume vs. cap, by severity band.
- Feasibility-engine latency and error rate (numeric correctness is safety-critical).
- Intent-classification confidence distribution, flagged when trending down.

## 17. Auditability
- Every state transition recorded with actor (customer/AI/deterministic engine), evidence
  reference, and timestamp, using the shared audit event envelope.
- Full replay capability: given a `goal_id`, reconstruct the entire decision path.

## 18. Testing Strategy
- Unit tests per module (J1–J10).
- Golden-fixture tests for intent extraction against ambiguous/contradictory aspirations.
- Deterministic-engine tests are exact-value assertions, not fuzzy/LLM-graded.
- Property tests: nudge count never exceeds cap outside explicit customer request.
- Privacy tests: confirm no raw transaction line ever appears in an emitted
  `STABILIZED_JOURNAL_STATE` payload.

## 19. Scalability Considerations
- Per-customer state is independently shardable by `customer_id`.
- Feasibility computation is stateless and horizontally scalable.
- Financial memory is append-only, enabling cheap replication and time-travel queries.

## 20. Dependency Map
- Upstream: external account/transaction data providers (outside this plan's scope).
- Downstream: Anchor 2 (sole consumer of `STABILIZED_JOURNAL_STATE`).

## 21. Interface Contract with Anchor 2
`STABILIZED_JOURNAL_STATE` (v1) fields: `customer_ref` (opaque, non-reversible outside
Anchor 1), `objective_category`, `mechanism_category`, `feasibility_outcome`
(feasible/gap/at-risk), `coarse_target_band`, `coarse_timeline_band`, `confirmed_at`,
`state_version`. Explicitly excluded: raw transaction data, account numbers, exact income,
free-text aspiration content, name/contact details.

**v1.1 addition (additive, backward-compatible):** `coarse_sentiment_band` — a bucketed
category (e.g., `low_stress` / `moderate_stress` / `high_stress`, plus a separate
`confidence_band`), never a raw score or free text. Optional field; consumers on v1 ignore
it safely. This is the only sentiment-related data permitted to cross the Anchor 1/2
boundary — no raw sentiment text, no per-message stress scores, no `contradiction_note`
content ever leaves Anchor 1.

## 22. MVP Boundary
J1–J8 fully built; J9 basic (append-only, no advanced querying); J10 limited to a small
fixed set of material-change triggers (large withdrawal, income drop).

## 23. Future Extensions
- Richer material-change detection (life events inferred from spending pattern shifts).
- Multi-goal trade-off reasoning (competing aspirations sharing the same cash flow).
- Customer-facing "what-if" simulation sandbox built on the deterministic engine.

---

## Modular Sprints

### J1 — Financial Data Ingestion
- **Objective:** Reliably ingest permissioned account/transaction feeds.
- **Scope:** Connectors, schema validation, consent-scope tagging on ingest.
- **Inputs:** Raw provider feeds.
- **Outputs:** Normalized raw records tagged `observed_data`.
- **APIs/events:** `ingest.transaction.received`, `ingest.account.received`.
- **Data structures:** `RawTransaction`, `RawAccountSnapshot`.
- **Dependencies:** External provider access (out of scope).
- **Acceptance criteria:** 100% of ingested records pass schema validation or land in a
  quarantine queue with reason codes; zero silent drops.
- **Unit tests:** Schema validation edge cases (missing fields, malformed currency).
- **Integration tests:** End-to-end feed → normalized store.
- **Security/privacy tests:** Consent-scope tag present on every record; quarantine queue
  access-controlled.
- **Demo scenario:** Ingest a synthetic customer's 12-month transaction history.
- **Definition of Done:** Ingestion pipeline runs on synthetic fixtures with zero unhandled
  errors and full consent tagging.

### J2 — Financial Normalization
- **Objective:** Convert heterogeneous raw records into a canonical `FinancialSnapshot`.
- **Scope:** Currency/date normalization, obligation categorization, income smoothing for
  irregular earners.
- **Inputs:** Normalized raw records from J1.
- **Outputs:** `FinancialSnapshot`.
- **APIs/events:** `snapshot.updated`.
- **Data structures:** `FinancialSnapshot`.
- **Dependencies:** J1.
- **Acceptance criteria:** Snapshot reconciles to source totals within defined tolerance.
- **Unit tests:** Irregular-income smoothing, multi-currency accounts.
- **Integration tests:** J1 → J2 pipeline on fixture set.
- **Security/privacy tests:** No raw account numbers persisted in snapshot.
- **Demo scenario:** Produce a snapshot for a gig-worker persona with irregular income.
- **Definition of Done:** Snapshot generation passes reconciliation tests on all fixture
  personas.

### J3 — Journal State Model
- **Objective:** Implement the full state machine (§8) as a versioned, queryable model.
- **Scope:** State transitions, data-class tagging, append-only history.
- **Inputs:** J2 snapshots, customer events.
- **Outputs:** `JournalEntry` records.
- **APIs/events:** `journal.state.transitioned`.
- **Data structures:** `JournalEntry`.
- **Dependencies:** J2.
- **Acceptance criteria:** Every legal transition in §8 is representable; illegal
  transitions are rejected at the model layer.
- **Unit tests:** All transition edges, including rejected-interpretation loop-back.
- **Integration tests:** Full lifecycle replay from raw to stabilized on a fixture.
- **Security/privacy tests:** Data-class tag enforced on every write.
- **Demo scenario:** Replay one aspiration end-to-end through every state.
- **Definition of Done:** State machine passes all transition unit tests and one full
  replay integration test.

### J4 — Intent Extraction
- **Objective:** Classify the underlying objective behind a natural-language aspiration.
- **Scope:** NL understanding only; output is always tagged `ai_hypothesis`.
- **Inputs:** Raw aspiration text.
- **Outputs:** `{objective_category, confidence, evidence_snippets}`.
- **APIs/events:** `intent.extracted`.
- **Data structures:** `IntentHypothesis`.
- **Dependencies:** J3.
- **Acceptance criteria:** ≥ target accuracy on labeled fixture set; low-confidence cases
  trigger a clarifying question instead of a guess.
- **Unit tests:** Ambiguous and contradictory aspiration fixtures.
- **Integration tests:** J3 → J4 → state transition to `interpreted_expectation`.
- **Security/privacy tests:** No PII leaked into model prompts beyond what's needed.
- **Demo scenario:** "I want to protect my parents from medical expenses" → objective =
  healthcare protection, not "savings."
- **Definition of Done:** Passes accuracy threshold on fixture set; clarifying-question
  path verified.

### J5 — Banking-Equivalent Classifier
- **Objective:** Map an objective to one or more candidate financial mechanisms.
- **Scope:** Candidate generation only; feasibility judged in J6.
- **Inputs:** `IntentHypothesis`.
- **Outputs:** `MechanismCandidate[]`.
- **APIs/events:** `mechanism.candidates.generated`.
- **Data structures:** `MechanismCandidate`.
- **Dependencies:** J4.
- **Acceptance criteria:** For each fixture objective, at least one clinically sensible
  mechanism is proposed (validated by rubric, not just present).
- **Unit tests:** Multi-mechanism objectives (e.g., healthcare → insurance + reserve).
- **Integration tests:** J4 → J5 pipeline.
- **Security/privacy tests:** N/A beyond standard data handling.
- **Demo scenario:** Vehicle purchase aspiration → savings vs. alternative financing
  candidates.
- **Definition of Done:** Rubric-validated candidate generation on full fixture set.

### J6 — Feasibility Engine (Deterministic)
- **Objective:** Compute, deterministically, whether each mechanism candidate achieves the
  objective given the customer's real financial behavior.
- **Scope:** Pure numeric computation; no LLM involvement in the calculation itself.
- **Inputs:** `MechanismCandidate[]`, `FinancialSnapshot`.
- **Outputs:** `FeasibilityResult`.
- **APIs/events:** `feasibility.computed`.
- **Data structures:** `FeasibilityResult`.
- **Dependencies:** J2, J5.
- **Acceptance criteria:** Exact, reproducible numeric outputs given identical inputs;
  no randomness.
- **Unit tests:** Exact-value assertions across all fixture personas and edge cases (zero
  savings, negative cash flow, windfall).
- **Integration tests:** J5 → J6 → challenge trigger decision.
- **Security/privacy tests:** N/A (no external data exposure at this stage).
- **Demo scenario:** ₹3L Japan trip goal against a persona with insufficient savings rate —
  engine returns exact gap amount.
- **Definition of Done:** 100% exact-match on a reproducibility test suite; reviewed by a
  human for calculation correctness.

### J7 — Customer Challenge/Nudge Engine
- **Objective:** Turn a feasibility gap/risk into a structured challenge with alternatives,
  governed by the nudge cap.
- **Scope:** Challenge composition, alternative drafting, nudge-count enforcement. Reads
  `SentimentSignal` (J11) as an input: a high-stress signal softens tone and reduces nudge
  frequency/severity; a high-confidence signal permits more direct, actionable phrasing.
  Sentiment adjusts *how* a nudge is delivered, never *whether* the underlying gap is real.
- **Inputs:** `FeasibilityResult`, `NudgeLog`, `SentimentSignal` (optional; degrades
  gracefully to default tone if absent).
- **Outputs:** `Challenge`, `Alternative[]`, updated `NudgeLog`.
- **APIs/events:** `challenge.issued`, `nudge.sent`.
- **Data structures:** `Challenge`, `Alternative`, `NudgeLog`.
- **Dependencies:** J6.
- **Acceptance criteria:** Nudge count per aspiration never exceeds cap absent explicit
  customer request for more analysis.
- **Unit tests:** Cap enforcement at boundary (5th vs. 6th nudge).
- **Integration tests:** Full gap → challenge → customer response loop.
- **Security/privacy tests:** N/A.
- **Demo scenario:** Healthcare-reserve example from product thesis, producing an
  insurance+reserve alternative.
- **Definition of Done:** Cap enforcement property test passes; challenge content reviewed
  for tone/clarity.

### J8 — Customer Confirmation / Stabilization
- **Objective:** Record accept/reject/modify and produce a `StabilizedGoal`.
- **Scope:** Confirmation handling, modification loop-back, stabilization write. Reads
  `SentimentSignal` (J11) as a secondary validation signal alongside the explicit
  response: if sentiment repeatedly shows anxiety/stress against an aspiration the
  customer has just explicitly accepted, stabilization still proceeds (explicit
  confirmation always wins) but a `contradiction_note` is attached and one gentle
  follow-up check-in is scheduled. Sentiment never blocks or reverses stabilization on
  its own.
- **Inputs:** Customer response, `Challenge`/`Alternative`, `SentimentSignal` (optional).
- **Outputs:** `StabilizedGoal`, `STABILIZED_JOURNAL_STATE` event, `contradiction_note`
  (when applicable).
- **APIs/events:** `goal.stabilized`.
- **Data structures:** `StabilizedGoal`.
- **Dependencies:** J7.
- **Acceptance criteria:** Modify path correctly loops back to J5/J6 rather than
  force-stabilizing; emitted event matches the §21 contract exactly; a sentiment/explicit
  contradiction never blocks stabilization, only annotates it.
- **Unit tests:** All three response types; a contradiction case (explicit accept +
  repeated high-stress signal) correctly stabilizes while attaching a `contradiction_note`.
- **Integration tests:** Full pipeline J1→J8 on fixture set; schema-validate emitted event.
- **Security/privacy tests:** Confirm excluded fields (per §21) never appear in the event
  payload.
- **Demo scenario:** Customer modifies target amount; system re-runs feasibility before
  re-offering stabilization.
- **Definition of Done:** Emitted events pass shared-contract schema validation in CI.

### J9 — Financial Memory
- **Objective:** Durable, versioned, queryable history of aspiration evolution.
- **Scope:** Append-only storage, customer-facing query API.
- **Inputs:** All prior module outputs.
- **Outputs:** Queryable memory store.
- **APIs/events:** `GET /journal/memory`.
- **Data structures:** Versioned `JournalEntry`/`StabilizedGoal` history.
- **Dependencies:** J3, J8.
- **Acceptance criteria:** No record is ever overwritten; every version is retrievable.
- **Unit tests:** Version retrieval, tombstone-on-consent-withdrawal.
- **Integration tests:** Multi-version aspiration replay.
- **Security/privacy tests:** Access restricted to the owning customer.
- **Demo scenario:** Customer queries "how has my Japan trip goal changed over time."
- **Definition of Done:** Full history retrievable and correctly ordered on a fixture with
  three revisions.

### J10 — Continuous Monitoring
- **Objective:** Detect material financial changes and re-trigger analysis.
- **Scope:** A small, explicit set of MVP triggers (large withdrawal, income drop);
  extensible design for more later. A sudden spike in stress/frustration from J11 is
  itself treated as a (lower-weight) trigger candidate — it can prioritize an entry for
  earlier human/AI attention but, unlike the financial triggers, never re-runs the
  deterministic feasibility engine on its own.
- **Inputs:** Ongoing `FinancialSnapshot` updates, `SentimentSignal` (optional, priority
  input only).
- **Outputs:** `reanalysis.triggered` event (financial triggers), `priority.raised` event
  (sentiment-only triggers).
- **APIs/events:** `reanalysis.triggered`.
- **Data structures:** `MaterialChangeTrigger`.
- **Dependencies:** J2, J8.
- **Acceptance criteria:** Defined triggers fire reliably; no trigger storms (rate-limited
  per customer).
- **Unit tests:** Trigger threshold boundary tests.
- **Integration tests:** Snapshot change → re-analysis → new challenge cycle.
- **Security/privacy tests:** N/A.
- **Demo scenario:** Sudden large expense triggers re-evaluation of an active goal.
- **Definition of Done:** Trigger set validated against fixture edge cases with no false
  positive storms.

### J11 — Sentiment Analysis
- **Objective:** Detect stress, urgency, frustration, and confidence in aspiration text
  and customer responses, and expose it as a read-only annotation to J7, J8, and J10 —
  without gating or reordering any state transition.
- **Scope:** Runs parallel to J4 (Intent Extraction), reading the same raw text. Produces
  `SentimentSignal` records attached to the relevant `JournalEntry`/response. Tracks
  sentiment trend over time by riding J9's existing versioned history (no new store).
- **Inputs:** Raw aspiration text, customer responses to challenges.
- **Outputs:** `SentimentSignal { stress, urgency, frustration, confidence,
  evidence_snippet }`, always tagged `ai_hypothesis`.
- **APIs/events:** `sentiment.detected`.
- **Data structures:** `SentimentSignal`.
- **Dependencies:** J3 (for entry attachment), J4 (shares the same input text, run in
  parallel — no ordering dependency).
- **Acceptance criteria:** Sentiment detection never blocks, delays, or reorders any J1–J10
  transition; a `SentimentSignal` failure degrades gracefully (J7/J8/J10 fall back to
  default behavior with no sentiment input) rather than failing the pipeline.
- **Unit tests:** Detection accuracy on labeled fixture set (calm/urgent/anxious/confident
  phrasings); graceful-degradation test when the module errors out.
- **Integration tests:** J11 running alongside J4–J8 on the full fixture set, confirming
  no change to stabilization outcomes when sentiment is absent vs. present (except the
  tone/priority effects it's explicitly meant to have).
- **Security/privacy tests:** Confirm `SentimentSignal` content (raw text, scores) never
  crosses the Anchor 1/2 boundary — only the bucketed `coarse_sentiment_band` (§21) does.
- **Demo scenario:** Same aspiration expressed calmly vs. urgently ("I'd like a car
  someday" vs. "I urgently need a car") produces different `SentimentSignal` values and,
  downstream, different nudge tone in J7.
- **Definition of Done:** Detection accuracy threshold met on fixture set; graceful-
  degradation and boundary-exclusion tests pass in CI.
