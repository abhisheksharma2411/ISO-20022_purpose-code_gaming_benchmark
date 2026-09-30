#!/usr/bin/env python3
"""Fill every @@TOKEN@@ in the paper and supplement drafts from
results/summary.json and results/contradiction_test.json. Fails on an
unknown or leftover token and on any qualitative claim that does not hold.

Usage: fill_paper_v3.py <repo> <results-dir> <draft.tex> <out.tex> [<supp-draft.tex> <supp-out.tex>]
"""
import json, math, re, sys
import numpy as np

repo, RES, draft, out = sys.argv[1:5]
sd_in, sd_out = (sys.argv[5], sys.argv[6]) if len(sys.argv) > 6 else (None, None)
S = json.load(open(f"{RES}/summary.json"))
CT = json.load(open(f"{RES}/contradiction_test.json"))
sys.path.insert(0, repo)
import iso20022_gaming_bench as B
D = S["detectors"]; SEL = S["sel"]; L = S["loo"]; SH = S["shift"]; PR = S["prevalence"]
V = S["validity"]; AU = S["artefact_audit"]; G = S["grid"]; ETA = S["eta_sweep"]; ABL = S["ablations"]
prims = B.PRIMITIVES
tok = {}
f3 = lambda x: f"{x:.3f}"; f2 = lambda x: f"{x:.2f}"; pct1 = lambda x: f"{100*x:.1f}"; pct0 = lambda x: f"{100*x:.0f}"
n = S["n_each"]
tok["N"] = f"{n:,}".replace(",", "{,}"); tok["COMMIT"] = S["git_commit"][:12]
assert "dirty" not in S["git_commit"] and S["git_commit"] != "unversioned"
tok["PREV_PCT"] = pct1(S["prevalence_test"]); c1, c01 = S["tpr_ceiling@0.01"], S["tpr_ceiling@0.001"]
tok["CEIL1"], tok["CEIL01"], tok["CEIL1_PCT"] = f3(c1), f3(c01), pct1(c1)
tok["PNAME"], tok["TAU"] = f3(S["config"]["solved_P_NAME"]), f3(S["config"]["solved_TAU"])
tok["ROUTE_PCT"] = pct0(B.CONFIG_A.route_choice_rate)
tok["NGAMED_TEST_RANGE"] = f"{min(S['n_gamed_test']):,}--{max(S['n_gamed_test']):,}".replace(",", "{,}")
for d, e in D.items():
    tok[f"{d}_AUC"], tok[f"{d}_AUCSD"], tok[f"{d}_AP"] = f3(e["auc"]), f3(e["auc_sd"]), f3(e["ap"])
    tok[f"{d}_REC1"], tok[f"{d}_REC1SD"], tok[f"{d}_REC1_PCT"] = f3(e["recovery@0.01"]), f3(e["recovery@0.01_sd"]), pct1(e["recovery@0.01"])
    tok[f"{d}_PREC1"], tok[f"{d}_PREC1_PCT"] = f3(e["precision@0.01"]), pct0(e["precision@0.01"])
    tok[f"{d}_ALERT1"] = f3(e["alert_rate@0.01"]); apd = e["alerts_per_detection@0.01"]
    tok[f"{d}_APD1"] = f"{apd:.1f}" if math.isfinite(apd) else "--"
    tok[f"{d}_REC01"], tok[f"{d}_TOPQ1"] = f3(e["recovery@0.001"]), f3(e["topq_recovery@0.01"])
    tok[f"{d}_AUC_HW"], tok[f"{d}_REC1_HW"] = f3(e["auc_ci95_halfwidth_max"]), f3(e["recovery@0.01_ci95_halfwidth_max"])
    tok[f"{d}_CAP_SHARE_PCT"] = pct0(e["recovery@0.01"] / c1)
