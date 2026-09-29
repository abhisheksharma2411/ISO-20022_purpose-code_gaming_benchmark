#!/usr/bin/env python3
"""Fill every result-derived number in the manuscript from results/summary.json.

Usage: fill_paper.py <draft.tex> <repo> <out.tex>
Every @@TOKEN@@ in the draft is replaced from the summary; the script fails if a
token is unknown, if a token remains, or if a qualitative claim the prose makes
does not hold in the data (see CLAIMS at the bottom).
"""
import json, math, re, sys
import numpy as np

draft, repo, out = sys.argv[1:4]
S = json.load(open(f"{repo}/results/summary.json"))
seeds = S["seeds"]; n = S["n_each"]
D = S["detectors"]; L = S["loo"]; SEL = S["sel"]; SEL5 = S["sel_D5"]
tok = {}

def f3(x): return f"{x:.3f}"
def sd(v): return float(np.std(v, ddof=1))

tok["N"] = f"{n:,}".replace(",", "{,}")
ng = S["n_gamed"]; ni = S["n_illicit"]; nu = S["n_unevaded_illicit"]
tok["GAMED_PCT"] = f"{100*np.mean(ng)/n:.1f}"
tok["NGAMED_RANGE"] = f"{min(ng):,}--{max(ng):,}".replace(",", "{,}")
tok["ILLICIT_GAMED_PCT"] = f"{100*np.mean([g/i for g,i in zip(ng,ni)]):.1f}"
tok["UNEVADED_RANGE"] = f"{min(nu)}--{max(nu)}"
tok["UNEVADED_LIST"] = ", ".join(f"0/{u}" for u in nu)
c1, c01 = S["tpr_ceiling@0.01"], S["tpr_ceiling@0.001"]
tok["CEIL1"], tok["CEIL01"] = f3(c1), f3(c01)
tok["CEIL1_PCT"], tok["CEIL01_PCT"] = f"{100*c1:.1f}", f"{100*c01:.1f}"
tok["PNAME"] = f3(S["config"]["solved_P_NAME"]); tok["TAU"] = f3(S["config"]["solved_TAU"])
tok["COMMIT"] = S["git_commit"][:12]
assert "dirty" not in S["git_commit"] and S["git_commit"] != "unversioned", S["git_commit"]

ceil_seed = [0.01*n/g for g in ng]
for d, e in D.items():
    tok[f"{d}_AUC"] = f3(e["auc"]); tok[f"{d}_AUCSD"] = f3(sd(e["auc_per_seed"]))
    tok[f"{d}_AP"] = f3(e["ap"])
    tok[f"{d}_T1"] = f3(e["tpr@0.01"]); tok[f"{d}_T1SD"] = f3(sd(e["tpr@0.01_per_seed"]))
    tok[f"{d}_T01"] = f3(e["tpr@0.001"])
    tok[f"{d}_T1_PCT"] = f"{100*e['tpr@0.01']:.1f}"; tok[f"{d}_T01_PCT"] = f"{100*e['tpr@0.001']:.1f}"
    prec = [t/c for t, c in zip(e["tpr@0.01_per_seed"], ceil_seed)]
    tok[f"{d}_P1"] = f3(np.mean(prec)); tok[f"{d}_P1_PCT"] = f"{100*np.mean(prec):.0f}"
    hw = max((hi-lo)/2 for lo, hi in e["auc_ci95_per_seed"])
    tok[f"{d}_AUC_HW"] = f3(hw)
    hw1 = max((hi-lo)/2 for lo, hi in e["tpr@0.01_ci95_per_seed"])
    tok[f"{d}_T1_HW_PCT"] = f"{100*hw1:.1f}"
    tok[f"{d}_BEN1"] = f"{e['benign_alerts_per_M@0.01']:.0f}"
    tok[f"{d}_CAP_SHARE_PCT"] = f"{100*e['tpr@0.01']/c1:.0f}"

