#!/usr/bin/env python3
"""
run_protocol.py -- executes the full evaluation protocol from Section V of
"Detecting Purpose-Code Gaming in ISO 20022 Payments" and writes LaTeX
fragments that drop straight into the paper.

Phases
  0  calibration sweep      pi_0 in {0.30, 0.45, 0.60}
  1  main run x 3 seeds     -> Table I
  2  leave-one-primitive-out -> Table I, AUC_LOO column
  3  eta sweep              -> Fig. eta (the paper's actual result)
  4  ablations              -> Table II
  5  SEL per primitive      -> Fig. SEL
  6  XML corpus + XSD validation

Outputs
  results/*.json            raw results, one file per run, config-hashed
  latex/fig_roc.tex         pgfplots axis, paste over Fig. 4
  latex/fig_sel.tex         pgfplots axis, paste over Fig. 5
  latex/fig_eta.tex         pgfplots axis, new figure
  latex/table1.tex          tabular body, paste into Table I
  latex/table2.tex          tabular body, paste into Table II
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
import time

import numpy as np

import iso20022_gaming_bench as B

OUT = "results"
TEX = "latex"
DET_LABEL = {
    "D0": r"$D_0$ schema/code list",
    "D1": r"$D_1$ rules C1--C4",
    "D2": r"$D_2$ naive classifier",
    "D3": r"$D_3$ anomaly C3--C5",
    "D4": r"$D_4$ $D_1 \cup D_3$",
}
NEEDS_LABELS = {"D0": "no", "D1": "no", "D2": "yes", "D3": "no", "D4": "no"}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def save(tag, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{tag}.json")
    with open(p, "w") as f:
        json.dump(obj, f, indent=2)
    return p


def run_one(n, eta, rho, seed, k, lam, temp, knowledge, pi_floor,
            target_pi0, boot, loo=False):
    B.PI_FLOOR = pi_floor
    B.TEMP = temp
    B.P_NAME, B.TAU = 0.90, 0.55          # reset before each calibration
    if target_pi0 is not None:
        B.calibrate_p_name(target_pi0, eta, seed, knowledge)
    msgs = B.generate(n, eta, rho, seed, k, lam, knowledge)
    res = B.evaluate(msgs, seed=seed, boot=boot)
    if loo:
        res["loo"] = B.evaluate_loo(msgs, seed=seed)
    res["config"] = dict(n=n, eta=eta, rho=rho, seed=seed, k=k, lam=lam,
                         temp=temp, knowledge=knowledge, pi_floor=pi_floor,
                         target_pi0=target_pi0,
                         solved_P_NAME=B.P_NAME, solved_TAU=B.TAU)
    return res, msgs


# ---------------------------------------------------------------------------
def emit_table1(mains, loo_res, path):
    """Table I body: AUC / TPR@1% / TPR@0.1% / AUC_LOO, mean +- spread."""
    rows = []
    for d in ("D0", "D1", "D2", "D3", "D4"):
        auc = np.array([r["detectors"][d]["auc"] for r in mains])
        t1 = np.array([r["detectors"][d]["tpr@0.01"] for r in mains])
        t01 = np.array([r["detectors"][d]["tpr@0.001"] for r in mains])
        loo_vals = [loo_res[f][d] for f in ("P1", "P2", "P3")
                    if isinstance(loo_res.get(f), dict) and d in loo_res[f]]
        loo = np.mean(loo_vals) if loo_vals else float("nan")
        rows.append(
            f"{DET_LABEL[d]} & {NEEDS_LABELS[d]} & "
            f"{auc.mean():.3f} & {t1.mean():.3f} & {t01.mean():.3f} & "
            + ("--" if np.isnan(loo) else f"{loo:.3f}") + r" \\")
    body = "\n".join(rows)
    seeds = ", ".join(str(r["config"]["seed"]) for r in mains)
    note = (f"% mean over seeds {seeds}; n={mains[0]['config']['n']}, "
            f"eta={mains[0]['config']['eta']}, "
            f"target pi_0={mains[0]['config']['target_pi0']}\n")
    open(path, "w").write(note + body + "\n")
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


def emit_fig_sel(main, path):
    prims = [p for p in B.PRIMITIVES if p in main["sel"]]
    if not prims:
        open(path, "w").write("% no primitive reached the n>=30 threshold\n")
        return ""
    coords = " ".join(f"({p},{main['sel'][p]['SEL']:.3f})" for p in prims)
    coords_r = " ".join(f"({p},{main['sel'][p]['SEL_res']:.3f})" for p in prims)
    err = " ".join(
        f"({p},{main['sel'][p]['SEL']:.3f}) +- (0,{(main['sel'][p]['SEL_hi']-main['sel'][p]['SEL']):.3f})"
        for p in prims)
    lo = min(min(main["sel"][p]["SEL_res"] for p in prims), 1.0)
    hi = max(main["sel"][p]["SEL_hi"] for p in prims)
    body = (r"""\begin{tikzpicture}
