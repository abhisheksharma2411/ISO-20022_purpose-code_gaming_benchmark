#!/usr/bin/env python3
"""Re-derive the paper's headline numbers from the RAW per-run result files and
compare them with results/summary.json and with the manuscript text.

Independent of run_protocol's summariser: everything here is recomputed from
phase1_main_seed*.json, phase2_loo.json, phase3_eta_sweep.json,
phase4_ablations.json and phase5_calibration_grid.json.

Usage: verify_claims.py <repo> <paper.tex>
"""
import glob, json, re, sys
import numpy as np

repo, tex = sys.argv[1:3]
R = f"{repo}/results"
S = json.load(open(f"{R}/summary.json"))
mains = [json.load(open(p)) for p in sorted(glob.glob(f"{R}/phase1_main_seed*.json"))]
assert [m["config"]["seed"] for m in mains] == S["seeds"], "seed set differs"
text = open(tex).read()
fails = []
def check(name, a, b, tol=5e-4):
    ok = abs(a - b) <= tol
    print(("OK   " if ok else "FAIL ") + f"{name}: raw {a:.4f} vs summary {b:.4f}")
    if not ok: fails.append(name)
def in_text(name, s):
    ok = s in text
    print(("OK   " if ok else "FAIL ") + f"{name} '{s}' in manuscript")
    if not ok: fails.append(name)

n = mains[0]["n"]
ng = [m["n_gamed"] for m in mains]
for d in S["detectors"]:
    for met in ("auc", "ap", "tpr@0.01", "tpr@0.001"):
        raw = float(np.mean([m["detectors"][d][met] for m in mains]))
        check(f"{d} {met}", raw, S["detectors"][d][met])
    # every mean in the main table must appear in the text at 3 dp
    in_text(f"{d} auc text", f"{S['detectors'][d]['auc']:.3f}")
    in_text(f"{d} rec@1% text", f"{S['detectors'][d]['tpr@0.01']:.3f}")
ceil = float(np.mean([0.01 * n / g for g in ng]))
check("ceiling@1%", ceil, S["tpr_ceiling@0.01"])
in_text("ceiling text", f"{ceil:.3f}")
# D1 fills the 0.1% capacity with gamed records (stated in the text)
ben = [m["detectors"]["D1"]["benign_alerts_per_M@0.001"] for m in mains]
print(("OK   " if max(ben) == 0 else "FAIL ") + f"D1 zero benign alerts at 0.1%: {ben}")
if max(ben) != 0: fails.append("D1 benign@0.1%")
# no detector saturates the 1% capacity (the text says D2 recovers a share of the ceiling)
sat = [d for d in S["detectors"] if abs(S["detectors"][d]["tpr@0.01"] - ceil) < 0.005]
print(("OK   " if not sat else "FAIL ") + f"no detector saturates 1% capacity: {sat}")
if sat: fails.append("saturation")
# LOO
loo_seeds = [json.load(open(p)) for p in sorted(glob.glob(f"{R}/phase2_loo_seed*.json"))]
for fam in ("P1", "P2", "P3"):
    for d in ("D1", "D4", "D5", "D2", "D6"):
        raw = float(np.mean([l[fam][d] for l in loo_seeds]))
        check(f"LOO {fam} {d}", raw, S["loo"][fam][d])
        in_text(f"LOO {fam} {d} text", f"{S['loo'][fam][d]:.3f}")
    for d in ("D2", "D6"):
        raw = float(np.mean([l[fam][d + "_matched_in"] for l in loo_seeds]))
        check(f"LOO {fam} {d} in", raw, S["loo"][fam][d + "_matched_in"])
        in_text(f"LOO {fam} {d} in text", f"{S['loo'][fam][d+'_matched_in']:.3f}")
# SEL means and residuals (D4) from raw per-seed tables
for p, v in S["sel"].items():
    raw = float(np.mean([m["sel"][p]["SEL"] for m in mains]))
    check(f"SEL {p}", raw, v["SEL"])
    rawr = float(np.mean([m["sel"][p]["SEL_res"] for m in mains]))
    check(f"SEL_res(D4) {p}", rawr, v["SEL_res"])
    in_text(f"SEL {p} figure", f"({p},{v['SEL']:.3f})")
    in_text(f"SEL_res {p} figure", f"({p},{v['SEL_res']:.3f})")
for p, v in S["sel_D5"].items():
    rawr = float(np.mean([m["sel_D5"][p]["SEL_res"] for m in mains]))
    check(f"SEL_res(D5) {p}", rawr, v["SEL_res"])
    in_text(f"SEL_res5 {p} figure", f"({p},{v['SEL_res']:.3f})")
# unevaded controls and delta0
nu = [m["sel"]["_baseline"]["n_unevaded_illicit"] for m in mains]
d0 = [m["sel"]["_baseline"]["delta0"] for m in mains]
print("unevaded per seed", nu, "delta0", d0)
in_text("unevaded range", f"{min(nu)}--{max(nu)}")
# eta sweep and grid and ablations
eta = json.load(open(f"{R}/phase3_eta_sweep.json"))
for e, dets in eta.items():
    for d in ("D1", "D3", "D4", "D5"):
        in_text(f"eta {e} {d} figure", f"({float(e):.2f},{dets[d]['auc']:.4f})")
grid = json.load(open(f"{R}/phase5_calibration_grid.json"))
gsel = [v["SEL_min"] for v in grid.values()] + [v["SEL_max"] for v in grid.values()]
gauc = [v["detectors"]["D4"]["auc"] for v in grid.values()]
in_text("grid SEL min", f"{min(gsel):.2f}"); in_text("grid SEL max", f"{max(gsel):.2f}")
in_text("grid D4 min", f"{min(gauc):.3f}"); in_text("grid D4 max", f"{max(gauc):.3f}")
abl = json.load(open(f"{R}/phase4_ablations.json"))
for a in abl:
    in_text(f"ablation {a['setting']} D4", f"{a['detectors']['D4']['auc']:.3f}")
    in_text(f"ablation {a['setting']} D5", f"{a['detectors']['D5']['auc']:.3f}")
# provenance
commit = mains[0]["config"]["git_commit"]
print("git commit in results:", commit)
if "dirty" in commit or commit == "unversioned": fails.append("provenance")
in_text("commit in text", commit[:12])
print(f"\n{len(fails)} failure(s)" + (": " + ", ".join(fails) if fails else ""))
sys.exit(1 if fails else 0)
