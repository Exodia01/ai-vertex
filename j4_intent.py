"""J4 intent extraction. Output always ai_hypothesis. Low conf -> clarifying question."""
import re
RULES=[
 ("travel",["japan","dubai","trip","flight","lounge","vacation","holiday"]),
 ("asset",["car","house","bike","flat"]),
 ("protection",["medical","emergency","parents","insurance","health","protect","surgery","hospital","treatment"]),
 ("liquidity",["save","saving","reserve","emergency fund"]),
 ("wealth",["invest","sip","wealth","mutual"]),
 ("debt",["loan","emi","debt","refinance"]),
]
MONTH_WORDS=("month","months","mo","yr","year","years","%","percent")
NUM=re.compile(r"(?:₹\s*|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(l|lakh|lakhs|cr|crores?)?\b", re.I)
NEXT_WORD=re.compile(r"\s*([A-Za-z%]+)")
def _next_word(text,pos):
    m=NEXT_WORD.match(text,pos)
    return m.group(1).lower() if m else ""
def _extract_amount(text):
    for m in NUM.finditer(text):
        if _next_word(text,m.end()) in MONTH_WORDS: continue
        unit=(m.group(2) or "").lower()
        val=float(m.group(1))
        if unit in ("l","lakh","lakhs"): return int(val*100000)
        if unit.startswith("cr"): return int(val*10000000)
        token=m.group(0).strip().lower()
        if token.startswith("₹") or token.startswith("rs"): return int(val)
    return None

STATED=[
 ("savings",["save","saving","bacha","bachao","jama","jamao","rakho","side me","reserve"]),
 ("insurance",["insurance","bima","cover","policy"]),
 ("loan",["loan","emi","borrow","udhaar"]),
 ("investment",["sip","invest","mutual","mf","share"]),
]
def _stated_mechanism(t):
    hits={}
    for mech,keys in STATED:
        s=sum(1 for k in keys if k in t)
        if s: hits[mech]=s
    return max(hits,key=hits.get) if hits else None

CONTRADICTION_MARKERS=[r"but also",r"but i also",r"and also",r"at the same time",
                       r"as well as",r"or maybe",r"confused",r"not sure which",r"either",r"or"]
CLARIFY_CONTRADICT=("Suna main ne do cheezein ek saath — tumhe pehle kaun si sortani hai? "
                    "Ek line me batao, phir main dusri par bhi usi hisaab se sochta hun.")
_MARKER_RE=re.compile(r"\b(?:"+"|".join(CONTRADICTION_MARKERS)+r")\b")

def _detect_contradiction(t,hits,stated):
    """A genuine ambiguity, not a keyword-count guess.

    Two objectives of equal strength mean we must ask rather than pick - UNLESS the customer
    has named a financing mechanism, which legitimately co-occurs with the goal it funds
    ("a 15L car on EMI" is one goal, not a conflict between an asset and a debt)."""
    if len(hits)<2: return False
    top=sorted(hits.values(),reverse=True)
    if top[0]-top[1]>=2: return False          # one objective clearly dominates
    if stated is not None: return False        # stated mechanism explains the pairing
    return True

def extract_intent(text: str):
    t=text.lower(); hits={}
    for obj,keys in RULES:
        s=sum(1 for k in keys if k in t)
        if s: hits[obj]=s
    amt=_extract_amount(text)
    tm=re.search(r"(\d+)\s*(?:mo|month)",t)
    horizon=int(tm.group(1)) if tm else 12
    stated=_stated_mechanism(t)
    if not hits:
        return {"objective_category":"unknown","confidence":0.0,"amount":amt,"horizon_mo":horizon,
                "stated_mechanism":stated,
                "data_class":"ai_hypothesis","clarify":"Aap kya chahte ho — travel, car/house, medical safety, saving ya loan? Ek line me batao."}
    best=max(hits,key=hits.get); conf=min(0.95,0.5+0.2*hits[best])
    out={"objective_category":best,"confidence":round(conf,2),"amount":amt,"horizon_mo":horizon,
         "stated_mechanism":stated,"data_class":"ai_hypothesis","alternatives_considered":sorted(hits)}
    if _detect_contradiction(t,hits,stated) or (len(hits)>1 and _MARKER_RE.search(t)):
        out["objective_category"]="contradictory"
        out["confidence"]=0.0
        out["clarify"]=CLARIFY_CONTRADICT
        out["data_class"]="ai_hypothesis"
        return out
    if conf<0.6: out["clarify"]="Thoda aur batao — kitna paisa, kab tak? (e.g. Dubai 1.2L Dec)"
    return out
