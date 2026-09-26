"""J10 continuous monitoring: small fixed trigger set, rate-limited."""
LARGE_WITHDRAWAL=50000
INCOME_DROP_PCT=0.20
class Monitor:
    def __init__(self, rate_limit=1):
        self.rate_limit=rate_limit; self.fired={}
    def detect(self, customer_ref, prev_snapshot, new_snapshot, new_txns):
        events=[]
        for t in new_txns or []:
            amt=t.amount if hasattr(t,"amount") else t.get("amount",0)
            if amt>=LARGE_WITHDRAWAL:
                events.append({"type":"large_withdrawal","amount":amt,"ref":getattr(t,"id",None)})
        if prev_snapshot and new_snapshot:
            p=prev_snapshot.income_monthly_avg; n=new_snapshot.income_monthly_avg
            if p>0 and (p-n)/p>=INCOME_DROP_PCT:
                events.append({"type":"income_drop","from":p,"to":n})
        out=[]
        for e in events:
            c=self.fired.get(customer_ref,0)
            if c>=self.rate_limit: continue
            self.fired[customer_ref]=c+1
            out.append({"event":"reanalysis.triggered","customer_ref":customer_ref,"trigger":e})
        return out