lf = ("D1", "D4", "D5", "D7"); shown = ("D1", "D2", "D5", "D6", "D7")
tok["ALERT_DEV"] = f3(max(abs(D[d]["alert_rate@0.01"] - 0.01) for d in shown))
tok["TOPQ_DIFF_MAX"] = f3(max(abs(D[d]["topq_recovery@0.01"] - D[d]["recovery@0.01"]) for d in shown))
tok["MAX_SD_AUC"] = f3(max(D[d]["auc_sd"] for d in shown)); tok["MAX_SD_REC"] = f3(max(D[d]["recovery@0.01_sd"] for d in shown))
tok["REC1_HW_MAX"] = f3(max(D[d]["recovery@0.01_ci95_halfwidth_max"] for d in ("D1", "D2", "D5", "D6", "D7")))
tok["AUC_HW_MAX"] = f3(max(D[d]["auc_ci95_halfwidth_max"] for d in ("D1", "D2", "D5", "D6", "D7")))
# LOO
for fam in ("P1", "P2", "P3"):
    r = L[fam]
    if "D2" not in r:
        for d in B.DETECTORS: tok[f"{fam}_{d}"] = "--"; tok[f"{fam}_{d}IN"] = tok[f"{fam}_{d}OUT"] = "--"
        tok[f"{fam}_N"] = "--"; continue
    tok[f"{fam}_N"] = f"{int(round(r['n_pure']))}"
    for d in B.DETECTORS:
        tok[f"{fam}_{d}"] = f3(r[d]); tok[f"{fam}_{d}IN"] = f3(r[d + "_matched_in"]); tok[f"{fam}_{d}OUT"] = f3(r[d])
        tok[f"{fam}_{d}OUT_SD"] = f3(r.get(d + "_sd", 0.0))
tok["P1_LF_MAX"] = f3(max(L["P1"][d] for d in ("D1", "D4", "D5", "D7"))) if "D1" in L["P1"] else "--"
mech = L["P1"]
tok["MECH_BEN_ABS_PCT"] = pct0(mech.get("benign_share_ultimate_absent", float("nan")))
tok["MECH_P_ABS_PCT"] = pct1(mech.get("train_P_gamed_given_ultimate_absent", float("nan")))
tok["MECH_P_PRES_PCT"] = pct1(mech.get("train_P_gamed_given_ultimate_present", float("nan")))
parts = []
for p in ("P1a", "P1b", "P1c", "P1d"):
    k = f"{p}_heldout_auc_D2"
    if k in mech:
        parts.append(f"{p} {f3(mech[k])} (ultimate absent in {pct0(mech[p + '_ultimate_absent_share'])}\\% of its records)")
        tok[f"MECH_{p.upper()}_AUC"] = f3(mech[k])
tok["MECH_PRIMS"] = ", ".join(parts) if parts else "no primitive had 30 pure test records in every seed"
# SEL
def sel_val(p, key):
    return SEL[p].get(key, float("nan"))
tok["SEL_COORDS"] = " ".join(f"({p},{sel_val(p,'SEL'):.3f})" for p in prims)
tok["SELATT_COORDS"] = " ".join(f"({p},{sel_val(p,'SEL_attempt'):.3f})" for p in prims)
for d in ("D1", "D2", "D5", "D7"):
    tok[f"SELRES_{d}_COORDS"] = " ".join(f"({p},{sel_val(p, f'SEL_res_{d}'):.3f})" for p in prims)
allv = [sel_val(p, k) for p in prims for k in ("SEL", "SEL_attempt", "SEL_res_D1", "SEL_res_D2", "SEL_res_D5", "SEL_res_D7")]
allv = [v for v in allv if math.isfinite(v)]
tok["SEL_YMIN"] = f"{max(0.0, math.floor((min(allv) - 0.05) * 10) / 10):.2f}"; tok["SEL_YMAX"] = f"{max(allv) * 1.22:.2f}"
sels = [sel_val(p, "SEL") for p in prims]
tok["SEL_MIN"], tok["SEL_MAX"] = f2(min(sels)), f2(max(sels))
tok["SEL_PCT_MIN"], tok["SEL_PCT_MAX"] = f"{100*(min(sels)-1):.0f}", f"{100*(max(sels)-1):.0f}"
tok["SEL_ALL"] = f2(SEL["all"]["SEL"]); tok["SEL_ATT_ALL"] = f2(SEL["all"]["SEL_attempt"])
for d in ("D1", "D2", "D5", "D7"):
    tok[f"SEL_RES_ALL_{d}"] = f2(SEL["all"][f"SEL_res_{d}"])