for fam in ("P1", "P2", "P3"):
    r = L[fam]
    tok[f"{fam}_N"] = f"{int(round(r['n_pure']))}"
    for d in ("D1", "D4", "D5"):
        tok[f"{fam}_{d}"] = f3(r[d])
    for d in ("D2", "D6"):
        tok[f"{fam}_{d}IN"] = f3(r[d + "_matched_in"]); tok[f"{fam}_{d}OUT"] = f3(r[d])
        outs = [o for _, o in r[d + "_per_seed"]]; ins = [i for i, _ in r[d + "_per_seed"]]
        tok[f"{fam}_{d}OUT_RANGE"] = f"{min(outs):.3f}--{max(outs):.3f}"
        tok[f"{fam}_{d}IN_RANGE"] = f"{min(ins):.3f}--{max(ins):.3f}"

etas = sorted(S["eta_sweep"], key=float)
for d in ("D1", "D3", "D4", "D5"):
    tok[f"ETA_{d}"] = " ".join(f"({float(e):.2f},{S['eta_sweep'][e][d]:.4f})" for e in etas)
    tok[f"ETA_{d}_DROP"] = f3(S["eta_sweep"][etas[0]][d] - S["eta_sweep"][etas[-1]][d])
allv = [S["eta_sweep"][e][d] for e in etas for d in ("D1", "D3", "D4", "D5")]
tok["ETA_YMIN"] = f"{math.floor((min(allv)-0.01)*20)/20:.2f}"; tok["ETA_YMAX"] = f"{math.ceil((max(allv)+0.01)*20)/20:.2f}"
tok["ETA_LO"], tok["ETA_HI"] = f"{float(etas[0]):.2f}", f"{float(etas[-1]):.2f}"

prims = [p for p in ("P1a","P1b","P1c","P1d","P2a","P2b","P2c","P2d","P3a","P3b","P3c") if p in SEL]
assert len(prims) == 11, prims
tok["SEL_COORDS"] = " ".join(f"({p},{SEL[p]['SEL']:.3f})" for p in prims)
tok["SELRES4_COORDS"] = " ".join(f"({p},{SEL[p]['SEL_res']:.3f})" for p in prims)
tok["SELRES5_COORDS"] = " ".join(f"({p},{SEL5[p]['SEL_res']:.3f})" for p in prims)
sels = [SEL[p]["SEL"] for p in prims]; res4 = [SEL[p]["SEL_res"] for p in prims]; res5 = [SEL5[p]["SEL_res"] for p in prims]
tok["SEL_MIN"], tok["SEL_MAX"] = f"{min(sels):.2f}", f"{max(sels):.2f}"
tok["SEL_PCT_MIN"], tok["SEL_PCT_MAX"] = f"{100*(min(sels)-1):.0f}", f"{100*(max(sels)-1):.0f}"
tok["SEL_YMIN"] = f"{math.floor(min(res4+res5+[1.0])*20)/20-0.05:.2f}"; tok["SEL_YMAX"] = f"{max(sels)*1.08:.2f}"
tok["SEL_HW_MAX"] = f3(max((hi-lo)/2 for p in prims for lo, hi in SEL[p]["SEL_ci_per_seed"]))
tok["SELRES_HW_MAX"] = f3(max((hi-lo)/2 for p in prims for lo, hi in SEL[p]["SEL_res_ci_per_seed"]))
for p in prims:
    tok[f"{p.upper()}_SEL"] = f3(SEL[p]["SEL"]); tok[f"{p.upper()}_RES4"] = f3(SEL[p]["SEL_res"]); tok[f"{p.upper()}_RES5"] = f3(SEL5[p]["SEL_res"])
    tok[f"{p.upper()}_DET4_PCT"] = f"{100*SEL[p]['detect_rate']:.1f}"; tok[f"{p.upper()}_DET5_PCT"] = f"{100*SEL5[p]['detect_rate']:.1f}"
