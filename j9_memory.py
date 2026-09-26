"""J9 financial memory: append-only, versioned, queryable, tombstonable.
Every record carries the same shape (tombstones included) so downstream consumers
never have to branch on record type."""
import json, os

class MemoryStore:
    def __init__(self, path="memory.jsonl"):
        self.path=path
        if not os.path.exists(path): open(path,"w").close()
    def _read(self):
        out=[]
        for line in open(self.path):
            line=line.strip()
            if line: out.append(json.loads(line))
        return out
    def _append(self, rec):
        with open(self.path,"a") as f: f.write(json.dumps(rec)+"\n")
    def _next_version(self, goal_id):
        return sum(1 for r in self._read()
                   if r.get("goal_id")==goal_id and not r.get("tombstone"))+1
    def add(self, goal_id, customer_ref, objective, mechanism, target, timeline, extra=None):
        version=self._next_version(goal_id)
        rec={"record_type":"goal","goal_id":goal_id,"customer_ref":customer_ref,
             "objective":objective,"mechanism":mechanism,"target":target,"timeline":timeline,
             "confirmed_at":"2026-09-26T10:00:00Z","state_version":f"v{version}",
             "tombstone":False}
        if extra: rec.update(extra)
        self._append(rec)
        return rec
    def history(self, goal_id):
        return [r for r in self._read() if r.get("goal_id")==goal_id]
    def revisions(self, goal_id):
        return [r for r in self.history(goal_id)
                if r.get("record_type")=="goal" and not r.get("tombstone")]
    def query(self, customer_ref):
        return [r for r in self._read() if r.get("customer_ref")==customer_ref]
    def tombstone(self, goal_id, reason="consent_withdrawn"):
        prior=[r for r in self.revisions(goal_id)]
        if not prior: return []
        self._append({"record_type":"tombstone","goal_id":goal_id,
                      "customer_ref":prior[0]["customer_ref"],
                      "objective":prior[0]["objective"],"mechanism":prior[0]["mechanism"],
                      "target":prior[0]["target"],"timeline":prior[0]["timeline"],
                      "confirmed_at":"2026-09-26T10:00:00Z",
                      "state_version":prior[-1]["state_version"],
                      "tombstone":True,"reason":reason,
                      "retracts":[r["state_version"] for r in prior]})
        return [r["state_version"] for r in prior]
