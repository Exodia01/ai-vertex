"""J7 challenge/nudge with cap 5 per aspiration. Fails closed."""
CAP=5
class NudgeLog:
    def __init__(self): self.d={}
    def count(self,a): return self.d.get(a,{"n":0})["n"]
    def issue(self, aspiration_id, feas, all_results=None, target=None):
        st=self.d.get(aspiration_id,{"n":0})
        if st["n"]>=CAP: return None
        gap_txt=(f"Need Rs {feas['monthly_need']:,.0f}/mo vs safe Rs {feas['avail_monthly']:,.0f}/mo. "
                 if feas["outcome"]=="gap" else
                 ("Sirf paise bachana is kaam ka nahi — bima ke bina ek bada medical aa gaya to sab khatam. "
                  if feas["outcome"]=="at-risk" else "Looks safe. "))
        alts=[]
        if feas["outcome"]=="gap":
            alts=[{"type":"timeline","description":"Extend horizon so need<=avail"},
                  {"type":"target","description":"Reduce target to fit cash flow"},
                  {"type":"mechanism","description":"Switch mechanism (e.g. EMI vs cash)"}]
        elif feas["outcome"]=="at-risk":
            better=[r["mechanism"] for r in (all_results or []) if r["outcome"]=="feasible"]
            alts=[{"type":"mechanism",
                   "description":(f"Switch to {better[0]}" if better else "insurance+reserve instead of save-only")}]
            gap_txt+=(f" {better[0]} se ye chalega. " if better else "")
        st["n"]+=1; st.update({"last_severity":"info"}); self.d[aspiration_id]=st
        return {"challenge":f"Bhai, {gap_txt}How do we get you what you actually want?",
                "alternatives":alts,"nudge_count":st["n"]}
