"""Synthetic-data linter (Master §4).

Blocks fixtures that resemble real account numbers, real institution names, or real PII.
Run in CI. Exit 1 on any finding so a pipeline can gate on it.
"""
import json, os, re, sys

REAL_INSTITUTIONS=[
 "hdfc","icici","sbi","state bank","axis bank","kotak","punjab national","bank of baroda",
 "canara","union bank","indusind","yes bank","kotak mahindra","idfc","au small finance",
 "paytm","phonepe","gpay","google pay","bhim","upi id","swift","visa","mastercard","rupay select",
]
NAME_HINTS=["ramesh","bhopal","suresh","anil","sunita","priya","amit","kavita","delhi","mumbai",
            "chennai","kolkata","jaipur","lucknow"]
# 12-19 digit runs, and common Indian bank card/bin shapes
ACCOUNT_PATTERNS=[
 (r"\b\d{12,19}\b","long digit run resembles an account/card number"),
 (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b","16-digit card-like number"),
 (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b","12-digit card-like number"),
 (r"\b[A-Z]{4}0[A-Z0-9]{6,}\b","PAN-like identifier"),
 (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b","email address"),
 (r"\b(\+91[-\s]?)?[6-9]\d{9}\b","10-digit phone number"),
 (r"\b\d{4}\s?\d{4}\s?\d{4}\b","aadhaar-like 12-digit number"),
]
# Deny-lists and negative test fixtures intentionally contain banned literals in order to
# assert their ABSENCE from emitted events. Exempt from the institution/name rules ONLY;
# still checked for card-like numbers, emails and JSON validity.
EXEMPT={
 "contracts.py",            # boundary deny-list
 "synthetic_linter.py",     # this file's own deny-list
 "test_mvp.py",             # asserts bank/PII strings never reach the snapshot or event
 "test_pipeline.py",        # asserts bank/PII strings never reach the snapshot or event
 "validate_contracts.py",   # asserts non-opaque customer_ref is rejected by the schema
}

def lint_text(text, exempt=False):
    findings=[]
    if '"_synthetic": true' in text.replace("'", '"'):
        return findings
    low=text.lower()
    if not exempt:
        for inst in REAL_INSTITUTIONS:
            if inst in low:
                findings.append(f"real institution name '{inst}'")
                break
        for name in NAME_HINTS:
            if re.search(rf"\b{name}\b",low):
                findings.append(f"real-world name/place hint '{name}'")
                break
    for pat,why in ACCOUNT_PATTERNS:
        for m in re.finditer(pat,text):
            findings.append(f"{why}: '{m.group(0)[:4]}...'")
            break
    return findings

def lint_file(path):
    try: raw=open(path).read()
    except Exception as e: return [f"unreadable: {e}"]
    findings=lint_text(raw, exempt=os.path.basename(path) in EXEMPT)
    if path.endswith(".json"):
        try: json.loads(raw)
        except Exception as e: findings.append(f"invalid JSON: {e}")
    return findings

def lint_paths(paths):
    report={}
    for root in paths:
        if os.path.isfile(root):
            f=lint_file(root)
            if f: report[root]=f
        else:
            for dirpath,_,files in os.walk(root):
                for fn in files:
                    if not fn.endswith((".json",".jsonl",".md",".py")): continue
                    if fn.startswith("."): continue
                    fp=os.path.join(dirpath,fn)
                    if os.path.abspath(fp)==os.path.abspath(__file__): continue
                    f=lint_file(fp)
                    if f: report[fp]=f
    return report

if __name__=="__main__":
    args=sys.argv[1:] or ["fixtures","mock_aa.json","soul.json"]
    rep=lint_paths(args)
    if not rep:
        print("LINT PASS: no synthetic-data violations in", ", ".join(args))
        sys.exit(0)
    print("LINT FAIL")
    for path,f in rep.items():
        print(f"  {path}")
        for x in f: print(f"    - {x}")
    sys.exit(1)