\begin{axis}[
  width=0.94\columnwidth, height=4.1cm,
  ybar=1.2pt, bar width=5pt,
  ylabel={SEL},
  symbolic x coords={""" + ",".join(prims) + r"""},
  xtick=data, ymin=""" + f"{max(0.9, lo*0.95):.2f}" + r""", ymax="""
        + f"{hi*1.08:.2f}" + r""",
  grid=both, grid style={black!12},
  legend style={at={(0.02,0.97)},anchor=north west,font=\tiny,
                draw=black!30,legend columns=2},
  label style={font=\scriptsize}, tick label style={font=\tiny}
]
\addplot[fill=black!25] coordinates {""" + coords + r"""};
\addlegendentry{$\mathrm{SEL}$ (no detector)}
\addplot[fill=black!60] coordinates {""" + coords_r + r"""};
\addlegendentry{$\mathrm{SEL_{res}}$ with $D_4$}
\end{axis}
\end{tikzpicture}""")
    open(path, "w").write(body + "\n%" + err + "\n")
    return body


def emit_fig_eta(sweep, path):
    plots = []
    styles = {"D1": "dashed", "D3": "solid", "D4": "solid,line width=1.1pt"}
    for d in ("D1", "D3", "D4"):
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
    ap.add_argument("--seeds", type=int, nargs="+", default=[7, 8, 9])
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--xsd-dir", default=None)
    ap.add_argument("--emit-xml", type=int, default=2000)
    a = ap.parse_args()

    n = a.n or (6000 if a.quick else 200_000)
    if a.quick:
        a.seeds, a.boot = a.seeds[:2], 200
    os.makedirs(TEX, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()

    # -- phase 0: calibration sweep -----------------------------------------
    log("phase 0: calibration sweep")
    calib = {}
    for tgt in (0.30, 0.45, 0.60):
        r, _ = run_one(n // 4, a.eta, a.rho, a.seeds[0], 2, a.lam, a.temp,
                       "grey", a.pi_floor, tgt, boot=100)
        sels = {k: v["SEL"] for k, v in r["sel"].items() if not k.startswith("_")}
        calib[str(tgt)] = {"P_NAME": r["config"]["solved_P_NAME"],
                           "TAU": r["config"]["solved_TAU"],
                           "SEL_mean": float(np.mean(list(sels.values())))
                           if sels else None,
                           "SEL_by_primitive": sels}
        log(f"  pi_0={tgt}: mean SEL={calib[str(tgt)]['SEL_mean']}")
    save("phase0_calibration", calib)

    # -- phase 1 + 2: main runs and LOO -------------------------------------
    log(f"phase 1-2: main runs, n={n}, seeds={a.seeds}")
    mains, loos, last_msgs = [], [], None
    for s in a.seeds:
        r, msgs = run_one(n, a.eta, a.rho, s, 2, a.lam, a.temp, "grey",
                          a.pi_floor, a.pi0, a.boot, loo=True)
        mains.append(r)
        loos.append(r["loo"])
        last_msgs = msgs
        log(f"  seed {s}: D4 AUC={r['detectors']['D4']['auc']:.3f} "
            f"gamed={r['n_gamed']}")
        save(f"phase1_main_seed{s}", r)

    loo_avg = {}
    for fam in ("P1", "P2", "P3"):
        vals = [l[fam] for l in loos if isinstance(l.get(fam), dict)
                and "D4" in l[fam]]
        if vals:
            loo_avg[fam] = {d: float(np.mean([v[d] for v in vals]))
                            for d in ("D0", "D1", "D2", "D3", "D4")}
            loo_avg[fam]["n_family"] = float(np.mean([v["n_family"] for v in vals]))
    save("phase2_loo", loo_avg)

    # -- phase 3: eta sweep --------------------------------------------------
    log("phase 3: eta sweep")
    etas = (0.02, 0.05, 0.10, 0.15, 0.25, 0.40)
    sweep = []
    for e in etas:
        r, _ = run_one(n // 2, e, a.rho, a.seeds[0], 2, a.lam, a.temp, "grey",
                       a.pi_floor, a.pi0, boot=100)
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
        r, _ = run_one(n // 2, a.eta, a.rho, a.seeds[0], 2, a.lam, a.temp,
                       "grey", a.pi_floor, a.pi0, boot=200)
        B.PRIMITIVES[:] = saved
        abl.append(("Primitive family" if fam == "P1" else "", f"{fam} only", r))
        log(f"  {fam} only: D4 AUC={r['detectors']['D4']['auc']:.3f}")
    for kk in (1, 2, 3):
        r, _ = run_one(n // 2, a.eta, a.rho, a.seeds[0], kk, a.lam, a.temp,
                       "grey", a.pi_floor, a.pi0, boot=200)
        abl.append(("Evader budget" if kk == 1 else "", f"$k={kk}$", r))
        log(f"  k={kk}: D4 AUC={r['detectors']['D4']['auc']:.3f}")
    for kn in ("black", "grey"):
        r, _ = run_one(n // 2, a.eta, a.rho, a.seeds[0], 2, a.lam, a.temp,
                       kn, a.pi_floor, a.pi0, boot=200)
        abl.append(("Knowledge" if kn == "black" else "", kn + "-box", r))
        log(f"  {kn}-box: D4 AUC={r['detectors']['D4']['auc']:.3f}")
    save("phase4_ablations",
         [{"factor": f, "setting": s, "detectors": r["detectors"]}
          for f, s, r in abl])

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
    emit_table1(mains, loo_avg, os.path.join(TEX, "table1.tex"))
    emit_table2(abl, os.path.join(TEX, "table2.tex"))
    emit_fig_roc(mains[0], os.path.join(TEX, "fig_roc.tex"))
    emit_fig_sel(mains[0], os.path.join(TEX, "fig_sel.tex"))
    emit_fig_eta(sweep, os.path.join(TEX, "fig_eta.tex"))

    summary = f"""# Protocol run summary

