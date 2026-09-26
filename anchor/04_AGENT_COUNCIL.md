# Anchor 4 — Council of Agents

## 1. Purpose
Provide multi-perspective, structured deliberation and management of policy proposals at a
scale beyond manual human review, without fabricating consensus and without descending into
uncontrolled agent-to-agent conversation.

## 2. Scope
- Consuming `POLICY_PROPOSAL` from Anchor 3.
- Running a structured, bounded deliberation across a defined agent topology.
- Recording positions, objections, evidence requests, simulations, and decision rationale.
- Producing `VALIDATED_POLICY_DECISION` back to Anchor 3.

## 3. Non-Goals
- Does not generate policy candidates itself (Anchor 3's job) — it only deliberates on
  what it receives.
- Does not access individual customer data.
- Not a free-form chatbot debate; every exchange is a structured message against a
  specific proposal field.

## 4. Core Concepts
- **Agent**: a bounded reasoning role representing one institutional/customer perspective,
  operating only on the structured proposal and any explicitly requested evidence.
- **Position**: an agent's structured stance (support / object / insufficient-evidence)
  on a proposal, with rationale.
- **Objection / Counterargument**: a structured challenge to another agent's position or
  to the proposal itself.
- **Evidence Request**: a structured ask for more data before an agent can commit to a
  position (routed back to Anchor 3, never fabricated).
- **Deliberation Record**: the complete, immutable transcript of a proposal's council
  review.
- **Decision**: the council's final structured output — never a summarized "everyone
  agreed" unless agreement is genuinely unanimous and evidenced.

## 5. Actors — Minimum Useful Agent Topology (MVP)
Starting minimal set (per the "determine the minimum useful topology" instruction — not
all 12 candidate agents are load-bearing for MVP):
- **Customer Advocate** — represents customer outcome/fairness.
- **Risk Agent** — credit/operational/reputational risk.
- **Economics Agent** — cost/benefit/scale viability for the institution.
- **Compliance Agent** — regulatory feasibility.
Deferred to post-MVP (OPEN DECISION, see Master doc): Product, Operations, Servicing,
Data Privacy, Credit, Insurance, Treasury/Economics split-out, Fairness/Customer Outcome
as a separate agent from Customer Advocate. Each additional agent should be added only when
a concrete policy class demonstrates the existing four are insufficient (e.g., a proposal
with heavy servicing complexity surfaces the need for an Operations Agent).

## 6. Inputs
`POLICY_PROPOSAL` (Anchor 3).

## 7. Outputs
`VALIDATED_POLICY_DECISION` (to Anchor 3), including full `DeliberationRecord`.

## 8. State Model
```
proposal_received
   → positions_gathered (each agent: support | object | insufficient_evidence)
      → objections_raised
         → evidence_requested (optional, loops back to Anchor 3, pauses deliberation)
            → evidence_received → positions_re-gathered
         → simulation_requested (optional, routes to Anchor 3's simulation engine)
            → simulation_received → positions_re-gathered
      → council_deliberation (structured exchange of objections/counterarguments only)
         → decision_reached
            → [unanimous support] → APPROVE
            → [unresolved conflict] → ESCALATE (human decision required)
            → [insufficient evidence across agents] → RETURN_TO_ANCHOR3 (needs more evidence)
```

## 9. Detailed Functional Flow
1. Receive and validate `POLICY_PROPOSAL` (C1).
2. Each agent independently evaluates the proposal against its perspective and produces a
   structured `Position` (C2).
3. Agents raise structured objections/counterarguments against specific proposal fields or
   other agents' positions — not open conversation (C3).
4. If any agent lacks sufficient evidence, an `EvidenceRequest` is issued back toward
   Anchor 3 rather than the agent guessing (C4).
5. If a proposal's risk/economics is contested, a simulation is requested (C4/C5, reusing
   Anchor 3's simulation engine via a defined call).
6. A deliberation coordinator runs bounded rounds of objection/counterargument until
   positions stabilize or a round limit is hit (C5).
7. Decision is recorded: approve, escalate to human, or return for more evidence — never a
   fabricated consensus (C6).
8. Full `DeliberationRecord` persisted (C7).
9. `VALIDATED_POLICY_DECISION` emitted to Anchor 3, including monitoring metrics and
   review/expiry date (C8).

## 10. Data Model
```
Position { policy_id, agent, stance (support|object|insufficient_evidence), rationale,
           evidence_refs[], created_at }
Objection { policy_id, from_agent, target (proposal_field|agent_position), content,
            created_at }
EvidenceRequest { policy_id, requesting_agent, requested_data, status, resolved_at }
SimulationRequest { policy_id, requesting_agent, parameters, result_ref }
DeliberationRecord { policy_id, positions[], objections[], evidence_requests[],
                     simulation_requests[], rounds, unresolved_questions[], decision }
VALIDATED_POLICY_DECISION {
  policy_id, decision (approve|escalate|return_for_evidence), rationale,
  agent_positions_summary[], dissent_record[], confidence, conditions[],
  monitoring_metrics[], expiry_review_date, contract_version
}
```

## 11. AI Responsibilities
- Each agent's evaluation and rationale drafting from its assigned perspective.
- Drafting objections/counterarguments grounded in the proposal's actual fields.
- Drafting the human-readable summary of the deliberation record.
Agents may only assert `support`/`object`/`insufficient_evidence` — they cannot silently
default to support when uncertain.

## 12. Deterministic Computation Responsibilities
- Round-limit enforcement in deliberation (prevents infinite/uncontrolled exchange).
- Decision-rule evaluation (what combination of positions yields approve / escalate /
  return-for-evidence) — a fixed rule, not an LLM judgment call.
- Consensus-fabrication guard: a deterministic check that a recorded "unanimous" decision
  actually has one `Position` per required agent, all `support`, with no unresolved
  objections outstanding.

## 13. Privacy/Security Requirements
- Operates exclusively on `POLICY_PROPOSAL` (aggregate-derived); no individual customer
  data reachable from this anchor at all.
- All evidence requests route through Anchor 3, never directly to Anchor 1 or 2.
- Full immutable audit trail of every position, objection, and decision.

## 14. API/Event Contracts
- Consumes: `POLICY_PROPOSAL` (Anchor 3).
- Produces: `VALIDATED_POLICY_DECISION` (to Anchor 3).
- Internal: `EvidenceRequest` / `SimulationRequest` (routed back to Anchor 3's P6/P1 as a
  synchronous or async call, per integration design).

## 15. Failure Modes
- An agent fails to respond → proposal held at `positions_gathered`, not silently treated
  as support.
- Round limit reached with unresolved objections → `ESCALATE`, never forced to `APPROVE`.
- Evidence request unanswered past a timeout → `RETURN_TO_ANCHOR3`, not a stalled proposal.

## 16. Observability
- Decision distribution (approve / escalate / return-for-evidence) over time.
- Per-agent objection rate (an agent that never objects may indicate a broken evaluation
  path, not genuine agreement).
- Average rounds-to-decision.

## 17. Auditability
- Every `DeliberationRecord` is immutable and fully replayable.
- Dissent is explicitly preserved even when the overall decision is approve (a dissenting
  agent's position and rationale are never dropped from the record).

## 18. Testing Strategy
- Consensus-fabrication guard tests: attempt to force an `APPROVE` with a missing agent
  position or an unresolved objection; must fail.
- Round-limit tests.
- Fixture transcripts for each outcome type (unanimous approve, unresolved conflict,
  insufficient-evidence rejection) — see Master doc §4.
- Evidence-request round-trip tests (request → Anchor 3 fixture response → re-evaluation).

## 19. Scalability Considerations
- Deliberation is per-proposal and independently parallelizable across proposals.
- Agent evaluation calls are stateless per round, enabling horizontal scaling under high
  proposal volume from Anchor 3.

## 20. Dependency Map
- Upstream: Anchor 3 (`POLICY_PROPOSAL`, and evidence/simulation responses).
- Downstream: Anchor 3 (`VALIDATED_POLICY_DECISION`).

## 21. Interface Contracts with Other Anchors
- **From Anchor 3:** `POLICY_PROPOSAL` (v1) — full structure required; a proposal missing
  required fields is rejected back to Anchor 3, not repaired by the council.
- **To Anchor 3:** `VALIDATED_POLICY_DECISION` (v1) as defined in §10, including dissent
  record and monitoring conditions — drives Anchor 3's P7/P8 lifecycle transitions.
- **Evidence/simulation loop:** requests are structured, logged, and always routed through
  Anchor 3's existing contracts — the council never queries Anchor 1 or 2 directly.

## 22. MVP Boundary
C1–C6 built with the 4-agent minimal topology; C7 (full deliberation record) built; C8
(decision emission) built for `approve`/`escalate`/`return_for_evidence` — no additional
agents, no cross-council learning/memory across proposals.

## 23. Future Extensions
- Expand agent topology as concrete policy classes demonstrate need (Servicing, Operations,
  Data Privacy, Credit, Insurance, Treasury, separate Fairness agent).
- Cross-proposal pattern learning (e.g., recognizing a policy class that recurs across many
  proposals) without compromising per-proposal auditability.
- Configurable decision rules per policy risk tier (e.g., stricter unanimity requirement
  for higher-risk policy classes).

---

## Modular Sprints

### C1 — Proposal Ingestion & Validation
- **Objective:** Reliably receive and validate `POLICY_PROPOSAL` events.
- **Scope:** Schema validation, rejection of incomplete proposals.
- **Inputs:** `POLICY_PROPOSAL` (synthetic fixtures initially).
- **Outputs:** Validated proposal ready for deliberation.
- **APIs/events:** `council.proposal.received`.
- **Data structures:** Validated `PolicyProposal` (as received).
- **Dependencies:** Anchor 3 contract (or fixture stand-in).
- **Acceptance criteria:** Incomplete proposals rejected back to Anchor 3, never repaired
  or guessed at by the council.
- **Unit tests:** Missing-field rejection.
- **Integration tests:** Fixture stream → validated store.
- **Security/privacy tests:** Confirm no individual-level fields are reachable even if
  accidentally present (defense-in-depth).
- **Demo scenario:** Ingest Anchor 3's fixture proposal set, including the deliberately
  weak proposal.
- **Definition of Done:** Full fixture set ingested; weak proposal correctly flagged for
  insufficient structure if applicable, otherwise passed to C2.

### C2 — Agent Position Generation
- **Objective:** Each of the 4 MVP agents produces a structured `Position`.
- **Scope:** Independent, perspective-bound evaluation per agent.
- **Inputs:** Validated proposal.
- **Outputs:** `Position[]` (one per agent).
- **APIs/events:** `council.position.recorded`.
- **Data structures:** `Position`.
- **Dependencies:** C1.
- **Acceptance criteria:** Every agent produces exactly one of the three allowed stances,
  with rationale grounded in the proposal's actual fields.
- **Unit tests:** Each agent against a proposal clearly favorable/unfavorable to its
  perspective.
- **Integration tests:** C1 → C2 on full fixture set.
- **Security/privacy tests:** N/A.
- **Demo scenario:** Run all four agents on the insurance+reserve fixture proposal.
- **Definition of Done:** All four agents produce valid, rationale-backed positions on
  every fixture proposal.

### C3 — Objection & Counterargument Engine
- **Objective:** Generate structured objections against specific proposal fields or other
  agents' positions.
- **Scope:** Structured-message generation only; no open-ended dialogue.
- **Inputs:** `Position[]`.
- **Outputs:** `Objection[]`.
- **APIs/events:** `council.objection.raised`.
- **Data structures:** `Objection`.
- **Dependencies:** C2.
- **Acceptance criteria:** Every objection targets a specific field or position — no
  free-floating objections without a target.
- **Unit tests:** Objection targeting correctness.
- **Integration tests:** C2 → C3 on a fixture with genuine disagreement (e.g., Risk Agent
  objects, Economics Agent supports).
- **Security/privacy tests:** N/A.
- **Demo scenario:** Risk Agent objects to eligibility criteria; Compliance Agent counters.
- **Definition of Done:** Objection/counterargument fixture transcript produced and
  reviewed for structure compliance.

### C4 — Evidence & Simulation Request Loop
- **Objective:** Route evidence/simulation requests back to Anchor 3 and resume
  deliberation on response.
- **Scope:** Request/response round-trip, timeout handling.
- **Inputs:** Agent-flagged insufficient-evidence positions.
- **Outputs:** `EvidenceRequest` / `SimulationRequest`, and re-evaluated `Position` on
  response.
- **APIs/events:** `council.evidence.requested`, `council.evidence.received`.
- **Data structures:** `EvidenceRequest`, `SimulationRequest`.
- **Dependencies:** C2, C3, Anchor 3's P1/P6 (or fixture stand-in).
- **Acceptance criteria:** A timed-out request results in `RETURN_TO_ANCHOR3`, never a
  stalled or fabricated position.
- **Unit tests:** Timeout path, successful round-trip path.
- **Integration tests:** Full loop against Anchor 3's fixture harness.
- **Security/privacy tests:** Confirm requests never target Anchor 1/2 directly.
- **Demo scenario:** Economics Agent requests a simulation; receives result; updates
  position from `insufficient_evidence` to `support`.
- **Definition of Done:** Both timeout and successful round-trip demonstrated on fixtures.

### C5 — Deliberation Coordinator (Bounded Rounds)
- **Objective:** Run bounded rounds of objection/counterargument until stabilization or
  round-limit.
- **Scope:** Round orchestration, stabilization detection, round-limit enforcement.
- **Inputs:** `Position[]`, `Objection[]`.
- **Outputs:** Stabilized position set or round-limit-reached flag.
- **APIs/events:** `council.round.completed`.
- **Data structures:** Round counter, stabilization check result.
- **Dependencies:** C3, C4.
- **Acceptance criteria:** Deliberation never runs unbounded; round limit is configurable
  but always enforced.
- **Unit tests:** Round-limit boundary tests.
- **Integration tests:** A fixture designed to never naturally stabilize hits the round
  limit and escalates rather than looping forever.
- **Security/privacy tests:** N/A.
- **Demo scenario:** Run the unresolved-conflict fixture transcript to its round limit.
- **Definition of Done:** Round-limit property test passes; unresolved-conflict fixture
  correctly reaches `ESCALATE`.

### C6 — Decision Rule Engine (Anti-Fabrication Guard)
- **Objective:** Deterministically compute the final decision from stabilized positions.
- **Scope:** Fixed decision rule; consensus-fabrication guard.
- **Inputs:** Stabilized `Position[]`, unresolved `Objection[]`.
- **Outputs:** `decision` (approve | escalate | return_for_evidence).
- **APIs/events:** `council.decision.computed`.
- **Data structures:** Decision record (pre-full-`VALIDATED_POLICY_DECISION` assembly).
- **Dependencies:** C5.
- **Acceptance criteria:** `approve` is only reachable when every required agent's
  position is `support` and no unresolved objection remains; any missing/dissenting/
  insufficient position blocks it.
- **Unit tests:** Adversarial tests attempting to force `approve` with a missing agent
  position or a lingering objection — must fail.
- **Integration tests:** All three fixture outcome transcripts (approve, escalate,
  return-for-evidence) produce the correct decision.
- **Security/privacy tests:** N/A.
- **Demo scenario:** Run all three fixture transcripts through the engine.
- **Definition of Done:** Anti-fabrication adversarial test suite passes 100%.

### C7 — Deliberation Record Persistence
- **Objective:** Persist the complete, immutable `DeliberationRecord`.
- **Scope:** Storage, replayability, dissent preservation.
- **Inputs:** All C2–C6 outputs.
- **Outputs:** `DeliberationRecord`.
- **APIs/events:** `council.record.persisted`.
- **Data structures:** `DeliberationRecord`.
- **Dependencies:** C6.
- **Acceptance criteria:** Dissent is preserved verbatim even in an `approve` outcome;
  record is fully replayable.
- **Unit tests:** Dissent-preservation assertion on an approve-with-dissent fixture (if the
  decision rule allows approval with a documented, resolved objection).
- **Integration tests:** Full replay of a persisted record reconstructs the exact
  deliberation sequence.
- **Security/privacy tests:** Access control on record retrieval.
- **Demo scenario:** Replay the health-related pilot proposal's full deliberation.
- **Definition of Done:** Replay test passes for all fixture transcripts.

### C8 — Decision Emission to Anchor 3
- **Objective:** Emit `VALIDATED_POLICY_DECISION` per shared contract.
- **Scope:** Final assembly (decision + rationale + dissent + monitoring conditions +
  expiry/review date), contract-schema emission.
- **Inputs:** `DeliberationRecord`.
- **Outputs:** `VALIDATED_POLICY_DECISION` event.
- **APIs/events:** `decision.emitted`.
- **Data structures:** `VALIDATED_POLICY_DECISION`.
- **Dependencies:** C7.
- **Acceptance criteria:** 100% schema conformance; every emitted decision includes a
  non-empty monitoring-metrics list and an expiry/review date.
- **Unit tests:** Schema validation.
- **Integration tests:** Full C1→C8 pipeline on fixture set, consumed successfully by
  Anchor 3's fixture harness (closing the loop from Master doc IM-3).
- **Security/privacy tests:** N/A.
- **Demo scenario:** Full end-to-end run: fixture proposal in, validated decision out,
  consumed by Anchor 3.
- **Definition of Done:** Emitted events validated against `iaspire-contracts` schema in CI
  and successfully advance a fixture policy's lifecycle state in Anchor 3.