for p in prims:
    P = p.upper()
    tok[f"{P}_SEL"] = f2(sel_val(p, "SEL")); tok[f"{P}_SELATT"] = f2(sel_val(p, "SEL_attempt")); tok[f"{P}_N"] = f"{sel_val(p, 'n_mean'):.0f}"
    for d in ("D1", "D2", "D5", "D7"):
        tok[f"{P}_RES_{d}"] = f2(sel_val(p, f"SEL_res_{d}")); tok[f"{P}_DET_{d}_PCT"] = pct1(sel_val(p, f"detect_rate_{d}"))
tok["SEL_ALL_PCT"] = f"{100*(SEL['all']['SEL']-1):.0f}"
for p in prims:
    P = p.upper(); tok[f"{P}_RESMIN"] = f2(min(sel_val(p, f"SEL_res_{d}") for d in ("D1", "D2", "D5", "D7")))
tok["ATT_DIFF_MAX"] = f2(max(abs(sel_val(p, "SEL") - sel_val(p, "SEL_attempt")) for p in prims if p != "P3b"))
hw = []
for p in prims:
    for c in SEL[p].get("SEL_ci95_per_seed", []):
        if c: hw.append((c[1] - c[0]) / 2)
tok["SEL_HW_MAX"] = f3(max(hw)) if hw else "--"
# contradiction test
for d in ("D2", "D5", "D1", "D7"):
    r = CT["detectors"][d]; c = r["contradiction"]; f = r["family"]
    tok[f"CT_{d}_R2C"], tok[f"CT_{d}_PC"] = f2(c["r2"]), f"{c['p_r2']:.3f}"
    tok[f"CT_{d}_M1"], tok[f"CT_{d}_M0"] = pct1(c["mean_1"]), pct1(c["mean_0"])
    tok[f"CT_{d}_R2F"], tok[f"CT_{d}_PF"] = f2(f["r2"]), f"{f['p_r2']:.3f}"
    tok[f"CT_{d}_RHOCOST"], tok[f"CT_{d}_PCOST"] = f2(r["cost"]["rho"]), f"{r['cost']['p']:.2f}"
    tok[f"CT_{d}_RHOFREQ"], tok[f"CT_{d}_PFREQ"] = f2(r["frequency"]["rho"]), f"{r['frequency']['p']:.2f}"
    tok[f"CT_{d}_LOOC"], tok[f"CT_{d}_LOOF"], tok[f"CT_{d}_LOOB"] = f3(c["loo_mae"]), f3(f["loo_mae"]), f3(r["baseline_loo_mae"])
    tok[f"CT_{d}_R2C_SEEDS"] = f"{r['per_seed_r2_contradiction_mean']:.2f}$\\pm${r['per_seed_r2_contradiction_sd']:.2f}"
# prevalence
for rho, e in PR.items():
    key = rho.replace(".", "_")
    tok[f"PREV_{key}_CEIL"] = f3(e["ceiling@0.01"]); tok[f"PREV_{key}_NG"] = f"{e['n_gamed_test']:.0f}"
    for d in ("D1", "D2", "D5", "D7"):
        tok[f"PREV_{key}_{d}_PREC"] = f3(e[d]["precision@0.01"]); tok[f"PREV_{key}_{d}_REC"] = f3(e[d]["recovery@0.01"])
        tok[f"PREV_{key}_{d}_AP"] = f3(e[d]["ap"]); apd = e[d]["alerts_per_detection@0.01"]
        tok[f"PREV_{key}_{d}_APD"] = f"{apd:.0f}" if math.isfinite(apd) else "--"
