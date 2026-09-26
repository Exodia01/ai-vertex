"""J1 ingestion: schema validation, consent tags, quarantine. Zero silent drops."""
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple
REQUIRED_TXN = ["id","date","amount","merchant","category","channel"]
REQUIRED_ACCT = ["balance"]

@dataclass
class RawTransaction:
    id: str; date: str; amount: float; merchant: str; category: str; channel: str
    consent_scope: List[str]; data_class: str = "observed_data"; note: str = ""

@dataclass
class RawAccountSnapshot:
    name: str; balance: float; consent_scope: List[str]; meta: Dict = None

def validate_txn(d: Dict) -> Tuple[bool,str]:
    for f in REQUIRED_TXN:
        if f not in d: return False, f"missing:{f}"
    try: float(d["amount"])
    except: return False, "bad:amount"
    if not str(d["merchant"]): return False, "bad:merchant"
    return True, "ok"

def ingest(feed_txns: List[Dict], feed_accts: Dict, consent_scope: List[str]):
    """Returns (txns, accts, quarantine, audit). Every record tagged."""
    txns, quarantine, audit = [], [], []
    for d in feed_txns:
        ok, reason = validate_txn(d)
        if not ok:
            quarantine.append({"record": d, "reason": reason})
            audit.append({"event":"ingest.transaction.quarantined","reason":reason})
            continue
        txns.append(RawTransaction(d["id"],d["date"],float(d["amount"]),str(d["merchant"]),
            str(d["category"]),str(d["channel"]),consent_scope,"observed_data",d.get("note","")))
        audit.append({"event":"ingest.transaction.received","id":d["id"]})
    accts = {}
    for k,v in feed_accts.items():
        bal = v.get("balance") if isinstance(v,dict) else v
        if bal is None:
            quarantine.append({"record":{k:v},"reason":"missing:balance"})
            continue
        accts[k]=RawAccountSnapshot(k,float(bal),consent_scope,v if isinstance(v,dict) else {})
        audit.append({"event":"ingest.account.received","account":k})
    return txns, accts, quarantine, audit
