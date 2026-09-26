"""P0 gate: contracts, fixtures, linter, version threading, boundary, audit envelope.

Run: python3 tools/gate_p0.py
Exits non-zero on any failure so CI can block on it.
"""
import json, os, subprocess, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,ROOT); sys.path.insert(0,os.path.join(ROOT,"tools"))
os.chdir(ROOT)
fails=[]
def check(n,c,i=""):
    print(("PASS " if c else "FAIL ")+n,i)
    if not c: fails.append(n)
def run(label,args):
    r=subprocess.run([sys.executable]+args,capture_output=True,text=True)
    check(label,r.returncode==0,(r.stdout.strip().splitlines() or [""])[-1][:110])
    return r

print("=== 1. contract schemas self-test ===")
run("schema self-test (25 cases)",["tools/validate_contracts.py"])

print("=== 2. synthetic-data linter ===")
run("linter clean on fixtures+data",["tools/synthetic_linter.py","fixtures","mock_aa.json","soul.json","contracts.py"])

print("=== 3. fixture package completeness (Master §4) ===")
for f in ["fixtures/customers/index.json","fixtures/aspirations.json","fixtures/sentiment.json",
          "fixtures/journal_states.json","fixtures/stabilized_goals.json"]:
    check(f"exists {f}",os.path.exists(f))
idx=json.load(open("fixtures/customers/index.json"))
check("multiple personas (>=3)",len(idx)>=3,str(len(idx)))
check("multi-month history (>=300 txns each)",all(i["transactions"]>=300 for i in idx))
edge=" ".join(i["edge_case"] for i in idx).lower()
for named in ["irregular","zero savings","negative cash flow","windfall","debt spiral"]:
    check(f"edge case covered: {named}",named in edge)
asp=json.load(open("fixtures/aspirations.json"))["cases"]
check("ambiguous aspirations present",sum(1 for c in asp if c["bucket"]=="ambiguous")>=3)
check("contradictory aspirations present",sum(1 for c in asp if c["bucket"]=="contradictory")>=3)
check("stated-mechanism cases present",len(json.load(open("fixtures/aspirations.json"))["stated_mechanism_cases"])>=3)
sent=json.load(open("fixtures/sentiment.json"))
check("sentiment calm/urgent/anxious/unsure",all(all(k in p for k in ("calm","urgent","anxious","unsure")) for p in sent["pairs"]))
check("accept-vs-anxiety contradiction case",len(sent["contradiction_cases"])>=2)
js=json.load(open("fixtures/journal_states.json"))
check("one fixture per lifecycle stage",len(js["states"])==8,str(len(js["states"])))
check("rejected-interpretation loop-back present","rejected_interpretation_case" in js)

print("=== 4. fixtures validate against contracts (IM-1 readiness) ===")
from contracts import validate_event, assert_boundary_clean, SCHEMAS
from schema_validator import validate
sg=json.load(open("fixtures/stabilized_goals.json"))["goals"]
for g in sg:
    errs=validate_event(g,"SJS_v1.1")
    check(f"goal {g['customer_ref']} valid v1.1",not errs,"; ".join(errs[:2]))
bad=[]
for g in sg:
    try: assert_boundary_clean(g)
    except ValueError as e: bad.append(str(e))
check("no boundary violation in Anchor 2 inputs",not bad,str(bad[:1]))
check("at least one goal carries sentiment band",any("coarse_sentiment_band" in g for g in sg))
check("at least one goal at non-v1 revision",any(g["state_version"]!="v1" for g in sg))
csi={"insight_id":"csi_demo_01","segment":"hostel_owners_tier2","need":"travel","pct":42.0,
     "cohort_size":38,"confidence":"moderate"}
check("CUSTOMER_SEGMENT_INSIGHT sample valid",not validate(csi,SCHEMAS["CSI"]))

print("=== 5. version threading (the P0 bug) ===")
if os.path.exists("/tmp/gate_mem.jsonl"): os.remove("/tmp/gate_mem.jsonl")
from pipeline import Pipeline
p=Pipeline(memory_path="/tmp/gate_mem.jsonl")
a=p.submit("Dubai 1.2L in 3 months"); r1=p.respond(a["aspiration_id"],"accept")
gid=r1["goal"]["goal_id"]
r2=p.revise(gid,target=150000); r3=p.revise(gid,timeline_mo=12)
ev=[x["event"]["state_version"] for x in (r1,r2,r3)]
mem=[g["state_version"] for g in p.memory.revisions(gid)]
check("event state_version == memory state_version",ev==mem,f"{ev} vs {mem}")
check("J9 three-revision DoD",mem==["v1","v2","v3"],str(mem))
check("state_version is NOT the contract version",r1["goal"]["contract_version"]=="v1.1" and ev[0]=="v1")
b=p.submit("I want to save 3L for medical emergencies")
check("wrong-construct still challenged",b["results"][0]["outcome"]=="at-risk",b["results"][0]["outcome"])

print("=== 6. shared audit envelope ===")
check("audit envelopes emitted",len(p.audit_log.records)>0,str(len(p.audit_log.records)))
errs=validate([p.audit_log.records[-1]],{"type":"array","items":SCHEMAS["AUDIT"]})
check("every envelope schema-valid",not errs,"; ".join(errs[:2]))
traces={r["trace_id"] for r in p.audit_log.records}
check("trace_id correlates a decision path",any(t.startswith("trc_asp_") for t in traces),str(sorted(traces)[:2]))
check("all 5 envelope keys present",all(set(("actor","action","evidence_ref","timestamp","trace_id"))<=set(r) for r in p.audit_log.records))

print("=== 7. no regression in existing suites ===")
run("test_mvp.py",["test_mvp.py"])
run("test_pipeline.py",["test_pipeline.py"])

print("\nP0 GATE:","ALL PASS" if not fails else f"{len(fails)} FAILURES {fails}")
sys.exit(1 if fails else 0)
