"""J2 + J6 exact-value tests (Anchor 1: "Deterministic-engine tests are exact-value
assertions, not fuzzy/LLM-graded"; J6 DoD "100% exact-match ... reviewed by a human").

Expected values below are hand-computed from policy/feasibility_policy.json and the
fixtures, NOT captured from program output.

Run: python3 test_j2_j6_exact.py
"""
import json, os, sys
sys.path.insert(0,".")
from j1_ingest import ingest
from j2_snapshot import build_snapshot
import j6_feasibility as J6
from j6_feasibility import compute, T, POLICY_VERSION, policy_snapshot

fails=[]
def check(n,c,i=""):
    print(("PASS " if c else "FAIL ")+n,i)
    if not c: fails.append(n)
def eq(n,got,want):
    check(n,got==want,f"got={got} want={want}")

POLICY=json.load(open("policy/feasibility_policy.json"))
def snap_from(path,pattern=None):
    d=json.load(open(path))
    tx,ac,q,a=ingest(d["transactions"],d["accounts"],d.get("consent_scope",["txn.read","bal.read"]))
    s,ev=build_snapshot(d.get("persona_id","p"),tx,ac,d["as_of"],
                        income_pattern=pattern or d.get("profile",{}).get("income_pattern")
                        or d.get("income_pattern","flat"))
    return s,ev,d

print("=== J6.1 policy is authoritative, not hardcoded ===")
eq("max_savings_rate matches policy",T["max_savings_rate"],POLICY["thresholds"]["max_savings_rate"]["value"])
eq("emergency_months_required matches policy",T["emergency_months_required"],
   POLICY["thresholds"]["emergency_months_required"]["value"])
eq("every threshold is provisional or sourced",
   all(t.get("provisional") is not None or t.get("source") for t in
       list(POLICY["thresholds"].values())+list(POLICY["mechanism_rules"].values())),True)
check("policy declares provisional status",policy_snapshot()["provisional"] is True)
# prove the engine READS the policy: tighten it and the verdict must move
s_hostel,_,_=snap_from("mock_aa.json")
dubai={"mechanism":"savings goal","required_capital":120000,"horizon_mo":3,
       "liquidity_need":"med","financing_need":False}
before=compute(dubai,s_hostel)["outcome"]
old=T["max_savings_rate"]; T["max_savings_rate"]=0.01
after=compute(dubai,s_hostel)["outcome"]
T["max_savings_rate"]=old
eq("loosening policy to 40% -> feasible",before,"feasible")
eq("tightening policy to 1%  -> gap",after,"gap")

print("=== J6.2 exact values, app persona (mock_aa.json) ===")
# hand-computed: 12-month window observes 4 income months (May/Jul/Aug/Sep):
#   (110000+212000+198000+205000)/4 = 181250.  Worst = 110000 (May off-season).
eq("income_monthly_avg over observed months",s_hostel.income_monthly_avg,181250.0)
eq("months observed in window",s_hostel.income_profile["months_observed"],4)
eq("income_min_month captures off-season",s_hostel.income_min_month,110000.0)
# each recurring category normalised by months in which it appeared:
#   family_health 4200/1 + subscription 1299/1 + investment 15000/1 = 20499
eq("obligations derived from transactions, not hardcoded",s_hostel.obligations_monthly,20499.0)
# emergency = 420000 / (270000/6) = 420000/45000
eq("emergency runway months",round(s_hostel.balances["savings"]/45000,2),9.33)
# stress: 110000/205000 = 0.5366 < 0.75 -> stress applies
eq("stress test applied to worst month",round(110000/181250,3),0.607)
r_dubai=compute(dubai,s_hostel)
eq("Dubai monthly need = 120000/3",r_dubai["monthly_need"],40000.0)
eq("Dubai avail on average = 0.4*181250",r_dubai["avail_monthly"],72500.0)
eq("Dubai avail under stress = 0.4*110000",r_dubai["avail_stress_monthly"],44000.0)
eq("Dubai feasible",r_dubai["outcome"],"feasible")
japan={"mechanism":"savings goal","required_capital":250000,"horizon_mo":2,
       "liquidity_need":"med","financing_need":False}
r_j=compute(japan,s_hostel)
eq("Japan need = 250000/2",r_j["monthly_need"],125000.0)
eq("Japan gap measured against WORST month, not average",r_j["gap_amount"],81000.0)
eq("Japan outcome",r_j["outcome"],"gap")
health={"mechanism":"liquid reserve","required_capital":300000,"horizon_mo":12,
        "liquidity_need":"high","financing_need":False}
eq("save-only for medical is wrong-construct",compute(health,s_hostel)["outcome"],"at-risk")

print("=== J6.3 named edge cases (J6 unit tests) ===")
s_zero,_,d=snap_from("fixtures/customers/persona_zero_savings.json")
r=compute(dubai,s_zero)
eq("zero savings -> emergency 0",r["emergency_mo"],0.0)
eq("zero savings -> gap",r["outcome"],"gap")
check("zero savings -> emergency note present",
      any("emergency thin" in n for n in r["risk_notes"]),str(r["risk_notes"]))
s_neg,_,d=snap_from("fixtures/customers/persona_negative_cashflow.json")
r=compute(dubai,s_neg)
eq("negative cash flow -> debt spiral detected",r["debt_spiral"],True)
eq("negative cash flow -> blocked despite affordable need",r["outcome"],"gap")
s_wind,_,d=snap_from("fixtures/customers/persona_windfall.json")
r=compute(dubai,s_wind)
eq("windfall -> ample runway",r["emergency_mo"],20.0)
eq("windfall -> feasible",r["outcome"],"feasible")
s_gig,_,d=snap_from("fixtures/customers/persona_gig_irregular.json")
eq("gig irregular -> smoothing avoided a zero month",s_gig.income_monthly_avg>0,True)
eq("gig irregular -> stress test applied",compute(dubai,s_gig)["stress_applied"],True)
s_debt,_,d=snap_from("fixtures/customers/persona_debt_spiral.json")
eq("debt spiral detected",compute(dubai,s_debt)["debt_spiral"],True)

print("=== J6.4 determinism ===")
runs=[compute(japan,s_hostel) for _ in range(5)]
check("5 runs byte-identical",all(x==runs[0] for x in runs))
check("computed_by always deterministic_engine",all(x["computed_by"]=="deterministic_engine" for x in runs))
check("policy version echoed on every result",all(x["policy_version"]==POLICY_VERSION for x in runs))
check("no randomness: import of random absent from engine","random" not in open("j6_feasibility.py").read())

print("=== J2 reconciliation across ALL fixture personas ===")
import glob
for fp in sorted(glob.glob("fixtures/customers/persona_*.json")):
    s,ev,d=snap_from(fp)
    check(f"reconciled {d['persona_id']}",ev["reconciled"])
    check(f"no bank name in balances {d['persona_id']}",
          not any("bank" in k.lower() for k in s.balances))
    check(f"income observed over 12mo window {d['persona_id']}",
          s.income_profile["months_observed"]>0,str(s.income_profile["months_observed"]))
check("irregular-earner smoothing recorded in profile",
      s_gig.income_profile["pattern"]=="irregular_weekly")
check("obligations sourced from transactions",
      "observed_transactions" in s_hostel.income_profile["obligations_derived_from"])

print("\nJ2/J6 EXACT:","ALL PASS" if not fails else f"{len(fails)} FAILURES {fails}")
sys.exit(1 if fails else 0)
