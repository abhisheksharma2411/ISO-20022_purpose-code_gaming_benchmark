#!/usr/bin/env python3
"""Re-derive the paper's numbers from the RAW per-run files (not summary.json)
and check each appears in the manuscript. Usage: verify_claims_v3.py <repo> <results-dir> <paper.tex> <supp.tex>"""
import glob, json, sys
import numpy as np
repo, RES, tex, supp = sys.argv[1:5]
S = json.load(open(f"{RES}/summary.json"))
mains = sorted([json.load(open(p)) for p in glob.glob(f"{RES}/phase1_main_seed*.json")], key=lambda m: m["config"]["seed"])
loos = [json.load(open(p)) for p in sorted(glob.glob(f"{RES}/phase2_loo_seed*.json"))]
text = open(tex).read() + open(supp).read()
fails = []
def check(name, a, b, tol=5e-4):
    ok = abs(a - b) <= tol; print(("OK   " if ok else "FAIL ") + f"{name}: raw {a:.4f} summary {b:.4f}")
    if not ok: fails.append(name)
def in_text(name, s):
    ok = s in text; print(("OK   " if ok else "FAIL ") + f"{name} '{s}' in manuscript")
    if not ok: fails.append(name)
assert sorted(m["config"]["seed"] for m in mains) == sorted(S["seeds"])
for d in S["detectors"]:
    for met in ("auc", "ap", "recovery@0.01", "precision@0.01", "recovery@0.001"):
        raw = float(np.mean([m["detectors"][d][met] for m in mains])); check(f"{d} {met}", raw, S["detectors"][d][met])
        in_text(f"{d} {met} text", f"{raw:.3f}")
c1 = float(np.mean([m["tpr_ceiling@0.01"] for m in mains])); check("ceiling", c1, S["tpr_ceiling@0.01"]); in_text("ceiling text", f"{c1:.3f}")
for fam in ("P1", "P2", "P3"):
    rows = [l[fam] for l in loos if "D2" in l.get(fam, {})]
    if not rows: continue
    for d in ("D1", "D5", "D7", "D2", "D6"):
        raw = float(np.mean([r[d] for r in rows])); check(f"LOO {fam} {d}", raw, S["loo"][fam][d]); in_text(f"LOO {fam} {d} text", f"{raw:.3f}")
    for d in ("D2", "D6"):
        raw = float(np.mean([r[d + "_matched_in"] for r in rows])); check(f"LOO {fam} {d} in", raw, S["loo"][fam][d + "_matched_in"]); in_text(f"LOO {fam} {d} in text", f"{raw:.3f}")
sys.path.insert(0, repo)
import iso20022_gaming_bench as B
for p in B.PRIMITIVES:
    rows = [m["sel"][p] for m in mains if "SEL" in m["sel"].get(p, {})]
    if not rows: continue
    raw = float(np.mean([r["SEL"] for r in rows])); check(f"SEL {p}", raw, S["sel"][p]["SEL"]); in_text(f"SEL {p} figure", f"({p},{raw:.3f})")
    for d in ("D1", "D2", "D5"):
        raw = float(np.mean([r[f"SEL_res_{d}"] for r in rows])); check(f"SEL_res {d} {p}", raw, S["sel"][p][f"SEL_res_{d}"]); in_text(f"SEL_res {d} {p} figure", f"({p},{raw:.3f})")
commit = mains[0]["config"]["git_commit"]; print("git commit:", commit)
if "dirty" in commit or commit == "unversioned": fails.append("provenance")
in_text("commit in text", commit[:12])
V = json.load(open(f"{RES}/phase7_validity.json")); in_text("XSD checked", f"{V['xsd']['checked']:,}".replace(",", "{,}"))
print(f"\n{len(fails)} failure(s)" + (": " + ", ".join(fails) if fails else "")); sys.exit(1 if fails else 0)
