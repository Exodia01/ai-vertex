# iAspire — Master Architecture & Dependency Map

This document is the index and integration contract for the four independent anchor
documents. It does not duplicate their internal detail — it only defines how they fit
together, what can be built in parallel, and what "done" means at each level.

Companion documents:
- `01_FINANCIAL_JOURNAL.md`
- `02_DATA_HARVESTOR.md`
- `03_POLICY_BUILDER.md`
- `04_AGENT_COUNCIL.md`

---

## 1. Four-Anchor Architecture Diagram

```mermaid
flowchart TD
    C[Customer] -->|NL aspirations, permissioned data| A1[Anchor 1: Financial Journal]
    A1 -->|STABILIZED_JOURNAL_STATE event| A2[Anchor 2: Data Harvestor]
    A2 -->|CUSTOMER_SEGMENT_INSIGHT event\n(anonymized/aggregated)| A3[Anchor 3: Policy Builder]
    A3 -->|POLICY_PROPOSAL event| A4[Anchor 4: Council of Agents]
    A4 -->|VALIDATED_POLICY_DECISION event| A3
    A3 -->|ACTIVE policy catalog| BankOps[Institution / Servicing Systems]
    A4 -.->|no individual customer data ever flows back| A1
    A3 -.->|no individual customer data ever flows back| A1
```

Hard boundary rule: nothing computed in Anchor 2, 3, or 4 may be traced back to an
individual customer. Anchor 1 is the only anchor holding individually identifiable
financial data. All arrows crossing that boundary are one-directional and privacy-filtered.

---

## 2. Cross-Anchor Dependency Graph

| Anchor | Depends on (contract) | Produces (contract) | Can be mocked with |
|---|---|---|---|
| 1. Financial Journal | Core banking/account data feeds (external) | `STABILIZED_JOURNAL_STATE` | Synthetic customer/transaction fixtures |
| 2. Data Harvestor | `STABILIZED_JOURNAL_STATE` (Anchor 1) | `CUSTOMER_SEGMENT_INSIGHT` | Synthetic `STABILIZED_JOURNAL_STATE` fixtures |
| 3. Policy Builder | `CUSTOMER_SEGMENT_INSIGHT` (Anchor 2), `VALIDATED_POLICY_DECISION` (Anchor 4) | `POLICY_PROPOSAL` | Synthetic `CUSTOMER_SEGMENT_INSIGHT` fixtures |
| 4. Council of Agents | `POLICY_PROPOSAL` (Anchor 3) | `VALIDATED_POLICY_DECISION` | Synthetic `POLICY_PROPOSAL` fixtures |

Because every anchor consumes a well-defined event contract rather than another anchor's
internals, all four streams start on day 1 against synthetic fixtures (see §4) and only
need to re-point at the real upstream anchor at integration checkpoints.

---

## 3. Shared Contracts (owned jointly, versioned centrally)

All contracts live in a shared schema repo (`iaspire-contracts`), semver'd independently
of any anchor's internal release cadence.

1. **`STABILIZED_JOURNAL_STATE` (v1, extended to v1.1)** — Anchor 1 → Anchor 2.
   Customer-approved aspiration + feasibility outcome + coarse behavioral tags. No raw
   transaction lines, no PII beyond an opaque `customer_ref`. v1.1 adds an optional,
   additive `coarse_sentiment_band` field (bucketed category only — never raw sentiment
   text or scores); v1 consumers are unaffected and may ignore the field.
2. **`CUSTOMER_SEGMENT_INSIGHT` (v1)** — Anchor 2 → Anchor 3. Aggregated, cohort-thresholded
   statements only (e.g., `segment`, `need`, `pct`, `cohort_size`, `confidence`).
3. **`POLICY_PROPOSAL` (v1)** — Anchor 3 → Anchor 4. Structured proposal object (see Anchor 3
   data model) — never free-text-only.
4. **`VALIDATED_POLICY_DECISION` (v1)** — Anchor 4 → Anchor 3. Decision + rationale +
   dissent record + monitoring conditions.
5. **Identity/consent envelope** — used by Anchors 1–2 only; carries consent scope and
   purpose-limitation tags on every record crossing a boundary.
6. **Audit event envelope** — common structure (`actor`, `action`, `evidence_ref`,
   `timestamp`, `trace_id`) used by all four anchors for auditability.

Versioning strategy: additive fields only within a major version; breaking changes bump
the major version and both producer and consumer must support N and N-1 during a deprecation
window (minimum one full sprint cycle).

---

## 4. Mock/Stub Strategy & Test Fixtures

Each anchor ships a `fixtures/` package with:
- **Customers** (10–50 synthetic personas spanning income bands, life stages, risk profiles)
- **Transactions** (12–24 months synthetic history per persona, including edge cases:
  irregular income, large one-off expenses, debt spirals, sudden windfalls)
- **Aspirations** (travel, house, vehicle, emergency fund, education, medical, debt payoff,
  vague/ambiguous statements, contradictory statements)
- **Journal states** (one per lifecycle stage: raw → interpreted → challenged → stabilized →
  abandoned)
- **Sentiment fixtures** (paired same-objective aspirations expressed at different
  stress/urgency/confidence levels, plus one explicit-accept-vs-repeated-anxiety
  contradiction case, to validate J11's tone/priority/contradiction-note effects without
  changing stabilization outcomes)
- **Stabilized goals** (feeding Anchor 2 fixtures directly)
- **Aggregated segments** (feeding Anchor 3 fixtures directly, including a below-threshold
  cohort that must be suppressed)
