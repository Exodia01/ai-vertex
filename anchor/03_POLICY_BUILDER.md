# Anchor 3 — Policy Builder

## 1. Purpose
Determine what policies, products, or services a financial institution should create or
modify to serve recurring customer needs surfaced by Anchor 2, producing structured,
versioned, bounded policy proposals rather than an unbounded pile of ideas.

## 2. Scope
- Consuming `CUSTOMER_SEGMENT_INSIGHT` from Anchor 2.
- Generating structured `POLICY_PROPOSAL` objects with all required fields.
- Managing policy lifecycle state (DRAFT → REVIEW → SIMULATION → APPROVED → ACTIVE →
  MONITORED → MODIFIED/RETIRED).
- Consuming `VALIDATED_POLICY_DECISION` from Anchor 4 to advance lifecycle state.
- Feeding proposals to Anchor 4 when proposal volume exceeds manual review capacity.

## 3. Non-Goals
- Does not access individual customer data at any point.
- Does not itself deliberate/debate — that's Anchor 4's role once volume warrants it.
- Not a servicing/operations execution system; it produces policy definitions, not
  running products.

## 4. Core Concepts
- **Policy Candidate**: an unreviewed idea derived from one or more segment insights.
- **Policy Proposal**: a fully structured object with all required fields (§13), ready for
  review or council deliberation.
- **Policy Lifecycle**: the versioned state progression a proposal moves through.
- **Evidence**: the specific `CUSTOMER_SEGMENT_INSIGHT` records backing a proposal —
  never traceable further back to individuals.
- **Conflict/Trade-off**: an explicit record of where a proposal competes with or
  contradicts another proposal or existing policy.

## 5. Actors
- **Insight Consumer** — ingests Anchor 2 output.
- **Proposal Generator (AI)** — drafts candidate policies from evidence.
- **Structuring Engine** — enforces the required-fields schema before a candidate becomes
  a proposal.
- **Lifecycle Manager** — deterministic state-machine enforcement.
- **Human Reviewer** — override authority at REVIEW and APPROVED gates.
- **Council Router** — sends proposals to Anchor 4 once volume/complexity thresholds are
  met.

## 6. Inputs
- `CUSTOMER_SEGMENT_INSIGHT` (Anchor 2).
- `VALIDATED_POLICY_DECISION` (Anchor 4).
- Existing active policy catalog (for conflict detection).

