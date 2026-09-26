"""Deterministic synthetic fixture generator (Master §4).

Seeded so CI is reproducible. Produces personas with 12-24 months of history,
including the irregular-income, zero-savings, negative-cash-flow and windfall
edge cases named in Anchor 1 J2/J6 unit tests.

Run: python3 fixtures/generate.py
"""
import json, os, random
HERE=os.path.dirname(os.path.abspath(__file__))

PERSONAS=[
 {"id":"persona_hostel_tier2","label":"Guest_44","band":"mid","life_stage":"family_with_child",
  "risk":"moderate","monthly_income":205000,"income_pattern":"seasonal","savings":420000,
  "fd":600000,"mf":1200000,"debt":0,"obligations":19200,
  "note":"off-season dip to ~110k; peak ~240k"},
 {"id":"persona_gig_irregular","label":"Guest_28","band":"low","life_stage":"single",
  "risk":"high","monthly_income":38000,"income_pattern":"irregular_weekly","savings":18000,
  "fd":0,"mf":0,"debt":95000,"obligations":6000,
  "note":"J2 named case: irregular-income smoothing"},
 {"id":"persona_zero_savings","label":"Guest_52","band":"mid","life_stage":"pre_retiree",
  "risk":"high","monthly_income":74000,"income_pattern":"flat","savings":0,
  "fd":0,"mf":0,"debt":240000,"obligations":31000,
  "note":"J6 named case: zero savings"},
 {"id":"persona_negative_cashflow","label":"Guest_36","band":"low","life_stage":"single",
  "risk":"high","monthly_income":42000,"income_pattern":"flat","savings":5000,
  "fd":0,"mf":0,"debt":410000,"obligations":38000,
  "note":"J6 named case: negative cash flow (spend exceeds income)"},
 {"id":"persona_windfall","label":"Guest_41","band":"high","life_stage":"family",
  "risk":"low","monthly_income":180000,"income_pattern":"flat","savings":900000,
  "fd":300000,"mf":1500000,"debt":0,"obligations":22000,
  "note":"J6 named case: sudden windfall (inheritance credit)"},
 {"id":"persona_debt_spiral","label":"Guest_31","band":"low","life_stage":"single",
  "risk":"high","monthly_income":58000,"income_pattern":"flat","savings":9000,
  "fd":0,"mf":0,"debt":680000,"obligations":29000,
  "note":"Master §4 edge case: debt spiral"},
]

CATS=[("FoodDeliveryCo","food_delivery",(300,900),.22),("MarketPlace","shopping",(400,2500),.10),
      ("StreamingBundle","subscription",(149,999),.04),("Family pharmacy","family_health",(800,5000),.05),
      ("Hostel maintenance","hostel_ops",(1500,9000),.06),("FuelCo","transport",(500,2000),.08),
      ("GroceryCo","essentials",(800,3500),.20),("ApparelCo","shopping",(600,3000),.05),
      ("RechargeCo","utilities",(200,1200),.10),("MiscVendor","misc",(100,900),.10)]

def monthly_income(pattern,base,month_idx,rng):
    if pattern=="seasonal":
        if month_idx in (4,5,6): return int(base*0.54)
        if month_idx in (10,11): return int(base*1.17)
        return base
    if pattern=="irregular_weekly":
        return int(max(0,base + rng.randint(-int(base*0.9),int(base*0.7))))
    return base

