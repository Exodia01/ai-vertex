"""Validate emitted contracts + fixtures against the shared schemas.

Usage:
  python3 tools/validate_contracts.py            # self-test the schemas
  python3 tools/validate_contracts.py --all      # also validate live emitted events
"""
import json, os, sys
sys.path.insert(0,os.path.dirname(__file__))
from schema_validator import validate, load

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C=os.path.join(ROOT,"contracts","iaspire-contracts")
def sch(name): return load(os.path.join(C,name))

SJS_V1  = sch("stabilized_journal_state.v1.schema.json")
SJS_V11 = sch("stabilized_journal_state.v1.1.schema.json")
CSI     = sch("customer_segment_insight.v1.schema.json")
PP      = sch("policy_proposal.v1.schema.json")
VPD     = sch("validated_policy_decision.v1.schema.json")
ICE     = sch("identity_consent_envelope.v1.schema.json")
AUDIT   = sch("audit_event_envelope.v1.schema.json")

fails=[]
def check(name,cond,info=""):
    print(("PASS " if cond else "FAIL ")+name,info)
    if not cond: fails.append(name)

def valid(name,instance,schema,expect_valid=True):
    errs=validate(instance,schema)
    ok=(not errs) if expect_valid else bool(errs)
    check(name,ok,"" if ok else "; ".join(errs[:3]))
    return errs

GOOD_V1={"customer_ref":"cust_opaque_7f3a","objective_category":"travel",
  "mechanism_category":"savings_goal","feasibility_outcome":"feasible",
  "coarse_target_band":"0-1.5L","coarse_timeline_band":"0-3mo",
  "confirmed_at":"2026-09-26T10:00:00Z","state_version":"v1"}

print("--- STABILIZED_JOURNAL_STATE v1 ---")
valid("v1 accepts valid payload",GOOD_V1,SJS_V1)
v11=dict(GOOD_V1,state_version="v1.1",coarse_sentiment_band="low_stress",confidence_band="high_confidence")
valid("v1 rejects v1.1 sentiment fields",v11,SJS_V1,expect_valid=False)
valid("v1.1 accepts additive sentiment bands",v11,SJS_V11)
valid("v1.1 accepts plain v1 payload (additive)",GOOD_V1,SJS_V11)
valid("v1 rejects raw sentiment score",dict(GOOD_V1,coarse_sentiment_band=0.83),SJS_V1,expect_valid=False)
valid("v1 rejects extra field",dict(GOOD_V1,raw_text="I want to go to Japan"),SJS_V1,expect_valid=False)
valid("v1 rejects bad feasibility outcome",dict(GOOD_V1,feasibility_outcome="maybe"),SJS_V1,expect_valid=False)
valid("v1 rejects non-opaque customer_ref",dict(GOOD_V1,customer_ref="Ramesh@Bhopal"),SJS_V1,expect_valid=False)
valid("v1 rejects out-of-enum mechanism",dict(GOOD_V1,mechanism_category="crypto"),SJS_V1,expect_valid=False)

print("--- CUSTOMER_SEGMENT_INSIGHT v1 ---")
valid("csi valid",{"insight_id":"csi_seg_0001","segment":"hostel_owners_tier2","need":"travel",
  "pct":42.5,"cohort_size":38,"confidence":"moderate"},CSI)
valid("csi cohort_size>=1 enforced",{"insight_id":"csi_seg_0002","segment":"x","need":"travel",
  "pct":10,"cohort_size":0,"confidence":"low"},CSI,expect_valid=False)
valid("csi suppression marker requires reason",{"insight_id":"csi_seg_0003","segment":"x",
  "need":"travel","pct":1,"cohort_size":2,"confidence":"low","suppressed":True},CSI,expect_valid=False)
valid("csi suppression w/ reason ok",{"insight_id":"csi_seg_0004","segment":"x","need":"travel",
  "pct":1,"cohort_size":2,"confidence":"low","suppressed":True,"suppression_reason":"k<5"},CSI)

print("--- POLICY_PROPOSAL v1 ---")
valid("proposal valid",{"policy_id":"pol_0001","version":"v1","lifecycle_state":"DRAFT",
  "target_segment":"hostel_owners_tier2","customer_need":"travel",
  "evidence":["csi_seg_0001"],"financial_mechanism":"lounge_debit_upgrade",
  "created_at":"2026-09-26T10:00:00Z","updated_at":"2026-09-26T10:00:00Z"},PP)
valid("proposal rejects non-csi evidence",{"policy_id":"pol_0002","version":"v1","lifecycle_state":"DRAFT",
  "target_segment":"s","customer_need":"travel","evidence":["cust_opaque_7f3a"],
  "financial_mechanism":"m","created_at":"2026-09-26T10:00:00Z","updated_at":"2026-09-26T10:00:00Z"},
  PP,expect_valid=False)
valid("proposal rejects bad lifecycle",{"policy_id":"pol_0003","version":"v1","lifecycle_state":"LIVE",
  "target_segment":"s","customer_need":"travel","evidence":["csi_seg_0001"],"financial_mechanism":"m",
  "created_at":"2026-09-26T10:00:00Z","updated_at":"2026-09-26T10:00:00Z"},PP,expect_valid=False)

print("--- VALIDATED_POLICY_DECISION v1 ---")
valid("decision valid",{"policy_id":"pol_0001","decision":"approve","rationale":"economics ok",
  "agent_positions_summary":[{"agent":"economics","stance":"support"}],"dissent_record":[],
  "confidence":"moderate","contract_version":"v1"},VPD)
valid("escalate requires conditions",{"policy_id":"pol_0001","decision":"escalate","rationale":"conflict",
  "agent_positions_summary":[{"agent":"risk","stance":"object"}],
  "dissent_record":[{"agent":"risk","position":"too broad"}],"confidence":"low",
  "contract_version":"v1"},VPD,expect_valid=False)
valid("agent cannot invent a stance",{"policy_id":"pol_0001","decision":"approve","rationale":"r",
  "agent_positions_summary":[{"agent":"risk","stance":"abstain"}],"dissent_record":[],
  "confidence":"low","contract_version":"v1"},VPD,expect_valid=False)

print("--- IDENTITY_CONSENT_ENVELOPE v1 ---")
valid("consent valid",{"customer_ref":"cust_opaque_7f3a","consent_scope":["txn.read","bal.read"],
  "purpose":"journal_analysis","granted_at":"2026-09-26T10:00:00Z"},ICE)
valid("consent rejects unknown scope",{"customer_ref":"cust_opaque_7f3a","consent_scope":["everything"],
  "purpose":"journal_analysis","granted_at":"2026-09-26T10:00:00Z"},ICE,expect_valid=False)

print("--- AUDIT_EVENT_ENVELOPE v1 ---")
valid("audit valid",{"actor":"deterministic_engine","action":"feasibility.computed",
  "evidence_ref":"asp_001","timestamp":"2026-09-26T10:00:00Z","trace_id":"trc_00000001"},AUDIT)
valid("audit rejects unknown actor",{"actor":"wizard","action":"a.b",
  "evidence_ref":"x","timestamp":"2026-09-26T10:00:00Z","trace_id":"trc_00000001"},AUDIT,expect_valid=False)
valid("audit rejects missing trace_id",{"actor":"ai","action":"a.b",
  "evidence_ref":"x","timestamp":"2026-09-26T10:00:00Z"},AUDIT,expect_valid=False)

print("\nSCHEMA RESULT:","ALL PASS" if not fails else f"{len(fails)} FAILS {fails}")
sys.exit(1 if fails else 0)
