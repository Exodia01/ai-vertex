"""Shared audit event envelope (Master §3.6, Anchor 1 §17).
One structure, one store, every anchor action. Schema-validated on emit."""
import itertools
from contracts import validate_event

ACTOR_ALIASES={"engine":"deterministic_engine","system":"deterministic_engine",
               "ai":"ai","customer":"customer","human":"human_auditor","anchor":"ai"}
_ctr=itertools.count(1)

def _norm_actor(a):
    a=ACTOR_ALIASES.get(a,a)
    base=a.split(".")[0]
    if base not in ("customer","ai","deterministic_engine","human_auditor","anchor1",
                    "anchor2","anchor3","anchor4"):
        raise ValueError(f"illegal audit actor {a!r}")
    return a

def _norm_action(a):
    a=a.lower()
    if not all(c.islower() or c.isdigit() or c in "._" for c in a):
        raise ValueError(f"illegal audit action {a!r}")
    return a

class AuditLog:
    def __init__(self, anchor=1):
        self.anchor=anchor; self.records=[]; self._seq=itertools.count(1)
    def emit(self, actor, action, evidence_ref, trace_id, contract_version="v1"):
        env={"actor":_norm_actor(actor),"action":_norm_action(action),
             "evidence_ref":evidence_ref,"timestamp":f"2026-09-26T{10+self._seq.peek()%12:02d}:00:00Z"
             if hasattr(self._seq,"peek") else "2026-09-26T10:00:00Z",
             "trace_id":trace_id,"anchor":self.anchor,"contract_version":contract_version}
        n=next(self._seq)
        env["timestamp"]=f"2026-09-26T{10+n%12:02d}:{(n//12)%60:02d}:00Z"
        errs=validate_event(env,"AUDIT")
        if errs: raise ValueError(f"invalid audit envelope: {errs[:2]}")
        self.records.append(env)
        return env
    def for_goal(self,goal_id):
        return [r for r in self.records if goal_id in str(r["evidence_ref"])]