tok["P2D_CI_LIST"] = ", ".join(f"{lo:.3f}--{hi:.3f}" for lo, hi in SEL["P2d"]["SEL_res_ci_per_seed"])
tok["P2D_CI5_LIST"] = ", ".join(f"{lo:.3f}--{hi:.3f}" for lo, hi in SEL5["P2d"]["SEL_res_ci_per_seed"])
p2abc4 = [SEL[p]["detect_rate"] for p in ("P2a","P2b","P2c")]; p2abc5 = [SEL5[p]["detect_rate"] for p in ("P2a","P2b","P2c")]
tok["P2ABC_DET4_MIN"], tok["P2ABC_DET4_MAX"] = f"{100*min(p2abc4):.1f}", f"{100*max(p2abc4):.1f}"
tok["P2ABC_DET5_MIN"], tok["P2ABC_DET5_MAX"] = f"{100*min(p2abc5):.1f}", f"{100*max(p2abc5):.1f}"
# Conservative sensitivity: replace an observed delta0 of zero by the exact
# Clopper-Pearson two-sided 95% upper bound for 0/n and rescale the P2d
# residual-SEL upper endpoints.
d0 = S["delta0"]
if all(x == 0.0 for x in d0):
    ub = [1 - 0.025 ** (1.0 / u) for u in nu]
    adj4 = max(hi / (1 - b) for (lo, hi), b in zip(SEL["P2d"]["SEL_res_ci_per_seed"], ub))
    tok["P2D_CP_UPPER4"] = f3(adj4); tok["P2D_HI4"] = f3(max(hi for lo, hi in SEL["P2d"]["SEL_res_ci_per_seed"]))
    tok["DELTA0_ZERO"] = "yes"
else:
    tok["DELTA0_ZERO"] = "no"
    tok["P2D_CP_UPPER4"] = "n/a"; tok["P2D_HI4"] = "n/a"

# D5 residual-SEL baseline and the same conservative sensitivity check
import glob as _glob
_mains = [json.load(open(x)) for x in sorted(_glob.glob(f"{repo}/results/phase1_main_seed*.json"))]
d05 = [m["sel_D5"]["_baseline"]["delta0"] for m in _mains]
tok["DELTA0_D5_LIST"] = ", ".join(f"{x:.3f}" for x in d05)
if all(x == 0.0 for x in d05):
    ub = [1 - 0.025 ** (1.0 / u) for u in nu]
    adj5 = max(hi / (1 - b) for (lo, hi), b in zip(SEL5["P2d"]["SEL_res_ci_per_seed"], ub))
    tok["P2D_CP_UPPER5"] = f3(adj5)
else:
    tok["P2D_CP_UPPER5"] = "n/a"
tok["P2D_HI5"] = f3(max(hi for lo, hi in SEL5["P2d"]["SEL_res_ci_per_seed"]))
tok["P2D_HI4"] = f3(max(hi for lo, hi in SEL["P2d"]["SEL_res_ci_per_seed"]))
tok["CP_UB_MAX_PCT"] = f"{100*max(1 - 0.025 ** (1.0 / u) for u in nu):.1f}"

# diagnostics (seed 7): artefact audit and P1 inversion mechanism
DG = json.load(open(f"{repo}/results/diagnostics_seed7.json"))
A = DG["artefact_audit"]; M = DG["p1_inversion"]
tok["ART_GAMED_PCT"] = f"{100*A['share_gamed_out_of_range']:.1f}"
tok["ART_BENIGN_PCT"] = f"{100*A['share_benign_out_of_range']:.1f}"
for d, v in A["alert_mass_on_out_of_range"].items():
    tok[f"ART_MASS_{d}_PCT"] = f"{100*v:.0f}"
tok["RULE_AUC"] = f3(A["out_of_range_rule"]["auc"]); tok["RULE_REC1_PCT"] = f"{100*A['out_of_range_rule']['rec@0.01']:.1f}"
tok["INR_NGAMED"] = f"{A['in_range_subset']['n_gamed']:,}".replace(",", "{,}")
for d, v in A["in_range_subset"]["auc"].items():
    tok[f"INR_{d}_AUC"] = f3(v)
