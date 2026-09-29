#!/usr/bin/env python3
"""
run_protocol.py -- executes the full evaluation protocol from Section V of
"Detecting Purpose-Code Gaming in ISO 20022 Payments" and writes LaTeX
fragments that drop straight into the paper.

Phases
  0  calibration sweep       pi_0 in {0.30, 0.45, 0.60}
  1  main run x 3 seeds      -> detector table and SEL figure
  2  leave-one-family-out    -> held-out-family table (k=1)
  3  eta sweep               -> noise-sensitivity figure
  4  ablations               -> family/budget/knowledge checks
  5  XML corpus + optional XSD validation

Outputs
  results/*.json            raw results, one file per run, config-hashed
  latex/fig_roc.tex         pgfplots axis, paste over Fig. 4
  latex/fig_sel.tex         pgfplots axis, paste over Fig. 5
  latex/fig_eta.tex         pgfplots axis, new figure
  latex/table1.tex          main detector table body
  latex/table_loo.tex       held-out-family table body
  latex/table2.tex          ablation table body
  latex/SUMMARY.md          what to change in the .tex, in order

Usage
  python run_protocol.py --quick          # ~3 min, sanity check
  python run_protocol.py --full           # paper run; takes a while
  python run_protocol.py --full --xsd-dir ./xsd
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

import numpy as np

import iso20022_gaming_bench as B

OUT = "results"
TEX = "latex"
DET_LABEL = {
    "D0": r"$D_0$ C1--C2 checks",
    "D1": r"$D_1$ fixed rules",
    "D2": r"$D_2$ supervised GBM",
    "D3": r"$D_3$ isolation forest",
    "D4": r"$D_4$ combined",
    "D5": r"$D_5$ LOF",
    "D6": r"$D_6$ logistic",
}
NEEDS_LABELS = {"D0": "no", "D1": "no", "D2": "yes", "D3": "no", "D4": "no",
                "D5": "no", "D6": "yes"}
DETS = tuple(DET_LABEL)
GIT_SHA = "unversioned"


def _git_sha():
    """Commit of the tree that produced this run, with -dirty when tracked
    files differ from HEAD. Captured once at start-up, before the run writes
    its own result files."""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here,
                                      text=True).strip()
        st = subprocess.run(["git", "status", "--porcelain",
                             "--untracked-files=no"], cwd=here,
                            capture_output=True, text=True).stdout.strip()
        return sha + ("-dirty" if st else "")
    except Exception:
        return "unversioned"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def save(tag, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{tag}.json")
    with open(p, "w") as f:
        json.dump(obj, f, indent=2)
    return p


def run_one(n, eta, rho, seed, k, lam, temp, knowledge, pi_floor,
            target_pi0, boot, loo=False, name_share=0.6, extra=True):
    B.PI_FLOOR = pi_floor
    B.TEMP = temp
    B.P_NAME, B.TAU = 0.90, 0.55          # reset before each calibration
    if target_pi0 is not None:
        B.calibrate_p_name(target_pi0, eta, seed, knowledge,
                           name_share=name_share,
                           n_probe=min(4000, max(500, n)))
    msgs = B.generate(n, eta, rho, seed, k, lam, knowledge)
    res = B.evaluate(msgs, seed=seed, boot=boot, extra=extra)
    if loo:
        res["loo"] = B.evaluate_loo(msgs, seed=seed, extra=extra)
    res["config"] = dict(n=n, eta=eta, rho=rho, seed=seed, k=k, lam=lam,
                         temp=temp, knowledge=knowledge, pi_floor=pi_floor,
                         target_pi0=target_pi0, name_share=name_share,
                         solved_P_NAME=B.P_NAME, solved_TAU=B.TAU,
                         git_commit=GIT_SHA, cross_fit="2-fold by row parity",
                         c5_history="other fold only, no labels",
                         d4_standardisation="other-fold statistics")
    return res, msgs


# ---------------------------------------------------------------------------
def emit_table1(mains, path):
    """Main detector table: mean AUC and exact-capacity TPR over seeds."""
    rows = []
    for d in DETS:
        if d not in mains[0]["detectors"]:
            continue
        auc = np.array([r["detectors"][d]["auc"] for r in mains])
        t1 = np.array([r["detectors"][d]["tpr@0.01"] for r in mains])
        t01 = np.array([r["detectors"][d]["tpr@0.001"] for r in mains])
        rows.append(
            f"{DET_LABEL[d]} & {NEEDS_LABELS[d]} & "
            f"{auc.mean():.3f} ({auc.min():.3f}--{auc.max():.3f}) & "
            f"{t1.mean():.3f} ({t1.min():.3f}--{t1.max():.3f}) & "
            f"{t01.mean():.3f} " + r" \\")
    c1 = np.mean([r["tpr_ceiling@0.01"] for r in mains])
    c01 = np.mean([r["tpr_ceiling@0.001"] for r in mains])
    rows.append(f"Capacity ceiling & -- & -- & {c1:.3f} & {c01:.3f} " + r" \\")
    body = "\n".join(rows)
    seeds = ", ".join(str(r["config"]["seed"]) for r in mains)
    note = (f"% mean (min--max) over seeds {seeds}; n={mains[0]['config']['n']}, "
            f"eta={mains[0]['config']['eta']}; TPR uses exact expected "
            "capacity with label-blind tie-breaking; learned detectors are "
            "2-fold cross-fitted\n")
    open(path, "w").write(note + body + "\n")
    return body

def emit_table_loo(loo_res, path):
    """Per-family leave-one-out against a MATCHED in-distribution baseline.

    Only D2 trains on gaming labels, so only D2 can have a holdout gap. The
    zero drop for D1/D3/D4 is a property of the design, not a measurement --
    say so in the caption rather than presenting it as a result.
    """
    rows = []
    for fam, name in (("P1", "P1 misfielding"), ("P2", "P2 code sub."),
                      ("P3", "P3 structure")):
        r = loo_res.get(fam)
        if not isinstance(r, dict) or "D4" not in r:
            rows.append(f"{name} & -- & -- & -- & -- \\\\")
            continue
        rows.append(
            f"{name} & {int(round(r['n_pure']))} & "
            f"{r['D1']:.3f} & "
            f"{r['D2_matched_in']:.3f}\\,$\\rightarrow$\\,{r['D2']:.3f} & "
            f"{r['D4']:.3f} \\\\")
    body = "\n".join(rows)
    open(path, "w").write(
        "% cols: family | n (pure) | D1 | D2 in->held-out | D4\n"
        "% D1/D3/D4 use no gaming labels, so held-out == in-distribution\n"
        "% by construction. Only D2 has a real holdout gap.\n" + body + "\n")
    return body


def emit_table2(abl, path):
    rows = []
    for label, setting, r in abl:
        auc = r["detectors"]["D4"]["auc"]
        sels = [v["SEL_res"] for k, v in r["sel"].items()
                if not k.startswith("_")]
        sr = np.mean(sels) if sels else float("nan")
        rows.append(f"{label} & {setting} & {auc:.3f} & "
                    + ("--" if np.isnan(sr) else f"{sr:.2f}") + r" \\")
    body = "\n".join(rows)
    open(path, "w").write(body + "\n")
    return body


def emit_fig_roc(main, path):
    styles = {"D1": "dashed", "D2": "dotted", "D3": "solid",
              "D4": "solid,line width=1.1pt"}
    plots = []
    for d in ("D1", "D2", "D3", "D4"):
        pts = " ".join(f"({x:.5f},{y:.4f})" for x, y in main["roc"][d]
                       if x >= 5e-4)
        plots.append(f"\\addplot[{styles[d]}] coordinates {{{pts}}};\n"
                     f"\\addlegendentry{{{DET_LABEL[d]}}}")
    body = r"""\begin{tikzpicture}