- **Policy proposals** (feeding Anchor 4 fixtures directly, including a deliberately weak
  proposal with insufficient evidence, to test the council's refusal path)
- **Agent deliberations** (a full transcript fixture per outcome type: consensus, unresolved
  conflict, insufficient-evidence rejection)

Real customer data is never used pre-production; a synthetic-data linter runs in CI to
block any fixture that resembles real account numbers, names, or PII patterns.

---

## 5. Parallel Sprint Schedule (illustrative, 6 two-week sprints to MVP)

| Sprint | Anchor 1 | Anchor 2 | Anchor 3 | Anchor 4 |
|---|---|---|---|---|
| 1 | J1, J2 | H1 (fixtures + contract) | P1 (fixtures + contract) | C1 (fixtures + contract) |
| 2 | J3, J4 | H2 | P2 | C2 |
| 3 | J5, J6 | H3 | P3 | C3 |
| 4 | J7, J8 | H4, H5 | P4 | C4, C5 |
| 5 | J9 | H6 | P5, P6 | C6 |
| 6 | J10 + integration | H7, H8 + integration | P7, P8 + integration | C7, C8 + integration |

*J11 (Sentiment Analysis) runs alongside J4 starting Sprint 2 — it has no ordering
dependency on J5–J10 and can be built by a separate sub-track within the Anchor 1 team
without affecting this schedule.*

Integration checkpoints occur at the end of sprints 2, 4, and 6 (see §6).

---

## 6. Integration Milestones

- **IM-1 (end of Sprint 2):** Anchor 1 emits a real `STABILIZED_JOURNAL_STATE` from its
  own pipeline (still synthetic customers). Anchor 2 swaps its fixture source for Anchor 1's
  live output in a staging environment.
- **IM-2 (end of Sprint 4):** Anchor 2 emits real `CUSTOMER_SEGMENT_INSIGHT` from
  aggregated Anchor-1 data. Anchor 3 swaps to it. Anchor 3 emits real `POLICY_PROPOSAL`;
  Anchor 4 swaps to it.
- **IM-3 (end of Sprint 6, MVP cut):** Full closed loop — Anchor 4 decisions flow back
  into Anchor 3's policy lifecycle; all four anchors run against each other's live outputs
  in staging with synthetic customers end-to-end.

---

## 7. Critical-Path Analysis

The longest dependency chain is: **J3/J4/J5/J6 (Journal state + intent + feasibility) →
J8 (stabilization) → H2/H3 (ingestion + privacy transform) → H5 (aggregation) → P3
(evidence-to-proposal mapping) → C4 (deliberation engine) → C6 (decision recording)**.
Anything on this chain that slips delays every downstream anchor's ability to test against
real (not synthetic) data — though not their ability to keep building, since fixtures
absorb the delay. The two highest-risk nodes are **J6 (feasibility engine)**, because it is
the first place deterministic finance and LLM reasoning must be cleanly separated, and
**H3 (privacy transform)**, because privacy guarantees are architectural and hard to retrofit.

---

## 8. MVP Cut Line

In scope for MVP:
- Anchor 1: ingestion, normalization, intent extraction, feasibility engine, one round of
  challenge/nudge, stabilization, basic monitoring (J1–J8, partial J10).
- Anchor 2: ingestion contract, anonymization/aggregation, k-anonymity suppression,
  single-segment insight output (H1–H5).
- Anchor 3: proposal generation from insights, structured policy schema, DRAFT→SIMULATION
  lifecycle only (P1–P4).
- Anchor 4: a minimal 4-agent council (Customer Advocate, Risk, Economics, Compliance),
  structured deliberation, decision recording (C1–C4).

Deferred past MVP: differential privacy, full agent topology (Product/Operations/
Servicing/Credit/Insurance/Treasury/Fairness agents), full policy lifecycle through
ACTIVE/MONITORED/RETIRED, continuous re-analysis on material life events, multi-tenant
isolation at scale.

---

## 9. Risks / Blockers

- **OPEN DECISION:** Whether differential privacy is required for MVP or can be deferred
  to k-anonymity + suppression alone. Alternatives: (a) k-anonymity only — faster to ship,
  weaker guarantee against auxiliary-data attacks; (b) DP from day one — stronger guarantee,
  materially slower to build and harder to explain to compliance reviewers. Consequence of
  deferring: MVP aggregate outputs are not formally DP-safe and must be scoped to low-risk
  cohorts only until DP lands.
- **OPEN DECISION:** Final agent topology for Anchor 4 (which of the 12 candidate agents
  are load-bearing vs. redundant). Consequence of under-deciding: council decisions may look
  authoritative while missing a required perspective (e.g., no Servicing Agent means
  operationally unbuildable policies get approved).
- **Risk:** LLM-based intent classification (J4) drifting into acting as the financial
  calculator rather than the reasoner. Mitigation: J6's deterministic engine is the sole
  source of numeric feasibility truth; J4/J5 output is always advisory input to it, never
  a replacement.
- **Blocker candidate:** Access to real historical customer financial behavior for anything
  beyond synthetic testing requires a data-use approval that is outside this plan's scope
  and should be tracked as an external dependency.

---

## 10. Definitions

**"Ready for integration"** (per anchor): the anchor's event contract is implemented and
schema-validated, its fixtures pass the synthetic-data linter, its own sprint acceptance
criteria are met, and it can consume/produce the shared contract version currently pinned
in `iaspire-contracts` without manual patching.

**"Production ready"** (whole system): all four anchors have passed IM-3, the privacy
architecture in Anchor 2 has been independently reviewed, every policy in Anchor 3 has a
defined lifecycle state and retirement condition, every Anchor 4 decision has a recorded
evidence trail and monitoring metric, human override paths exist at each anchor boundary,
and the audit event envelope is emitting consistently across all four anchors into a single
queryable audit store.