for d, v in A["in_range_subset"]["rec@0.01"].items():
    tok[f"INR_{d}_REC1_PCT"] = f"{100*v:.1f}"
tok["MECH_HELDOUT_AUC"] = f3(M["heldout_P1_auc_D2"])
tok["MECH_P_ABS_PCT"] = f"{100*M['train_P_gamed_given_ultimate_absent']:.1f}"
tok["MECH_P_PRES_PCT"] = f"{100*M['train_P_gamed_given_ultimate_present']:.1f}"
tok["MECH_BEN_ABS_PCT"] = f"{100*M['benign_share_ultimate_absent']:.0f}"
for prim in ("P1a", "P1c", "P1d"):
    pp = M["per_primitive"][prim]
    tok[f"MECH_{prim.upper()}_AUC"] = f3(pp["heldout_auc_vs_benign_D2"]) if "heldout_auc_vs_benign_D2" in pp else "n/a"
    tok[f"MECH_{prim.upper()}_ABS_PCT"] = f"{100*pp['ultimate_absent_share']:.0f}" if "ultimate_absent_share" in pp else "n/a"
tok["MECH_N"] = f"{M['n']:,}".replace(",", "{,}")

tok["NGAMED_MEAN"] = f"{int(round(np.mean(ng), -1)):,}".replace(",", "{,}")
tok["MAX_SD_AUC"] = f3(max(sd(D[d]["auc_per_seed"]) for d in D))
tok["MAX_SD_T1"] = f3(max(sd(D[d]["tpr@0.01_per_seed"]) for d in D))
tok["MAX_AUC_HW"] = f3(max(float(tok[f"{d}_AUC_HW"]) for d in D))
best_lf_t1 = max(D[d]["tpr@0.01"] for d in ("D0", "D1", "D3", "D4", "D5"))
tok["D6_MINUS_D1_PP"] = f"{100*(D['D6']['tpr@0.01'] - best_lf_t1):.1f}"
tok["D2_MINUS_D6_PP"] = f"{100*(D['D2']['tpr@0.01'] - D['D6']['tpr@0.01']):.1f}"
tok["ART_MASS_MAX_PCT"] = f"{100*max(A['alert_mass_on_out_of_range'].values()):.0f}"
d5e = [S["eta_sweep"][e]["D5"] for e in etas]
tok["ETA_D5_ABSDROP"] = f3(max(d5e) - min(d5e))
tok["DELTA0_COUNTS"] = ", ".join(f"{int(round(x*u))}/{u}" for x, u in zip(d0, nu))
from math import comb
def cp_upper(k, nn, alpha=0.025):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        p = (lo + hi) / 2
        cdf = sum(comb(nn, i) * p**i * (1-p)**(nn-i) for i in range(k+1))
        lo, hi = (p, hi) if cdf > alpha else (lo, p)
    return (lo + hi) / 2
infl = max(1/(1-cp_upper(int(round(x*u)), u)) / (1/(1-x)) - 1 for x, u in zip(d0, nu))
tok["RES_INFLATION_MAX_PCT"] = f"{100*infl:.0f}"
tok["MECH_P1C_PRES_PCT"] = f"{100*(1-M['per_primitive']['P1c']['ultimate_absent_share']):.0f}"
tok["MECH_P1B_N"] = str(M["per_primitive"]["P1b"]["n"])

g = S["grid"]
tok["GRID_SEL_MIN"] = f"{min(v['SEL_min'] for v in g.values()):.2f}"; tok["GRID_SEL_MAX"] = f"{max(v['SEL_max'] for v in g.values()):.2f}"
tok["GRID_D4_MIN"] = f3(min(v["D4_auc"] for v in g.values())); tok["GRID_D4_MAX"] = f3(max(v["D4_auc"] for v in g.values()))