\begin{semilogxaxis}[
  width=0.92\columnwidth, height=4.5cm,
  xlabel={False positive rate (log)}, ylabel={True positive rate},
  xmin=0.0005, xmax=1, ymin=0, ymax=1,
  grid=both, grid style={black!12},
  legend style={at={(0.98,0.03)},anchor=south east,font=\tiny,
                draw=black!30,row sep=-1.5pt},
  label style={font=\scriptsize}, tick label style={font=\tiny},
  every axis plot/.append style={line width=0.7pt}
]
""" + "\n".join(plots) + r"""
\end{semilogxaxis}
\end{tikzpicture}"""
    open(path, "w").write(body + "\n")
    return body


def emit_fig_sel(mains, path):
    """SEL bars as three-seed means, matching the paper figure."""
    prims = [p for p in B.PRIMITIVES if all(p in r["sel"] for r in mains)]
    if not prims:
        open(path, "w").write("% no primitive reached the n>=30 threshold\n")
        return ""
    mean_sel = {p: float(np.mean([r["sel"][p]["SEL"] for r in mains]))
                for p in prims}
    mean_res = {p: float(np.mean([r["sel"][p]["SEL_res"] for r in mains]))
                for p in prims}
    coords = " ".join(f"({p},{mean_sel[p]:.3f})" for p in prims)
    coords_r = " ".join(f"({p},{mean_res[p]:.3f})" for p in prims)
    lo = min(min(mean_res.values()), 1.0)
    hi = max(mean_sel.values())
    body = (r"""\begin{tikzpicture}