## 7. Outputs
- `POLICY_PROPOSAL` events (to Anchor 4, and to human reviewers for lower-volume paths).
- Active policy catalog (to institution/servicing systems — outside this plan's scope).

## 8. State Model
```
DRAFT → REVIEW → SIMULATION → APPROVED → ACTIVE → MONITORED → MODIFIED
                                                            ↘ RETIRED
```
- `DRAFT`: generated from evidence, not yet structurally complete.
- `REVIEW`: complete structure, awaiting human or council judgment.
- `SIMULATION`: modeled against historical/aggregate data for expected impact.
- `APPROVED`: accepted, not yet live.
- `ACTIVE`: live and being monitored.
- `MONITORED`: active with defined monitoring metrics being tracked.
- `MODIFIED`: an active policy revised (creates a new version, prior version retired).
- `RETIRED`: no longer offered; retirement condition recorded.

## 9. Detailed Functional Flow
1. Ingest one or more `CUSTOMER_SEGMENT_INSIGHT` records (P1).
2. Generate policy candidates from evidence (P2).
3. Structure each candidate into the full required-fields schema (P3); reject/return to
   draft anything incomplete.
4. Detect conflicts/trade-offs against the existing catalog and other in-flight proposals
   (P4).
5. Route to human review or Anchor 4 council based on volume/complexity thresholds (P5).
6. Run simulation against aggregate/historical data (P6).
7. On approval (human or council), advance lifecycle to APPROVED → ACTIVE (P7).
8. Monitor active policies against their defined metrics; handle MODIFIED/RETIRED
   transitions (P8).

## 10. Data Model
```
PolicyProposal {
  policy_id, version, lifecycle_state,
  target_segment, customer_need, evidence[] (CUSTOMER_SEGMENT_INSIGHT refs),
  assumptions[], eligibility, financial_mechanism,
  expected_customer_benefit, institution_benefit,
  risk[], compliance_considerations[], operational_requirements[],
  servicing_requirements[], dependencies[], estimated_scale,
  conflicts_tradeoffs[], retirement_conditions, created_at, updated_at
}
```
- `SimulationResult { policy_id, model_inputs, projected_outcomes, confidence }`
- `ConflictRecord { policy_id, conflicting_policy_id, nature, resolution_status }`
- `LifecycleTransition { policy_id, from_state, to_state, actor, evidence_ref, timestamp }`

## 11. AI Responsibilities
- Drafting policy candidates from segment evidence.
- Drafting the narrative fields (expected benefit, risk description) for human readability.
- Flagging likely conflicts/trade-offs for human/council attention.
AI drafts are always `DRAFT` state; no AI output advances lifecycle state on its own.

## 12. Deterministic Computation Responsibilities
- Structural completeness validation (all required fields present) before DRAFT→REVIEW.
- Simulation modeling math (projected scale, cost/benefit estimates) — deterministic
  models fed by aggregate data, not LLM-estimated numbers.
- Lifecycle state-machine transitions themselves.

## 13. Privacy/Security Requirements
- Operates exclusively on Anchor 2's aggregate output; no path exists to ingest
  individual-level data.
- Evidence references point to `CUSTOMER_SEGMENT_INSIGHT` records, never to Anchor 1 data.
- Access controls on who can advance a policy through REVIEW/APPROVED gates.
- Full audit trail per lifecycle transition.

## 14. API/Event Contracts
- Consumes: `CUSTOMER_SEGMENT_INSIGHT` (Anchor 2), `VALIDATED_POLICY_DECISION` (Anchor 4).
- Produces: `POLICY_PROPOSAL` (to Anchor 4 and/or human review queue).
- `GET /policies/{id}` — full structured record with version history.

## 15. Failure Modes
- Incomplete evidence (insight below a usefulness threshold) → candidate stays in DRAFT,
  flagged for more evidence rather than force-completed with assumptions.
- Conflict detection failure → proposal held at REVIEW rather than auto-approved.
- Simulation model unavailable → proposal cannot advance past SIMULATION; fails closed.

## 16. Observability
- Proposal volume by lifecycle state (detects pileups, e.g., stuck at REVIEW).
- Council-routed vs. human-routed proposal ratio.
- Time-in-state per lifecycle stage.

## 17. Auditability
- Every lifecycle transition recorded with actor and evidence reference.
- Every retirement recorded with its triggering condition.

## 18. Testing Strategy
- Schema-completeness tests (a proposal missing any required field cannot reach REVIEW).
- Conflict-detection tests against a fixture catalog with deliberate overlaps.
- Simulation reproducibility tests (same inputs → same projected outcomes).
- Lifecycle state-machine tests covering every legal and illegal transition.

## 19. Scalability Considerations
- Designed for thousands of concurrent proposals; volume-based routing to Anchor 4 exists
  specifically because manual review does not scale to this.
- Proposal generation and structuring are independently horizontally scalable per segment.

## 20. Dependency Map
- Upstream: Anchor 2 (`CUSTOMER_SEGMENT_INSIGHT`), Anchor 4 (`VALIDATED_POLICY_DECISION`).
- Downstream: Anchor 4 (`POLICY_PROPOSAL`), institution servicing systems (out of scope).

## 21. Interface Contracts with Other Anchors
- **From Anchor 2:** consumes `CUSTOMER_SEGMENT_INSIGHT` as-is; never requests more granular
  data than the contract provides.
- **To Anchor 4:** `POLICY_PROPOSAL` (v1) as defined in §10 — full structure required,
  no free-text-only proposals accepted by the council.
- **From Anchor 4:** `VALIDATED_POLICY_DECISION` — decision, rationale, dissent record,
  monitoring conditions; drives P7/P8 lifecycle transitions.

## 22. MVP Boundary
P1–P4 fully built; P5 routes everything to a single reviewer path plus a basic council
hand-off; P6 (simulation) built for simple scale/cost projections only; P7–P8 built through
ACTIVE, with MODIFIED/RETIRED stubbed for post-MVP.

## 23. Future Extensions
- Richer simulation models (multi-scenario, sensitivity analysis).
- Automated conflict-resolution suggestions.
- Portfolio-level view across all active policies for the institution.

---

## Modular Sprints

### P1 — Insight Ingestion
- **Objective:** Consume `CUSTOMER_SEGMENT_INSIGHT` reliably.
- **Scope:** Event consumption, schema validation.
- **Inputs:** `CUSTOMER_SEGMENT_INSIGHT` (synthetic fixtures initially).
- **Outputs:** Validated insight store.
- **APIs/events:** `builder.insight.received`.
- **Data structures:** Stored insight records.
- **Dependencies:** Anchor 2 contract (or fixture stand-in).
- **Acceptance criteria:** 100% schema-invalid events quarantined.
- **Unit tests:** Schema validation edge cases.
- **Integration tests:** Fixture stream → validated store.
- **Security/privacy tests:** Confirm no identifier fields present (should already be
  guaranteed by Anchor 2, but defense-in-depth check here too).
- **Demo scenario:** Ingest Anchor 2's fixture insight set.
- **Definition of Done:** Full fixture set ingested with zero unhandled errors.

### P2 — Candidate Generation
- **Objective:** Draft policy candidates from one or more insights.
- **Scope:** AI-drafted candidates, always tagged DRAFT.
- **Inputs:** Validated insights.
- **Outputs:** `PolicyProposal` (DRAFT, incomplete fields allowed).
- **APIs/events:** `builder.candidate.drafted`.
- **Data structures:** Partial `PolicyProposal`.
- **Dependencies:** P1.
- **Acceptance criteria:** Every candidate cites at least one evidence reference.
- **Unit tests:** Candidate generation from single vs. multiple insights.
- **Integration tests:** P1 → P2.
- **Security/privacy tests:** N/A (aggregate data only).
- **Demo scenario:** Healthcare-reserve insight → insurance+reserve candidate.
- **Definition of Done:** Candidates generated for full fixture insight set, each with
  evidence linkage.

### P3 — Structuring Engine
- **Objective:** Enforce the full required-fields schema before DRAFT→REVIEW.
- **Scope:** Schema completeness validation only.
- **Inputs:** DRAFT `PolicyProposal`.
- **Outputs:** REVIEW-eligible `PolicyProposal` or rejection with missing-field list.
- **APIs/events:** `builder.proposal.structured`.
- **Data structures:** Complete `PolicyProposal`.
- **Dependencies:** P2.
- **Acceptance criteria:** No proposal reaches REVIEW missing any required field from §13
  (product-thesis list).
- **Unit tests:** Missing-field rejection cases.
- **Integration tests:** P2 → P3 → REVIEW transition.
- **Security/privacy tests:** N/A.
- **Demo scenario:** A candidate missing `risk` is rejected back to DRAFT with a specific
  reason.
- **Definition of Done:** Schema-completeness property test passes for all fixture
  candidates.

### P4 — Conflict/Trade-off Detection
- **Objective:** Detect overlaps/contradictions against the existing catalog and other
  in-flight proposals.
- **Scope:** Comparison logic, `ConflictRecord` generation.
- **Inputs:** Structured proposals, existing catalog.
- **Outputs:** `ConflictRecord[]`.
- **APIs/events:** `builder.conflict.detected`.
- **Data structures:** `ConflictRecord`.
- **Dependencies:** P3.
- **Acceptance criteria:** Deliberately overlapping fixture proposals are correctly
  flagged.
- **Unit tests:** Overlap and contradiction fixture cases.
- **Integration tests:** P3 → P4 on fixture catalog.
- **Security/privacy tests:** N/A.
- **Demo scenario:** Two proposals targeting the same segment with contradictory
  eligibility rules get flagged.
- **Definition of Done:** All fixture conflict cases correctly detected with zero false
  negatives on the test set.

### P5 — Routing (Human vs. Council)
- **Objective:** Route each REVIEW-stage proposal to a human reviewer or Anchor 4 based on
  volume/complexity thresholds.
- **Scope:** Routing logic only.
- **Inputs:** REVIEW-stage proposals.
- **Outputs:** Routed proposal (to reviewer queue or `POLICY_PROPOSAL` event to Anchor 4).
- **APIs/events:** `builder.proposal.routed`, `POLICY_PROPOSAL` (to Anchor 4).
- **Data structures:** Routing decision record.
- **Dependencies:** P3, P4.
- **Acceptance criteria:** Routing rule is deterministic and explainable (not opaque).
- **Unit tests:** Threshold boundary tests.
- **Integration tests:** P4 → P5 → Anchor 4 fixture harness receives a well-formed
  `POLICY_PROPOSAL`.
- **Security/privacy tests:** N/A.
- **Demo scenario:** A high-conflict proposal is routed to the council; a simple,
  conflict-free proposal is routed to human review.
- **Definition of Done:** Emitted `POLICY_PROPOSAL` events pass shared-contract schema
  validation in CI.

### P6 — Simulation Engine
- **Objective:** Model expected scale/impact of a proposal against aggregate data.
- **Scope:** Simple scale/cost projections for MVP.
- **Inputs:** Structured proposal, aggregate historical data.
- **Outputs:** `SimulationResult`.
- **APIs/events:** `builder.simulation.completed`.
- **Data structures:** `SimulationResult`.
- **Dependencies:** P3.
- **Acceptance criteria:** Reproducible outputs given identical inputs.
- **Unit tests:** Exact-value reproducibility assertions.
- **Integration tests:** P3 → P6 → SIMULATION state transition.
- **Security/privacy tests:** Confirm model inputs are aggregate-only.
- **Demo scenario:** Project estimated adoption scale for the insurance+reserve policy.
- **Definition of Done:** Reproducibility test suite passes 100%.

### P7 — Approval & Activation Lifecycle
- **Objective:** Advance proposals from APPROVED to ACTIVE and record the decision source.
- **Scope:** Lifecycle transition logic, decision-source recording (human or
  `VALIDATED_POLICY_DECISION`).
- **Inputs:** Approved proposals or `VALIDATED_POLICY_DECISION` events.
- **Outputs:** `ACTIVE` policies, `LifecycleTransition` records.
- **APIs/events:** `builder.policy.activated`.
- **Data structures:** `LifecycleTransition`.
- **Dependencies:** P5, P6, Anchor 4 contract (or fixture stand-in).
- **Acceptance criteria:** Every activation traces to a specific decision record (human
  or council).
- **Unit tests:** Both decision-source paths.
- **Integration tests:** Full P1→P7 pipeline on fixture set.
- **Security/privacy tests:** N/A.
- **Demo scenario:** A council-approved fixture proposal is activated with full traceability.
- **Definition of Done:** Every ACTIVE fixture policy has a traceable decision record in
  the audit store.

### P8 — Monitoring, Modification & Retirement
- **Objective:** Track active-policy metrics and handle MODIFIED/RETIRED transitions.
- **Scope:** Monitoring-metric tracking, retirement-condition evaluation.
- **Inputs:** Active policies, ongoing monitoring metrics.
- **Outputs:** `MODIFIED`/`RETIRED` transitions with recorded conditions.
- **APIs/events:** `builder.policy.modified`, `builder.policy.retired`.
- **Data structures:** Updated `LifecycleTransition`.
- **Dependencies:** P7.
- **Acceptance criteria:** Every retirement records its triggering condition; every
  modification creates a new version rather than mutating history.
- **Unit tests:** Retirement-condition evaluation, version-increment correctness.
- **Integration tests:** Full lifecycle including a fixture policy that gets retired.
- **Security/privacy tests:** N/A.
- **Demo scenario:** A fixture policy underperforms its monitoring metric and is retired
  with the reason recorded.
- **Definition of Done:** Full lifecycle (DRAFT→...→RETIRED) demonstrated end-to-end on a
  fixture policy with an intact audit trail.