abl = {a["setting"]: a for a in S["ablations"]}
m = {"P1": "P1 only", "P2": "P2 only", "P3": "P3 only", "K1": "$k=1$", "K2": "$k=2$", "K3": "$k=3$", "B": "black-box", "G": "grey-box"}
for k, setting in m.items():
    tok[f"ABL_{k}_4"] = f3(abl[setting]["D4_auc"]); tok[f"ABL_{k}_5"] = f3(abl[setting]["D5_auc"])

text = open(draft).read()
used = set()
def rep(mo):
    key = mo.group(1); used.add(key)
    if key not in tok: raise SystemExit(f"unknown token {key}")
    return tok[key]
text = re.sub(r"@@([A-Za-z0-9_]+)@@", rep, text)
assert "@@" not in text
open(out, "w").write(text)
json.dump(tok, open(out.rsplit(".",1)[0] + ".tokens.json", "w"), indent=1)

# ---- qualitative claims the prose makes; fail loudly if the data disagree ---
labelfree = ["D0", "D1", "D3", "D4", "D5"]
CLAIMS = {
 "D5 is the best label-free detector by AUC": max(labelfree, key=lambda d: D[d]["auc"]) == "D5",
 "label-free AUC order D5>D4>D1": D["D5"]["auc"] > D["D4"]["auc"] > D["D1"]["auc"],
 "label-free recovery order D1>D4>D5 (reverse)": D["D1"]["tpr@0.01"] > D["D4"]["tpr@0.01"] > D["D5"]["tpr@0.01"],
 "D1 recovers about half the ceiling (0.45-0.55)": 0.45 < D["D1"]["tpr@0.01"]/c1 < 0.55,
 "D1 fills the 0.1% capacity with gamed records (zero benign alerts)": D["D1"]["benign_alerts_per_M@0.001"] == 0 and abs(D["D1"]["tpr@0.001"] - c01) < 0.0005,
 "D1 has the best label-free average precision": max(labelfree, key=lambda d: D[d]["ap"]) == "D1",
 "D2 has the best AUC overall": max(D, key=lambda d: D[d]["auc"]) == "D2",
 "D2 does not saturate the 1% capacity": c1 - D["D2"]["tpr@0.01"] > 0.01,
 "D5 beats D3 on AUC, AP and both recoveries": all(D["D5"][m] > D["D3"][m] for m in ("auc", "ap", "tpr@0.01", "tpr@0.001")),
 "D5 recovers less than D4 at 1%": D["D5"]["tpr@0.01"] < D["D4"]["tpr@0.01"],
 "D6 recovers more than the best label-free": D["D6"]["tpr@0.01"] > best_lf_t1,
 "D2 recovers more than D6": D["D2"]["tpr@0.01"] > D["D6"]["tpr@0.01"],
 "boosting adds at least as much as labels (D2-D6 >= D6-bestLF)": (D["D2"]["tpr@0.01"] - D["D6"]["tpr@0.01"]) >= (D["D6"]["tpr@0.01"] - best_lf_t1),
 "differences discussed exceed uncertainty": (D["D5"]["auc"]-D["D4"]["auc"] > float(tok["MAX_AUC_HW"])) and (D["D4"]["auc"]-D["D1"]["auc"] > float(tok["MAX_AUC_HW"])) and (D["D4"]["tpr@0.01"]-D["D5"]["tpr@0.01"] > 2*float(tok["MAX_SD_T1"])),
 "artefact audit: <2% of gamed out of range, 0 benign, <=6% alert mass": A["share_gamed_out_of_range"] < 0.02 and A["share_benign_out_of_range"] == 0 and max(A["alert_mass_on_out_of_range"].values()) <= 0.06,
 "P1 held-out D2 AUC below 0.5": L["P1"]["D2"] < 0.5,
 "P1 D2 drop is the largest family drop": L["P1"]["D2_drop"] == max(L[f]["D2_drop"] for f in L),
 "P2 drop smaller than P1 drop": L["P2"]["D2_drop"] < L["P1"]["D2_drop"],
 "P3 label-free AUCs near chance (D1,D4 < 0.55)": L["P3"]["D1"] < 0.55 and L["P3"]["D4"] < 0.55,
 "P2 is D1's easiest family": max(L, key=lambda f: L[f]["D1"]) == "P2",
 "mechanism: gamed rate lower given absent ultimate debtor": M["train_P_gamed_given_ultimate_absent"] < M["train_P_gamed_given_ultimate_present"],
 "mechanism: P1a and P1d AUC < 0.35, P1c > 0.5": M["per_primitive"]["P1a"]["heldout_auc_vs_benign_D2"] < 0.35 and M["per_primitive"]["P1d"]["heldout_auc_vs_benign_D2"] < 0.35 and M["per_primitive"]["P1c"]["heldout_auc_vs_benign_D2"] > 0.5,
 "mechanism: P1a and P1d always remove the ultimate debtor": M["per_primitive"]["P1a"]["ultimate_absent_share"] == 1.0 and M["per_primitive"]["P1d"]["ultimate_absent_share"] == 1.0,
 "P1b rarely selected alone (<30)": M["per_primitive"]["P1b"]["n"] < 30,
 "P2d residual SEL under D4 above 1 but below SEL": 1.0 < SEL["P2d"]["SEL_res"] < SEL["P2d"]["SEL"],
 "P2d most alerted under D4": max(prims, key=lambda p: SEL[p]["detect_rate"]) == "P2d",
 "D5 P2d detection under 10%": SEL5["P2d"]["detect_rate"] < 0.10,
 "P2c detected more by D5 than D4": SEL5["P2c"]["detect_rate"] > SEL["P2c"]["detect_rate"],
 "P3b has the largest SEL": max(prims, key=lambda p: SEL[p]["SEL"]) == "P3b",
 "P3b residual within 0.1 of SEL under both": SEL["P3b"]["SEL"]-SEL["P3b"]["SEL_res"] < 0.1 and SEL["P3b"]["SEL"]-SEL5["P3b"]["SEL_res"] < 0.1,
 "P3c D4 detection rate below 2%": SEL["P3c"]["detect_rate"] < 0.02,
 "D1 most stable under eta among D1/D3/D4; D3 fastest": min(("D1","D3","D4"), key=lambda d: float(tok[f"ETA_{d}_DROP"])) == "D1" and max(("D1","D3","D4"), key=lambda d: float(tok[f"ETA_{d}_DROP"])) == "D3",
 "D5 flat under eta (range < 0.02)": float(tok["ETA_D5_ABSDROP"]) < 0.02,
 "all detectors above chance at highest eta": min(S["eta_sweep"][etas[-1]][d] for d in ("D1","D3","D4","D5")) > 0.5,
 "delta0 near zero (<=0.02) every seed": max(d0) <= 0.02,
 "k ablation monotone for D4": abl["$k=1$"]["D4_auc"] < abl["$k=2$"]["D4_auc"] < abl["$k=3$"]["D4_auc"],
 "grey-box easier than black-box for D4": abl["grey-box"]["D4_auc"] > abl["black-box"]["D4_auc"],
 "P3-only lowest for D4; P1-only lowest for D5; D5 weakest LOO family is P1": min(("P1 only","P2 only","P3 only"), key=lambda s_: abl[s_]["D4_auc"]) == "P3 only" and min(("P1 only","P2 only","P3 only"), key=lambda s_: abl[s_]["D5_auc"]) == "P1 only" and min(L, key=lambda fam: L[fam]["D5"]) == "P1",
 "D5 weaker on P1, stronger on P2 and P3 than D4": abl["P1 only"]["D5_auc"] < abl["P1 only"]["D4_auc"] and abl["P2 only"]["D5_auc"] > abl["P2 only"]["D4_auc"] and abl["P3 only"]["D5_auc"] > abl["P3 only"]["D4_auc"],
}
bad = [k for k, v in CLAIMS.items() if not v]
print(f"filled {len(used)} tokens -> {out}")
for k, v in CLAIMS.items(): print(("OK   " if v else "FAIL ") + k)
if bad: raise SystemExit(f"{len(bad)} claim(s) do not hold; fix the prose before building")