\begin{axis}[
  width=0.94\columnwidth, height=4.1cm,
  ybar=1.2pt, bar width=5pt,
  ylabel={SEL},
  symbolic x coords={""" + ",".join(prims) + r"""},
  xtick=data, ymin=""" + f"{max(0.75, lo*0.95):.2f}" + r""", ymax="""
        + f"{hi*1.08:.2f}" + r""",
  grid=both, grid style={black!12},
  legend style={at={(0.02,0.97)},anchor=north west,font=\tiny,
                draw=black!30,legend columns=2},
  label style={font=\scriptsize}, tick label style={font=\tiny}
]
\addplot[fill=black!25] coordinates {""" + coords + r"""};
\addlegendentry{$\mathrm{SEL}$}
\addplot[fill=black!60] coordinates {""" + coords_r + r"""};
\addlegendentry{$\mathrm{SEL}_{\mathrm{res}}$ with $D_4$}
\end{axis}
\end{tikzpicture}""")
    open(path, "w").write(body + "\n")
    return body

def emit_fig_eta(sweep, path):
    plots = []
    styles = {"D1": "dashed", "D3": "solid", "D4": "solid,line width=1.1pt",
              "D5": "dotted,line width=1.0pt"}
    for d in ("D1", "D3", "D4", "D5"):
        if d not in sweep[0][1]["detectors"]:
            continue
        pts = " ".join(f"({eta:.3f},{r['detectors'][d]['auc']:.4f})"
                       for eta, r in sweep)
        plots.append(f"\\addplot[{styles[d]},mark=*,mark size=1pt] "
                     f"coordinates {{{pts}}};\n"
                     f"\\addlegendentry{{{DET_LABEL[d]}}}")
    body = r"""\begin{tikzpicture}