# shift
for d in B.DETECTORS:
    for side, tag in (("A_to_B", "AB"), ("B_to_B", "BB")):
        e = SH[d][side]
        tok[f"SH_{d}_{tag}_AUC"], tok[f"SH_{d}_{tag}_REC"], tok[f"SH_{d}_{tag}_PREC"], tok[f"SH_{d}_{tag}_ALERT"] = f3(e["auc"]), f3(e["recovery@0.01"]), f3(e["precision@0.01"]), f3(e["alert_rate@0.01"])
shown = ("D1", "D2", "D5", "D6", "D7")
tok["SH_AUC_GAP_MAX"] = f3(max(abs(SH[d]["A_to_B"]["auc"] - SH[d]["B_to_B"]["auc"]) for d in shown))
for d in B.DETECTORS:
    tok[f"SH_{d}_AB_ALERT_PCT"] = pct1(SH[d]["A_to_B"]["alert_rate@0.01"]); tok[f"SH_{d}_AB_REC_PCT"] = pct1(SH[d]["A_to_B"]["recovery@0.01"])
# validity and audit
tok["XSD_CHECKED"] = f"{V['xsd']['checked']:,}".replace(",", "{,}"); tok["XSD_VALID"] = f"{V['xsd']['valid']:,}".replace(",", "{,}")
tok["XSD_VALID_PCT"] = f"{100*V['xsd']['valid']/max(1,V['xsd']['checked']):.1f}"
tok["INV_VIOL"] = str(V["invariants"]["violations_total"]); tok["INV_CHECKED"] = f"{V['invariants']['gamed_checked']:,}".replace(",", "{,}")
tok["ART_GAMED_PCT"] = pct1(AU["share_gamed_test_out_of_range"]); tok["ART_BEN_PCT"] = pct1(AU["share_benign_test_out_of_range"])
tok["ART_MASS_MAX_PCT"] = pct0(max(AU["alert_mass_on_out_of_range"].values()))
tok["ART_LENS"], tok["ART_MAXSPLIT"], tok["ART_MINNAME"] = str(AU["benign_train_remittance_lengths"]), str(AU["benign_train_max_splits"]), str(AU["benign_train_min_name_len"])
tok["ART_MASS_LIST"] = ", ".join(f"${d}$ {pct1(v)}\\%".replace("$D", "$D_").replace("_", "_{", 1).replace("$ ", "}$ ", 1) if False else f"$D_{d[1]}$ {pct1(v)}\\%" for d, v in AU["alert_mass_on_out_of_range"].items())
# eta drops, grid ranges
etas = sorted(ETA, key=float)
for d in ("D1", "D2", "D5", "D7"):
    tok[f"ETA_{d}_DROP"] = f3(ETA[etas[0]][d]["auc"] - ETA[etas[-1]][d]["auc"])
tok["GRID_SEL_MIN"], tok["GRID_SEL_MAX"] = f2(min(v["SEL_min"] for v in G.values())), f2(max(v["SEL_max"] for v in G.values()))
tok["GRID_D1_MIN"], tok["GRID_D1_MAX"] = f3(min(v["D1_auc"] for v in G.values())), f3(max(v["D1_auc"] for v in G.values()))
# --- supplement table bodies -------------------------------------------------
def esc(s): return str(s).replace("_", "\\_")
A_, B_ = B.CONFIG_A, B.CONFIG_B
rows = []
for fld in ("pairs_per", "pair_concentration", "profile_alpha", "profile_perturb", "industry_weights", "corridor_weights", "path_pref_beta", "batch_rate", "batch_size_range", "batch_tail", "ultimate_beta", "ult_names", "amount_logmean", "amount_pair_sd", "amount_msg_sd", "defect_mix", "rmt_words_max", "rmt_second_ref", "name_len", "route_choice_rate", "listed_ultimate_share"):
    rows.append(f"{esc(fld)} & {esc(getattr(A_, fld))} & {esc(getattr(B_, fld))} \\\\")
