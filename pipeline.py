"""Pipeline orchestrator J1->J10. Deterministic math stays in J6; LLM never computes."""
import json, itertools
from j1_ingest import ingest
from j2_snapshot import build_snapshot
from j3_state import JournalStore
from j4_intent import extract_intent
from j5_mechanism import candidates
from j6_feasibility import compute
from j7_challenge import NudgeLog
from j8_stabilize import stabilize
from j9_memory import MemoryStore
from j10_monitor import Monitor
from audit import AuditLog
from contracts import PINNED

CUSTOMER_REF="cust_opaque_7f3a"
_ids=itertools.count(1)

class Pipeline:
    def __init__(self, mock_path="mock_aa.json", bench_path="benchmarks.json", memory_path="memory.jsonl"):
        self.mock=json.load(open(mock_path)); self.bench=json.load(open(bench_path))
        self.behaviour=self.mock.get("summary_3mo",{})
        self.store=JournalStore(); self.nudges=NudgeLog(); self.memory=MemoryStore(memory_path)
        self.monitor=Monitor(); self.audit_log=AuditLog(anchor=1)
        self.audit=[]; self.snapshot=None; self.quarantine=[]
        self.baseline=None
        self.goal_seq=0
        self._ingest_and_snapshot()
    def _trace(self, ref): return f"trc_{ref}_00000001"
    def _log(self, ev, actor="ai", **kw):
        """Emit the shared audit envelope. Keeps the legacy flat view for the UI."""
        rec={"event":ev, **kw}
        self.audit.append(rec)
        try:
            self.audit_log.emit(actor, ev.replace("STABILIZED_JOURNAL_STATE","journal_state.stabilized"),
                                kw.get("aspiration_id") or kw.get("goal_id") or "system",
                                self._trace(kw.get("aspiration_id") or kw.get("goal_id") or "sys"))
        except ValueError:
            pass
        return rec
    def _ingest_and_snapshot(self):
        txns,accts,q,aud=ingest(self.mock["transactions"],self.mock["accounts"],["txn.read","bal.read","profile.read"])
        self.txns=txns; self.quarantine=q
        for a in aud: self._log(a["event"])
        pattern=self.mock.get("summary_3mo",{}).get("income_pattern") or self.mock.get("income_pattern","flat")
        self.snapshot,ev=build_snapshot(self.mock.get("persona_id","persona"),txns,accts,
                                        self.mock["as_of"],income_pattern=pattern)
        self._log(ev["event"],reconciled=ev["reconciled"])
        if not ev["reconciled"]: raise ValueError("snapshot reconciliation failed")
        self.baseline=self.snapshot
    def submit(self, text, amount_override=None, horizon_override=None):
        aid=f"asp_{next(_ids):03d}"
        self.store.transition(aid,None,"raw_observation","observed_data",{"raw_text":text},text,"customer")
        self._log("aspiration.created",aspiration_id=aid)
        intent=extract_intent(text)
        if amount_override: intent["amount"]=amount_override
        if horizon_override: intent["horizon_mo"]=horizon_override
        if intent["objective_category"]=="unknown" or "clarify" in intent and intent["confidence"]<0.6:
            self.store.transition(aid,"raw_observation","interpreted_expectation","ai_hypothesis",intent,text,"ai")
            return {"aspiration_id":aid,"status":"needs_clarification","clarify":intent.get("clarify"),"intent":intent}
        self.store.transition(aid,"raw_observation","interpreted_expectation","ai_hypothesis",intent,text,"ai")
        self._log("intent.extracted",aspiration_id=aid,objective=intent["objective_category"],confidence=intent["confidence"])
        cands=candidates(intent)
        self.store.transition(aid,"interpreted_expectation","banking_equivalent","ai_hypothesis",{"candidates":cands},text,"ai")
        self._log("mechanism.candidates.generated",aspiration_id=aid,count=len(cands))
        results=[compute(c,self.snapshot,self.bench) for c in cands]
        for r in results: self._log("feasibility.computed",aspiration_id=aid,mechanism=r["mechanism"],outcome=r["outcome"],gap=r["gap_amount"])
        best=results[0]
        self.store.transition(aid,"banking_equivalent","analysis","observed_data",{"results":results},self.snapshot.balances and "mock_aa","deterministic_engine")
        packet={"aspiration_id":aid,"status":"analysed","intent":intent,"candidates":cands,"results":results}
        if best["outcome"]!="feasible":
            ch=self.nudges.issue(aid,best,all_results=results)
            if ch:
                self.store.transition(aid,"analysis","challenge","ai_hypothesis",{"challenge":ch["challenge"],"alternatives":ch["alternatives"]},best["mechanism"],"ai")
                self._log("challenge.issued",aspiration_id=aid,nudge_count=ch["nudge_count"])
                packet.update(ch)
            else:
                packet["status"]="analysis_pending"
                packet["note"]="nudge cap reached, challenge deferred"
        return packet
    def respond(self, aspiration_id, response, modified=None, sentiment=None):
        hist=self.store.history(aspiration_id)
        def latest(state):
            for e in reversed(hist):
                if e["state"]==state: return e
            return None
        intent=latest("interpreted_expectation")["payload"]
        cands=latest("banking_equivalent")["payload"]["candidates"]
        results=latest("analysis")["payload"]["results"]
        if response=="modify":
            newc=[dict(c) for c in cands]
            if modified and "target" in modified: newc[0]["required_capital"]=modified["target"]
            if modified and "timeline_mo" in modified: newc[0]["horizon_mo"]=modified["timeline_mo"]
            self.store.transition(aspiration_id,"analysis","customer_response","customer_confirmed_data",{"response":"modify","modified":modified or {}},modified or "customer","customer")
            self.store.transition(aspiration_id,"customer_response","banking_equivalent","customer_confirmed_data",{"candidates":newc},"customer_mod","ai")
            newres=[compute(c,self.snapshot,self.bench) for c in newc]
            self.store.transition(aspiration_id,"banking_equivalent","analysis","observed_data",{"results":newres},"mock_aa","deterministic_engine")
            out={"aspiration_id":aspiration_id,"status":"re-analysed","results":newres}
            if newres[0]["outcome"]!="feasible":
                ch=self.nudges.issue(aspiration_id,newres[0],all_results=newres)
                if ch:
                    self.store.transition(aspiration_id,"analysis","challenge","ai_hypothesis",{"challenge":ch["challenge"],"alternatives":ch["alternatives"]},newres[0]["mechanism"],"ai")
                    out.update(ch)
            return out
        if response=="reject":
            self.store.transition(aspiration_id,"analysis","customer_response","customer_rejected_interpretation",{"response":"reject"},"customer","customer")
            return {"aspiration_id":aspiration_id,"status":"abandoned"}
        feas=results[0]; cand=cands[0]
        self.store.transition(aspiration_id,"analysis","customer_response","customer_confirmed_data",{"response":"accept"},"customer","customer")
        self.goal_seq+=1; goal_id=f"goal_{self.goal_seq:03d}"
        rec=self.memory.add(goal_id,CUSTOMER_REF,intent["objective_category"],cand["mechanism"],
                            cand["required_capital"],cand["horizon_mo"],
                            extra={"feasibility_outcome":feas["outcome"],"aspiration_id":aspiration_id,
                                   "contract_version":PINNED})
        res=stabilize(aspiration_id,CUSTOMER_REF,intent,cand,feas,"accept",
                      version=rec["state_version"],
                      sentiment_band=(sentiment or {}).get("stress_band"),
                      confidence_band=(sentiment or {}).get("confidence_band"))
        if not res["stabilized"]: return {"aspiration_id":aspiration_id,"status":"not_stabilized"}
        self.store.transition(aspiration_id,"customer_response","stabilized_state","customer_confirmed_data",res["payload"],"customer","deterministic_engine")
        self._log("goal.stabilized",aspiration_id=aspiration_id,goal_id=goal_id,actor="customer")
        self._log("STABILIZED_JOURNAL_STATE",aspiration_id=aspiration_id,goal_id=goal_id,
                  actor="deterministic_engine",state_version=rec["state_version"])
        self.store.transition(aspiration_id,"stabilized_state","monitoring","observed_data",{"goal_id":goal_id},"memory","deterministic_engine")
        out={"aspiration_id":aspiration_id,"status":"stabilized","goal":rec,"event":res["payload"]}
        if "internal" in res: out["internal"]=res["internal"]
        return out
    def revise(self, goal_id, target=None, timeline_mo=None, sentiment=None):
        """J9 multi-revision path: re-run deterministic feasibility for an already
        stabilized goal and append a new version of the SAME goal_id."""
        revs=self.memory.revisions(goal_id)
        if not revs: return {"status":"not_found"}
        cur=revs[-1]
        cand={"mechanism":cur["mechanism"],"required_capital":target or cur["target"],
              "horizon_mo":timeline_mo or cur["timeline"],
              "liquidity_need":"high" if cur["objective"] in ("protection","liquidity") else "med",
              "financing_need":("loan" in cur["mechanism"].lower() or "emi" in cur["mechanism"].lower())}
        feas=compute(cand,self.snapshot,self.bench)
        self._log("feasibility.computed",actor="deterministic_engine",
                  goal_id=goal_id,mechanism=feas["mechanism"],outcome=feas["outcome"])
        rec=self.memory.add(goal_id,cur["customer_ref"],cur["objective"],cand["mechanism"],
                            cand["required_capital"],cand["horizon_mo"],
                            extra={"feasibility_outcome":feas["outcome"],
                                   "aspiration_id":cur.get("aspiration_id"),
                                   "contract_version":PINNED,
                                   "revision_reason":cur.get("revision_reason","customer_revised")})
        intent={"objective_category":cur["objective"]}
        res=stabilize(cur.get("aspiration_id","asp_000"),cur["customer_ref"],intent,cand,feas,
                      "accept",version=rec["state_version"],
                      sentiment_band=(sentiment or {}).get("stress_band"),
                      confidence_band=(sentiment or {}).get("confidence_band"))
        self._log("goal.stabilized",actor="customer",goal_id=goal_id,state_version=rec["state_version"])
        self._log("STABILIZED_JOURNAL_STATE",actor="deterministic_engine",goal_id=goal_id,
                  state_version=rec["state_version"])
        out={"status":"revised","goal":rec,"event":res["payload"],
             "revisions":[r["state_version"] for r in self.memory.revisions(goal_id)]}
        if "internal" in res: out["internal"]=res["internal"]
        return out

    def simulate_material_change(self, kind):
        from dataclasses import replace
        if kind=="income_drop":
            prev=self.baseline
            self.snapshot=replace(self.snapshot,income_monthly_avg=round(self.snapshot.income_monthly_avg*0.6,2))
            events=self.monitor.detect(CUSTOMER_REF,prev,self.snapshot,[])
        elif kind=="large_withdrawal":
            class T: amount=85000; id="txn_090"
            events=self.monitor.detect(CUSTOMER_REF,self.baseline,self.snapshot,[T()])
        else:
            return []
        out=[]
        for e in events:
            self._log(e["event"],trigger=e["trigger"])
            goals=self.memory.query(CUSTOMER_REF)
            for g in goals:
                if g.get("tombstone"): continue
                feas={"mechanism":g["mechanism"],"required_capital":g["target"],
                      "horizon_mo":g["timeline"],"liquidity_need":"med","financing_need":False}
                newr=compute(feas,self.snapshot,self.bench)
                if newr["outcome"]!="feasible":
                    ch=self.nudges.issue(g["aspiration_id"],newr,all_results=[newr])
                    out.append({"goal_id":g["goal_id"],"new_outcome":newr["outcome"],
                                "monthly_need":newr["monthly_need"],"challenge":(ch or {}).get("challenge"),
                                "alternatives":(ch or {}).get("alternatives",[])})
                else:
                    out.append({"goal_id":g["goal_id"],"new_outcome":newr["outcome"]})
        return out
    def memory_view(self): return self.memory.query(CUSTOMER_REF)
    def funnel(self):
        f={}
        for e in self.store.entries:
            f[e["state"]]=f.get(e["state"],0)+1
        f["quarantined"]=len(self.quarantine)
        f["nudges_issued"]=sum(v["n"] for v in self.nudges.d.values())
        return f