def generate_persona(p,months=18,seed=7):
    rng=random.Random(f"{p['id']}::{seed}")
    txns=[]; n=0
    year,month=2025,4
    for m in range(months):
        for _ in range(1):
            inc=monthly_income(p["income_pattern"],p["monthly_income"],m,rng)
            if inc>0:
                n+=1
                txns.append({"id":f"txn_{n:04d}","date":f"{year}-{month:02d}-15","amount":inc,
                             "merchant":f"{p['label']} operations","category":"income",
                             "channel":"bank","time":"10:00","note":"monthly aggregate"})
        budget=max(4000,p["monthly_income"]*0.92)-p["obligations"]
        for _ in range(rng.randint(14,22)):
            name,cat,(lo,hi),w=rng.choices(CATS,weights=[c[3] for c in CATS])[0]
            amt=rng.randint(lo,hi)
            if rng.random()<0.10: amt=int(amt*rng.uniform(2.0,4.5))
            n+=1
            txns.append({"id":f"txn_{n:04d}","date":f"{year}-{month:02d}-{rng.randint(1,28):02d}",
                         "amount":amt,"merchant":name,"category":cat,"channel":
                         rng.choice(["UPI","UPI","card"]),"time":f"{rng.randint(8,23):02d}:00","note":""})
        if p["id"]=="persona_windfall" and m==months-2:
            n+=1
            txns.append({"id":f"txn_{n:04d}","date":f"{year}-{month:02d}-20","amount":2500000,
                         "merchant":"Inheritance credit","category":"income","channel":"bank",
                         "time":"12:00","note":"J6 named case: windfall"})
        month+=1
        if month>12: month=1; year+=1
    return {"persona_id":p["id"],"label":p["label"],"as_of":"2026-09-26",
            "profile":{"income_band":p["band"],"life_stage":p["life_stage"],"risk_profile":p["risk"],
                       "income_pattern":p["income_pattern"],"note":p["note"]},
            "accounts":{"savings":{"bank":f"FixtureBank {p['label'][-2:]}","balance":p["savings"]},
                        "fd":{"balance":p["fd"],"rate":"7.1%"},
                        "mf":{"balance":p["mf"]},
                        "debt":{"balance":p["debt"],"rate":"0.14"},
                        "recurring_obligations":p["obligations"]},
            "consent_scope":["txn.read","bal.read","profile.read"],
            "summary_3mo":{"inflow_total":sum(t["amount"] for t in txns[-90:] if t["category"]=="income"),
                           "spend_total":sum(t["amount"] for t in txns[-90:] if t["category"]!="income"),
                           "random_leak":0,"joy":0,
                           "top_leaks":[],"travel_spend":0,"signals":[]},
            "transactions":txns}

def main():
    os.makedirs(os.path.join(HERE,"customers"),exist_ok=True)
    idx=[]
    for p in PERSONAS:
        d=generate_persona(p)
        fp=os.path.join(HERE,"customers",p["id"]+".json")
        with open(fp,"w") as f: json.dump(d,f,indent=1)
        debits=[t for t in d["transactions"] if t["category"]!="income"]
        leaks={}
        for t in debits: leaks[t["category"]]=leaks.get(t["category"],0)+t["amount"]
        d["summary_3mo"]["random_leak"]=int(sum(leaks.values())*0.18)
        d["summary_3mo"]["joy"]=int(sum(leaks.values())*0.04)
        d["summary_3mo"]["top_leaks"]=[{"merchant":k,"total":v,"count":sum(1 for t in debits if t["category"]==k)}
                                       for k,v in sorted(leaks.items(),key=lambda x:-x[1])[:3]]
        d["summary_3mo"]["signals"]=[d["profile"]["note"]] if d["profile"]["note"] else []
        with open(fp,"w") as f: json.dump(d,f,indent=1)
        idx.append({"persona_id":p["id"],"label":p["label"],"band":p["band"],
                    "risk":p["risk"],"months":18,"transactions":len(d["transactions"]),
                    "edge_case":d["profile"]["note"]})
    with open(os.path.join(HERE,"customers","index.json"),"w") as f: json.dump(idx,f,indent=1)
    print(f"generated {len(idx)} personas -> fixtures/customers/")
    for i in idx: print(f"  {i['persona_id']:28} {i['transactions']:4d} txns  {i['edge_case']}")

if __name__=="__main__": main()