tok["TAB_GEN"] = "\n".join(rows)
tok["TAB_COUNTS"] = "; ".join(f"{p} {S['primitive_counts'][p]:.0f} ({S['primitive_counts_test'][p]:.0f})" for p in prims)
tok["TAB_GRID"] = "\n".join(f"{v_key.split(',')[0].split('=')[1]} & {v_key.split(',')[1].split('=')[1]} & {f3(v['P_NAME'])} & {f3(v['TAU'])} & {f3(v['D1_auc'])} & {f3(v['D2_auc'])} & {f3(v['D5_auc'])} & {f2(v['SEL_min'])}--{f2(v['SEL_max'])} \\\\" for v_key, v in G.items())
tok["TAB_MAIN_FULL"] = "\n".join(f"$D_{d[1]}$ & {tok[d+'_AUC']}$\\pm${tok[d+'_AUCSD']} & {tok[d+'_AP']} & {tok[d+'_REC1']}$\\pm${tok[d+'_REC1SD']} & {tok[d+'_PREC1']} & {tok[d+'_ALERT1']} & {tok[d+'_TOPQ1']} & {tok[d+'_REC01']} & {tok[d+'_AUC_HW']} & {tok[d+'_REC1_HW']} \\\\" for d in B.DETECTORS)
tok["TAB_PRIMS"] = "\n".join(f"{p} & {tok[p.upper()+'_N']} & {tok[p.upper()+'_SEL']} & {tok[p.upper()+'_SELATT']} & " + " & ".join(tok[f"{p.upper()}_RES_{d}"] for d in ("D1", "D2", "D5", "D7")) + " & " + " & ".join(tok[f"{p.upper()}_DET_{d}_PCT"] + "\\%" for d in ("D1", "D2", "D5", "D7")) + f" & {pct1(sel_val(p, 'orig_detect_rate_D2'))}\\% \\\\" for p in prims)
tok["TAB_CT"] = "\n".join(f"$D_{d[1]}$ & {tok[f'CT_{d}_R2C']} & {tok[f'CT_{d}_PC']} & {tok[f'CT_{d}_M1']}\\% & {tok[f'CT_{d}_M0']}\\% & {tok[f'CT_{d}_R2F']} & {tok[f'CT_{d}_PF']} & {tok[f'CT_{d}_RHOCOST']} ({tok[f'CT_{d}_PCOST']}) & {tok[f'CT_{d}_RHOFREQ']} ({tok[f'CT_{d}_PFREQ']}) & {tok[f'CT_{d}_LOOC']} & {tok[f'CT_{d}_LOOF']} & {tok[f'CT_{d}_LOOB']} & {tok[f'CT_{d}_R2C_SEEDS']} \\\\" for d in ("D2", "D5", "D1", "D7"))
tok["TAB_ETA"] = "\n".join(f"{float(e):.2f} & " + " & ".join(f3(ETA[e][d]["auc"]) for d in B.DETECTORS) + " \\\\" for e in etas)
tok["TAB_ABL"] = "\n".join(f"{a['factor']} & {esc(a['setting'])} & " + " & ".join(f"{f3(a[d]['auc'])} / {f3(a[d]['recovery@0.01'])}" for d in ("D1", "D2", "D5", "D7")) + " \\\\" for a in ABL)
tok["TAB_PREV"] = "\n".join(f"{float(rho):.3f} & {e['n_gamed_test']:.0f} & {f3(e['ceiling@0.01'])} & " + " & ".join(f"{f3(e[d]['ap'])} / {f3(e[d]['precision@0.01'])} / {e[d]['alerts_per_detection@0.01']:.0f}" for d in ("D1", "D2", "D5", "D7")) + " \\\\" for rho, e in PR.items())
tok["TAB_SHIFT"] = "\n".join(f"$D_{d[1]}$ & {tok[f'SH_{d}_AB_AUC']} & {tok[f'SH_{d}_AB_REC']} & {tok[f'SH_{d}_AB_PREC']} & {tok[f'SH_{d}_AB_ALERT']} & {tok[f'SH_{d}_BB_AUC']} & {tok[f'SH_{d}_BB_REC']} \\\\" for d in B.DETECTORS)
tok["TAB_LOO_FULL"] = "\n".join((f"{fam} & {tok[fam+'_N']} & " + " & ".join(tok[f"{fam}_{d}"] for d in ("D0", "D1", "D3", "D4", "D5", "D7")) + f" & {tok[fam+'_D2IN']}$\\rightarrow${tok[fam+'_D2OUT']} / {tok[fam+'_D6IN']}$\\rightarrow${tok[fam+'_D6OUT']} \\\\") for fam in ("P1", "P2", "P3"))
bp = V["xsd"]["by_primitive"]
tok["TAB_XSD"] = "; ".join(f"{k} {v['valid']}/{v['checked']}" for k, v in bp.items() if v["checked"])