n per run: {n} · seeds: {a.seeds} · eta: {a.eta} · rho: {a.rho}
lambda: {a.lam} · temp: {a.temp} · pi_floor: {a.pi_floor} · target pi_0: {a.pi0}
elapsed: {time.time() - t0:.0f}s

## Paste into paper_F7_IEEEtran.tex, in this order

1. **Table I** — replace the five `\\tbd` rows with `latex/table1.tex`.
   Delete "No values are given because the run has not been performed."
2. **Table II** — replace the body with `latex/table2.tex`.
3. **Fig. 4 (ROC)** — replace the whole `tikzpicture` with `latex/fig_roc.tex`.
   Rewrite the caption: drop "Illustrative (synthetic); not measured" and the
   analytic-model sentence; state n, seeds, eta and the calibrated pi_0.
4. **Fig. 5 (SEL)** — replace with `latex/fig_sel.tex`. Same caption surgery.
   Report the bootstrap intervals in the caption (they are in the JSON and as
   a comment in the .tex fragment).
5. **Add Fig. 6 (eta sweep)** from `latex/fig_eta.tex`. This is the paper's
   actual result. If you are over 6 pages, drop Fig. 2 (pipeline) — it is the
   most expendable figure — rather than this one.
6. **Section VI** — delete the bold "have not been executed" sentence and the
   "Illustrative Analysis and Reporting Template" title; rename to "Results".
   Keep H1--H3 but rewrite each as confirmed / not confirmed against the data.
   Keep §VI-B (falsification) and state which outcome occurred.
7. **Section VII-C Conclusion threat** — rewrite; results now exist.
8. **Abstract** — replace the last sentence with the measured headline.
9. **Section IV-B** — state the calibrated P_NAME, TAU and PI_FLOOR, and note
   that SEL is reported at target pi_0 = {a.pi0} with the sweep in phase 0.
10. **Section V** — add the TEMP value ({a.temp}) and the lambda ({a.lam}).

## Calibration sweep (phase 0) — cite this, do not report SEL at one point
{json.dumps(calib, indent=2)}

## Leave-one-primitive-out (the headline)
{json.dumps(loo_avg, indent=2)}
"""
    open(os.path.join(TEX, "SUMMARY.md"), "w").write(summary)
    log(f"done in {time.time() - t0:.0f}s -> {TEX}/SUMMARY.md")


if __name__ == "__main__":
    main()