\begin{axis}[
  width=0.92\columnwidth, height=4.1cm,
  xlabel={Accidental-defect rate $\eta$}, ylabel={AUC (gaming detection)},
  ymin=0.5, ymax=1.0, grid=both, grid style={black!12},
  legend style={at={(0.98,0.97)},anchor=north east,font=\tiny,draw=black!30},
  label style={font=\scriptsize}, tick label style={font=\tiny}
]
""" + "\n".join(plots) + r"""
\end{axis}
\end{tikzpicture}"""
    open(path, "w").write(body + "\n")
    return body


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small sanity run")
    ap.add_argument("--full", action="store_true", help="paper run")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--rho", type=float, default=0.05)
    ap.add_argument("--eta", type=float, default=0.15)
    ap.add_argument("--lam", type=float, default=0.18)
    ap.add_argument("--temp", type=float, default=0.10)
    ap.add_argument("--pi-floor", type=float, default=0.10)
    ap.add_argument("--pi0", type=float, default=0.45)
    ap.add_argument("--name-share", type=float, default=0.6,
                    help="fraction of baseline detection from the name leg. "
                         "Below ~0.4 the evader stops selecting P1. Sweep it.")
    ap.add_argument("--k", type=int, default=2, help="evader budget")
    ap.add_argument("--seeds", type=int, nargs="+", default=[7, 8, 9])
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--xsd-dir", default=None)
    ap.add_argument("--emit-xml", type=int, default=2000)
    ap.add_argument("--out", default="results", help="results directory")
    ap.add_argument("--tex", default="latex", help="LaTeX fragment directory")
    a = ap.parse_args()
    global OUT, TEX, GIT_SHA
    OUT, TEX = a.out, a.tex
    GIT_SHA = _git_sha()
    log(f"git commit: {GIT_SHA}")

    n = a.n or (6000 if a.quick else 200_000)
    if a.quick:
        a.seeds = a.seeds[:2]
        a.boot = min(a.boot, 40)
    os.makedirs(TEX, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()

    # -- phase 0: calibration sweep -----------------------------------------
    log("phase 0: calibration sweep")
    calib = {}
    for tgt in (0.30, 0.45, 0.60):
        r, _ = run_one(n // 4, a.eta, a.rho, a.seeds[0], 2, a.lam, a.temp,
                       "grey", a.pi_floor, tgt, boot=100,
                       name_share=a.name_share)
        sels = {k: v["SEL"] for k, v in r["sel"].items() if not k.startswith("_")}
        calib[str(tgt)] = {"P_NAME": r["config"]["solved_P_NAME"],
                           "TAU": r["config"]["solved_TAU"],
                           "SEL_mean": float(np.mean(list(sels.values())))
                           if sels else None,
                           "SEL_by_primitive": sels}
        log(f"  pi_0={tgt}: mean SEL={calib[str(tgt)]['SEL_mean']}")
    save("phase0_calibration", calib)

    # -- phase 1: main runs -----------------------------------------------
    log(f"phase 1: main runs, n={n}, seeds={a.seeds}")
    mains, last_msgs = [], None
    for seed in a.seeds:
        r, msgs = run_one(n, a.eta, a.rho, seed, a.k, a.lam, a.temp, "grey",
                          a.pi_floor, a.pi0, a.boot, loo=False,
                          name_share=a.name_share)
        mains.append(r)
        last_msgs = msgs
        log(f"  seed {seed}: D4 AUC={r['detectors']['D4']['auc']:.3f} "
            f"gamed={r['n_gamed']}")
        save(f"phase1_main_seed{seed}", r)

    # -- phase 2: leave-one-family-out at k=1 -------------------------------
    log("phase 2: leave-one-family-out at k=1")
    loos = []
    for seed in a.seeds:
        r, _ = run_one(n, a.eta, a.rho, seed, 1, a.lam, a.temp, "grey",
                       a.pi_floor, a.pi0, max(100, a.boot // 4), loo=True,
                       name_share=a.name_share)
        loos.append(r["loo"])
        save(f"phase2_loo_seed{seed}", r["loo"])

    loo_avg = {}
    for fam in ("P1", "P2", "P3"):
        vals = [item[fam] for item in loos if isinstance(item.get(fam), dict)
                and "D4" in item[fam] and "n_pure" in item[fam]]
        if vals:
            dets = [d for d in DETS if d in vals[0]]
            loo_avg[fam] = {d: float(np.mean([v[d] for v in vals]))
                            for d in dets}
            for d in dets:
                loo_avg[fam][d + "_matched_in"] = float(
                    np.mean([v[d + "_matched_in"] for v in vals]))
                loo_avg[fam][d + "_drop"] = float(
                    np.mean([v[d + "_drop"] for v in vals]))
                loo_avg[fam][d + "_per_seed"] = [
                    [v[d + "_matched_in"], v[d]] for v in vals]
            loo_avg[fam]["n_pure"] = float(np.mean([v["n_pure"] for v in vals]))
            loo_avg[fam]["n_pure_per_seed"] = [v["n_pure"] for v in vals]
            loo_avg[fam]["purity"] = float(np.mean([v["purity"] for v in vals]))
    save("phase2_loo", loo_avg)

    # -- phase 3: eta sweep --------------------------------------------------
    log("phase 3: eta sweep")
    etas = (0.02, 0.05, 0.10, 0.15, 0.25, 0.40)
    sweep = []
    for e in etas:
        r, _ = run_one(n // 2, e, a.rho, a.seeds[0], a.k, a.lam, a.temp, "grey",
                       a.pi_floor, a.pi0, boot=(20 if a.quick else 100),
                       name_share=a.name_share)
        sweep.append((e, r))
        log(f"  eta={e}: D4 AUC={r['detectors']['D4']['auc']:.3f}")
    save("phase3_eta_sweep",
         {str(e): r["detectors"] for e, r in sweep})

    # -- phase 4: ablations --------------------------------------------------
    log("phase 4: ablations")
    abl = []
    for fam, keep in (("P1", "P1"), ("P2", "P2"), ("P3", "P3")):
        saved = list(B.PRIMITIVES)
        B.PRIMITIVES[:] = [p for p in saved if B.FAMILY[p] == keep]
        r, _ = run_one(n // 2, a.eta, a.rho, a.seeds[0], a.k, a.lam, a.temp,
                       "grey", a.pi_floor, a.pi0,
                       boot=(20 if a.quick else 200),
                       name_share=a.name_share)
        B.PRIMITIVES[:] = saved
        abl.append(("Primitive family" if fam == "P1" else "", f"{fam} only", r))
        log(f"  {fam} only: D4 AUC={r['detectors']['D4']['auc']:.3f}")
    for kk in (1, 2, 3):
        r, _ = run_one(n // 2, a.eta, a.rho, a.seeds[0], kk, a.lam, a.temp,
                       "grey", a.pi_floor, a.pi0,
                       boot=(20 if a.quick else 200),
                       name_share=a.name_share)
        abl.append(("Evader budget" if kk == 1 else "", f"$k={kk}$", r))
        log(f"  k={kk}: D4 AUC={r['detectors']['D4']['auc']:.3f}")
    for kn in ("black", "grey"):
        r, _ = run_one(n // 2, a.eta, a.rho, a.seeds[0], a.k, a.lam, a.temp,
                       kn, a.pi_floor, a.pi0,
                       boot=(20 if a.quick else 200),
                       name_share=a.name_share)
        abl.append(("Knowledge" if kn == "black" else "", kn + "-box", r))
        log(f"  {kn}-box: D4 AUC={r['detectors']['D4']['auc']:.3f}")
    save("phase4_ablations",
         [{"factor": f, "setting": s, "detectors": r["detectors"]}
          for f, s, r in abl])

    # -- phase 5: calibration grid pi_0 x name-share ------------------------
    log("phase 5: calibration grid (pi_0 x name-share)")
    grid = {}
    for tgt in (0.30, 0.45, 0.60):
        for share in (0.4, 0.6, 0.8):
            r, _ = run_one(n // 2, a.eta, a.rho, a.seeds[0], a.k, a.lam, a.temp,
                           "grey", a.pi_floor, tgt, boot=(20 if a.quick else 100),
                           name_share=share, extra=False)
            sels = {kk: v["SEL"] for kk, v in r["sel"].items()
                    if not kk.startswith("_")}
            grid[f"pi0={tgt},share={share}"] = {
                "target_pi0": tgt, "name_share": share,
                "P_NAME": r["config"]["solved_P_NAME"],
                "TAU": r["config"]["solved_TAU"],
                "detectors": r["detectors"],
                "SEL_by_primitive": sels,
                "SEL_min": min(sels.values()) if sels else None,
                "SEL_max": max(sels.values()) if sels else None}
            log(f"  pi0={tgt} share={share}: D4 AUC="
                f"{r['detectors']['D4']['auc']:.3f} SEL "
                f"{grid[f'pi0={tgt},share={share}']['SEL_min']:.2f}--"
                f"{grid[f'pi0={tgt},share={share}']['SEL_max']:.2f}")
    save("phase5_calibration_grid", grid)

    # -- phase 6: XML corpus + XSD ------------------------------------------
    if a.emit_xml and last_msgs:
        log("phase 6: XML corpus")
        p = os.path.join(OUT, "corpus_sample.jsonl")
        nw = B.write_corpus(last_msgs, p, limit=a.emit_xml)
        log(f"  wrote {nw} messages -> {p}")
        if a.xsd_dir:
            nchk, ok, errs = B.validate_corpus(last_msgs, a.xsd_dir)
            log(f"  XSD: {ok}/{nchk} valid")
            for e in errs:
                log("   " + e)
            save("phase6_xsd", {"checked": nchk, "valid": ok, "errors": errs})

    # -- emit LaTeX ----------------------------------------------------------
    log("emitting LaTeX fragments")
    emit_table1(mains, os.path.join(TEX, "table1.tex"))
    emit_table_loo(loo_avg, os.path.join(TEX, "table_loo.tex"))
    emit_table2(abl, os.path.join(TEX, "table2.tex"))
    emit_fig_roc(mains[0], os.path.join(TEX, "fig_roc.tex"))
    emit_fig_sel(mains, os.path.join(TEX, "fig_sel.tex"))
    emit_fig_eta(sweep, os.path.join(TEX, "fig_eta.tex"))

    # -- machine-readable summary used by verify_claims.py ------------------
    dets_present = [d for d in DETS if d in mains[0]["detectors"]]
    summ = {"git_commit": GIT_SHA, "seeds": a.seeds, "n_each": n,
            "config": {kk: v for kk, v in mains[0]["config"].items()
                       if kk not in ("seed",)},
            "n_gamed": [r["n_gamed"] for r in mains],
            "n_illicit": [r["n_illicit"] for r in mains],
            "n_unevaded_illicit": [r["sel"]["_baseline"]["n_unevaded_illicit"]
                                   for r in mains],
            "delta0": [r["sel"]["_baseline"]["delta0"] for r in mains],
            "tpr_ceiling@0.01": float(np.mean([r["tpr_ceiling@0.01"]
                                               for r in mains])),
            "tpr_ceiling@0.001": float(np.mean([r["tpr_ceiling@0.001"]
                                                for r in mains])),
            "detectors": {}, "sel": {}, "sel_D5": {},
            "loo": loo_avg,
            "eta_sweep": {str(e): {d: r["detectors"][d]["auc"]
                                   for d in dets_present} for e, r in sweep},
            "ablations": [{"factor": f, "setting": st,
                           "D4_auc": r["detectors"]["D4"]["auc"],
                           "D5_auc": r["detectors"].get("D5", {}).get("auc")}
                          for f, st, r in abl],
            "grid": {kk: {"D4_auc": v["detectors"]["D4"]["auc"],
                          "SEL_min": v["SEL_min"], "SEL_max": v["SEL_max"]}
                     for kk, v in grid.items()}}
    for d in dets_present:
        rows = [r["detectors"][d] for r in mains]
        ent = {}
        for met in ("auc", "ap", "tpr@0.01", "tpr@0.001",
                    "benign_alerts_per_M@0.01", "benign_alerts_per_M@0.001"):
            vals = [row[met] for row in rows]
            ent[met] = float(np.mean(vals))
            ent[met + "_per_seed"] = vals
            ent[met + "_min"], ent[met + "_max"] = float(min(vals)), float(max(vals))
        for met in ("auc_ci95", "tpr@0.01_ci95", "tpr@0.001_ci95"):
            if met in rows[0]:
                ent[met + "_per_seed"] = [row[met] for row in rows]
        summ["detectors"][d] = ent
    for key in ("sel", "sel_D5"):
        if key not in mains[0]:
            continue
        for p in B.PRIMITIVES:
            if not all(p in r[key] for r in mains):
                continue
            summ[key][p] = {
                "n_mean": float(np.mean([r[key][p]["n"] for r in mains])),
                "SEL": float(np.mean([r[key][p]["SEL"] for r in mains])),
                "SEL_res": float(np.mean([r[key][p]["SEL_res"] for r in mains])),
                "detect_rate": float(np.mean([r[key][p]["detect_rate"]
                                              for r in mains])),
                "SEL_ci_per_seed": [[r[key][p]["SEL_lo"], r[key][p]["SEL_hi"]]
                                    for r in mains],
                "SEL_res_ci_per_seed": [[r[key][p]["SEL_res_lo"],
                                         r[key][p]["SEL_res_hi"]] for r in mains]}
    save("summary", summ)

    summary = f"""# Verified protocol summary

n per main run: {n} · seeds: {a.seeds} · eta: {a.eta} · rho: {a.rho}
lambda: {a.lam} · temperature: {a.temp} · target pi_0: {a.pi0}
elapsed: {time.time() - t0:.0f}s

- `table1.tex` reports mean AUC and TPR at exact expected alert capacities.
- `table_loo.tex` reports leave-one-family-out at k=1 on pure-family rows.
- `fig_sel.tex` uses three-seed means.
- XSD validation is reported only when `--xsd-dir` is supplied.

## Calibration sweep
{json.dumps(calib, indent=2)}

## Leave-one-family-out
{json.dumps(loo_avg, indent=2)}
"""
    open(os.path.join(TEX, "SUMMARY.md"), "w").write(summary)
    log(f"done in {time.time() - t0:.0f}s -> {TEX}/SUMMARY.md")


if __name__ == "__main__":
    main()