# --- substitute -----------------------------------------------------------------
PROSE = {"RES_A", "RES_B", "RES_B_SHIFT", "RES_C", "RES_D", "DISCUSSION"}   # written by hand after the run
def fill(src, dst):
    text = open(src).read(); used = set(); missing = set()
    def rep(mo):
        key = mo.group(1); used.add(key)
        if key not in tok:
            if key in PROSE:
                missing.add(key); return f"[[pending {key.replace(chr(95), chr(32))}]]"
            raise SystemExit(f"unknown token {key}")
        return tok[key]
    text = re.sub(r"@@([A-Za-z0-9_]+)@@", rep, text)
    assert "@@" not in text, "leftover token"
    if missing: print("  prose tokens still pending:", sorted(missing))
    open(dst, "w").write(text); return len(used)
nu = fill(draft, out); print(f"paper: {nu} tokens -> {out}")
if sd_in:
    ns = fill(sd_in, sd_out); print(f"supplement: {ns} tokens -> {sd_out}")
json.dump(tok, open(out.rsplit(".", 1)[0] + ".tokens.json", "w"), indent=1)

# --- qualitative claims (extended after the full run) ----------------------------
CLAIMS = {
 "XSD 100% valid": V["xsd"]["valid"] == V["xsd"]["checked"] and V["xsd"]["checked"] > 0,
 "no invariant violations": V["invariants"]["violations_total"] == 0,
 "artefact: under 0.5% of benign test records out of the benign training range": AU["share_benign_test_out_of_range"] < 0.005,
 "ceiling consistent with prevalence": abs(c1 - 0.01 / S["prevalence_test"]) < 0.01,
 "D1 precision about one half (0.45-0.55)": 0.45 <= D["D1"]["precision@0.01"] <= 0.55,
 "D5 best label-free AUC": max(lf, key=lambda d: D[d]["auc"]) == "D5",
 "D5 second-best label-free AP": sorted(lf, key=lambda d: -D[d]["ap"])[1] == "D5",
 "D5 lowest label-free recovery": min(lf, key=lambda d: D[d]["recovery@0.01"]) == "D5",
 "D2 best AUC and recovery overall": max(D, key=lambda d: D[d]["auc"]) == "D2" and max(D, key=lambda d: D[d]["recovery@0.01"]) == "D2",
 "D6 recovers less than D2": D["D6"]["recovery@0.01"] < D["D2"]["recovery@0.01"],
 "alert rates within 0.003 of target": float(tok["ALERT_DEV"]) <= 0.003,
 "P2d and P2c residual under D2 below 1": SEL["P2d"]["SEL_res_D2"] < 1 and SEL["P2c"]["SEL_res_D2"] < 1,
 "originals of P2d/P2c alerted under 1% by D2": SEL["P2d"]["orig_detect_rate_D2"] < 0.01 and SEL["P2c"]["orig_detect_rate_D2"] < 0.01,
 "P2d residual under D1 below 1": SEL["P2d"]["SEL_res_D1"] < 1,
 "D7 alerts P3c more than D1": SEL["P3c"]["detect_rate_D7"] > SEL["P3c"]["detect_rate_D1"],
 "P3b attempt-level SEL below 1, per-message above 1": SEL["P3b"]["SEL_attempt"] < 1 < SEL["P3b"]["SEL"],
 "other primitives: per-message and attempt SEL within 0.06": float(tok["ATT_DIFF_MAX"]) <= 0.06,
 "LOO P1: D2 held-out at or below 0.52; label-free max under 0.62": L["P1"]["D2"] <= 0.52 and float(tok["P1_LF_MAX"]) < 0.62,
 "LOO P1 mechanism: gamed rate lower given absent ultimate; P1a/P1d < 0.3 < 0.5 < P1c": mech["train_P_gamed_given_ultimate_absent"] < mech["train_P_gamed_given_ultimate_present"] and mech["P1a_heldout_auc_D2"] < 0.3 and mech["P1d_heldout_auc_D2"] < 0.3 and mech["P1c_heldout_auc_D2"] > 0.5,
 "LOO P2: supervised drop > 0.25; D1 and D5 above 0.8": L["P2"]["D2_drop"] > 0.25 and L["P2"]["D1"] > 0.8 and L["P2"]["D5"] > 0.8,
 "LOO P3: message-level detectors <= 0.56, D2 held-out <= 0.52, D7 >= 0.8": max(L["P3"][d] for d in ("D1", "D4", "D5")) <= 0.56 and L["P3"]["D2"] <= 0.52 and L["P3"]["D7"] >= 0.8,
 "CT: neither contradiction nor family significant for D2 and D5 (p > 0.05)": all(CT["detectors"][d][g]["p_r2"] > 0.05 for d in ("D2", "D5") for g in ("contradiction", "family")),
 "CT: contradiction R2 below 0.1 for D2 and D5": CT["detectors"]["D2"]["contradiction"]["r2"] < 0.1 and CT["detectors"]["D5"]["contradiction"]["r2"] < 0.1,
 "CT: cost rho negative for D2": CT["detectors"]["D2"]["cost"]["rho"] < 0,
 "CT: LOO grouping no better than grand mean for D2": min(CT["detectors"]["D2"]["contradiction"]["loo_mae"], CT["detectors"]["D2"]["family"]["loo_mae"]) >= CT["detectors"]["D2"]["baseline_loo_mae"] - 0.01,
 "P2c second most recovered by D2; P1b under 10%": sorted(prims, key=lambda p: -SEL[p]["detect_rate_D2"])[1] == "P2c" and SEL["P1b"]["detect_rate_D2"] < 0.10,
 "P2 easiest for D1 in LOO; P1 and P3 both under 0.6 for D1": max(("P1", "P2", "P3"), key=lambda f: L[f]["D1"]) == "P2" and L["P1"]["D1"] < 0.6 and L["P3"]["D1"] < 0.6,
 "shift: AUC gap <= 0.03 for shown detectors": float(tok["SH_AUC_GAP_MAX"]) <= 0.03,
 "shift: D2 A-frozen alert rate > 2%": SH["D2"]["A_to_B"]["alert_rate@0.01"] > 0.02,
 "prevalence 0.5%: D1 precision above D2": PR["0.005"]["D1"]["precision@0.01"] > PR["0.005"]["D2"]["precision@0.01"],
 "D5 AUC >= D7 AUC (range statement)": D["D5"]["auc"] >= D["D7"]["auc"],
 "P3a and P3c keep most lift (min residual > 1.3)": float(tok["P3A_RESMIN"]) > 1.3 and float(tok["P3C_RESMIN"]) > 1.3,
}
extra = f"{RES}/../analysis/claims_v3.py" if False else None
bad = [k for k, v in CLAIMS.items() if not v]
for k, v in CLAIMS.items(): print(("OK   " if v else "FAIL ") + k)
if bad: raise SystemExit(f"{len(bad)} claim(s) fail")
