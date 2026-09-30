#!/usr/bin/env python3
"""
run_protocol.py -- v3 evaluation protocol (temporal, paired, pre-registered).

Phases
  0  calibration grid       pi_0 x name-share, config A
  1  main runs              seeds 7-16, 200k, k=2: temporal protocol, frozen
                            thresholds, pair-clustered bootstrap, paired SEL
  2  leave-one-family-out   same seeds, k=1
  3  eta sweep              seed 7, 100k
  4  ablations              family-only, k, knowledge (seed 7, 100k)
  5  prevalence             rho in {0.005, 0.01, 0.05}, seeds 7-9, 200k
  6  generator shift        A -> B, seeds 7-9
  7  validity               XSD validation and invariants, seed 7 corpus
  8  artefact audit         seed 7
Writes results/*.json and results/summary.json.
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
GIT_SHA = "unversioned"
DETS = B.DETECTORS


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def save(tag, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{tag}.json")
    with open(p, "w") as f:
        json.dump(obj, f, indent=1)
    return p


def _git_sha():
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here, text=True).strip()
        st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=here,
                            capture_output=True, text=True).stdout.strip()
        return sha + ("-dirty" if st else "")
    except Exception:
        return "unversioned"


def setup(a, seed, pi0, share, cfg):
    B.PI_FLOOR = a.pi_floor
    B.TEMP = a.temp
    B.P_NAME, B.TAU = 0.90, 0.55
    return B.calibrate(pi0, a.eta, seed, "grey", share, n_probe=4000, cfg=cfg, verbose=True)


def cfg_dict(a, n, seed, k, rho, knowledge, pi0, share, cfg):
    return dict(n=n, eta=a.eta, rho=rho, seed=seed, k=k, lam=a.lam, temp=a.temp, knowledge=knowledge,
                pi_floor=a.pi_floor, target_pi0=pi0, name_share=share, generator=cfg.name,
                solved_P_NAME=B.P_NAME, solved_TAU=B.TAU, git_commit=GIT_SHA,
                protocol="temporal 60/20/20, thresholds frozen on validation, pair-clustered bootstrap")


def main():
    global OUT, GIT_SHA
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--rho", type=float, default=0.05)
    ap.add_argument("--eta", type=float, default=0.15)
    ap.add_argument("--lam", type=float, default=0.18)
    ap.add_argument("--temp", type=float, default=0.10)
    ap.add_argument("--pi-floor", type=float, default=0.10)
    ap.add_argument("--pi0", type=float, default=0.45)
    ap.add_argument("--name-share", type=float, default=0.6)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(range(7, 17)))
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--xsd-dir", default="xsd")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    OUT = a.out
    GIT_SHA = _git_sha()
    log(f"git commit: {GIT_SHA}")
    n = a.n or (8000 if a.quick else 200_000)
    if a.quick:
        a.seeds = a.seeds[:2]; a.boot = min(a.boot, 30)
    A, Bc = B.CONFIG_A, B.CONFIG_B
    t0 = time.time()

    # -- phase 0: calibration grid --------------------------------------------
    log("phase 0: calibration grid")
    grid = {}
    for tgt in (0.30, 0.45, 0.60):
        for share in (0.4, 0.6, 0.8):
            setup(a, a.seeds[0], tgt, share, A)
            msgs = B.generate(n // 2, a.eta, a.rho, a.seeds[0], a.k, a.lam, "grey", cfg=A)
            r = B.evaluate_run(msgs, seed=a.seeds[0], n_boot=0)
            sels = {p: v["SEL"] for p, v in r["sel"].items() if p != "all" and "SEL" in v}
            grid[f"pi0={tgt},share={share}"] = {"P_NAME": B.P_NAME, "TAU": B.TAU,
                                               "D1_auc": r["detectors"]["D1"]["auc"], "D2_auc": r["detectors"]["D2"]["auc"],
                                               "D5_auc": r["detectors"]["D5"]["auc"], "D7_auc": r["detectors"]["D7"]["auc"],
                                               "SEL_all": r["sel"]["all"].get("SEL"), "SEL_min": min(sels.values()), "SEL_max": max(sels.values())}
            log(f"  pi0={tgt} share={share}: D1 {r['detectors']['D1']['auc']:.3f} SEL {min(sels.values()):.2f}-{max(sels.values()):.2f}")
    save("phase0_calibration_grid", grid)

    # -- phase 1: main runs ---------------------------------------------------
    log(f"phase 1: main runs n={n} seeds={a.seeds}")
    mains = []
    for seed in a.seeds:
        setup(a, seed, a.pi0, a.name_share, A)
        msgs = B.generate(n, a.eta, a.rho, seed, a.k, a.lam, "grey", cfg=A)
        r = B.evaluate_run(msgs, seed=seed, n_boot=a.boot)
        r["config"] = cfg_dict(a, n, seed, a.k, a.rho, "grey", a.pi0, a.name_share, A)
        r["primitive_counts"] = {p: int(sum(p in m.primitives for m in msgs)) for p in B.PRIMITIVES}
        r["primitive_counts_test"] = {p: int(sum(p in m.primitives for m in msgs if m.t >= int(0.8 * n))) for p in B.PRIMITIVES}
        mains.append(r)
        save(f"phase1_main_seed{seed}", r)
        log(f"  seed {seed}: D1 {r['detectors']['D1']['auc']:.3f}/{r['detectors']['D1']['recovery@0.01']:.3f} "
            f"D2 {r['detectors']['D2']['auc']:.3f}/{r['detectors']['D2']['recovery@0.01']:.3f} "
            f"D5 {r['detectors']['D5']['auc']:.3f}/{r['detectors']['D5']['recovery@0.01']:.3f} "
            f"D7 {r['detectors']['D7']['auc']:.3f}/{r['detectors']['D7']['recovery@0.01']:.3f} gamed_test={r['n_gamed_test']}")

    # -- phase 2: leave-one-family-out at k=1 ----------------------------------
    log("phase 2: leave-one-family-out (k=1)")
    loos = []
    for seed in a.seeds:
        setup(a, seed, a.pi0, a.name_share, A)
        msgs = B.generate(n, a.eta, a.rho, seed, 1, a.lam, "grey", cfg=A)
        l = B.evaluate_loo(msgs, seed=seed)
        l["config"] = cfg_dict(a, n, seed, 1, a.rho, "grey", a.pi0, a.name_share, A)
        loos.append(l)
        save(f"phase2_loo_seed{seed}", l)
        log("  seed %d: " % seed + " ".join(f"{f}:{l[f].get('D2_matched_in', float('nan')):.3f}->{l[f].get('D2', float('nan')):.3f}" for f in ("P1", "P2", "P3")))

    # -- phase 3: eta sweep ---------------------------------------------------
    log("phase 3: eta sweep")
    sweep = {}
    for e in (0.02, 0.05, 0.10, 0.15, 0.25, 0.40):
        B.PI_FLOOR = a.pi_floor; B.TEMP = a.temp; B.P_NAME, B.TAU = 0.90, 0.55
        B.calibrate(a.pi0, e, a.seeds[0], "grey", a.name_share, n_probe=4000, cfg=A, verbose=False)
        msgs = B.generate(n // 2, e, a.rho, a.seeds[0], a.k, a.lam, "grey", cfg=A)
        r = B.evaluate_run(msgs, seed=a.seeds[0], n_boot=0, want_prims=False)
        sweep[str(e)] = {d: {k: r["detectors"][d][k] for k in ("auc", "ap", "recovery@0.01", "precision@0.01")} for d in DETS}
        log(f"  eta={e}: " + " ".join(f"{d} {sweep[str(e)][d]['auc']:.3f}" for d in ("D1", "D2", "D5", "D7")))
    save("phase3_eta_sweep", sweep)

    # -- phase 4: ablations ---------------------------------------------------
    log("phase 4: ablations")
    abl = []
    def one_abl(factor, setting, k, knowledge, prims=None):
        saved = list(B.PRIMITIVES)
        if prims is not None:
            B.PRIMITIVES[:] = prims
        setup(a, a.seeds[0], a.pi0, a.name_share, A)
        msgs = B.generate(n // 2, a.eta, a.rho, a.seeds[0], k, a.lam, knowledge, cfg=A)
        r = B.evaluate_run(msgs, seed=a.seeds[0], n_boot=0, want_prims=False)
        B.PRIMITIVES[:] = saved
        abl.append({"factor": factor, "setting": setting, **{d: {k2: r["detectors"][d][k2] for k2 in ("auc", "ap", "recovery@0.01")} for d in DETS}})
        log(f"  {factor} {setting}: " + " ".join(f"{d} {r['detectors'][d]['auc']:.3f}" for d in ("D1", "D2", "D5", "D7")))
    for fam in ("P1", "P2", "P3"):
        one_abl("family", fam, a.k, "grey", [p for p in B.PRIMITIVES if B.FAMILY[p] == fam])
    for kk in (1, 2, 3):
        one_abl("budget", f"k={kk}", kk, "grey")
    for kn in ("black", "grey"):
        one_abl("knowledge", kn, a.k, kn)
    save("phase4_ablations", abl)

    # -- phase 5: prevalence --------------------------------------------------
    log("phase 5: prevalence sensitivity")
    prev = {}
    for rho in (0.005, 0.01, 0.05):
        rows = []
        for seed in a.seeds[:3]:
            setup(a, seed, a.pi0, a.name_share, A)
            msgs = B.generate(n, a.eta, rho, seed, a.k, a.lam, "grey", cfg=A)
            r = B.evaluate_run(msgs, seed=seed, n_boot=0, want_prims=False)
            rows.append({"seed": seed, "n_gamed_test": r["n_gamed_test"], "prevalence_test": r["prevalence_test"],
                         "ceiling@0.01": r["tpr_ceiling@0.01"],
                         **{d: {k2: r["detectors"][d][k2] for k2 in ("auc", "ap", "recovery@0.01", "precision@0.01", "alerts_per_detection@0.01", "alert_rate@0.01")} for d in DETS}})
        prev[str(rho)] = rows
        log(f"  rho={rho}: ceiling {np.mean([x['ceiling@0.01'] for x in rows]):.3f} D2 prec {np.mean([x['D2']['precision@0.01'] for x in rows]):.3f} D1 prec {np.mean([x['D1']['precision@0.01'] for x in rows]):.3f}")
    save("phase5_prevalence", prev)

    # -- phase 6: generator shift ---------------------------------------------
    log("phase 6: generator shift A -> B")
    shifts = []
    for seed in a.seeds[:3]:
        setup(a, seed, a.pi0, a.name_share, A)        # the screening abstraction stays A-calibrated
        ma = B.generate(n, a.eta, a.rho, seed, a.k, a.lam, "grey", cfg=A)
        mb = B.generate(n, a.eta, a.rho, seed + 100, a.k, a.lam, "grey", cfg=Bc)
        s = B.evaluate_shift(ma, mb, seed=seed)
        s["seed"] = seed
        shifts.append(s)
        log(f"  seed {seed}: " + " ".join(f"{d} A->B {s['detectors'][d]['A_to_B']['auc']:.3f}/{s['detectors'][d]['A_to_B']['recovery@0.01']:.3f} (B->B {s['detectors'][d]['B_to_B']['auc']:.3f})" for d in ("D1", "D2", "D5", "D7")))
    save("phase6_shift", shifts)

    # -- phase 7: validity (XSD + invariants) ---------------------------------
    log("phase 7: XSD validation and invariants (seed %d)" % a.seeds[0])
    setup(a, a.seeds[0], a.pi0, a.name_share, A)
    msgs = B.generate(n, a.eta, a.rho, a.seeds[0], a.k, a.lam, "grey", cfg=A)
    val = validate_all(msgs, a.xsd_dir, n)
    save("phase7_validity", val)
    log(f"  XSD valid {val['xsd']['valid']}/{val['xsd']['checked']}; invariant violations {val['invariants']['violations_total']}")

    # -- phase 8: artefact audit ----------------------------------------------
    log("phase 8: artefact audit")
    aud = B.artefact_audit(msgs, seed=a.seeds[0])
    save("phase8_artefact_audit", aud)
    log(f"  gamed out of range {aud['share_gamed_test_out_of_range']:.4f}; max alert mass {max(aud['alert_mass_on_out_of_range'].values()):.3f}")

    # -- summary --------------------------------------------------------------
    summ = summarise(a, n, mains, loos, sweep, abl, prev, shifts, val, aud, grid)
    save("summary", summ)
    log(f"done in {time.time() - t0:.0f}s")


def validate_all(msgs, xsd_dir, n):
    from lxml import etree
    schemas = {}
    for key, fn in (("pain.001", "pain.001.001.09.xsd"), ("pacs.008", "pacs.008.001.08.xsd")):
        p = os.path.join(xsd_dir, fn)
        if not os.path.exists(p):
            return {"xsd": {"checked": 0, "valid": 0, "error": f"missing {p}"}, "invariants": {"violations_total": -1}}
        schemas[key] = etree.XMLSchema(etree.parse(p))
    test_start = int(0.8 * n)
    targets = [(m, "test") for m in msgs if m.t >= test_start] + [(m, "gamed") for m in msgs if m.gamed and m.t < test_start]
    by_prim = {p: {"checked": 0, "valid": 0} for p in B.PRIMITIVES + ["benign", "unevaded", "original"]}
    checked = valid = 0
    errs = []
    def check(m, keys):
        nonlocal checked, valid
        ok = True
        try:
            schemas[m.msg_type].assertValid(etree.fromstring(B.to_xml(m).encode()))
        except Exception as e:      # noqa: BLE001
            ok = False
            if len(errs) < 10:
                errs.append(f"{m.msg_id} {m.msg_type} {list(m.primitives)}: {str(e)[:160]}")
        checked += 1; valid += ok
        for k in keys:
            by_prim[k]["checked"] += 1; by_prim[k]["valid"] += ok
    for m, _ in targets:
        keys = list(m.primitives) if m.gamed else (["unevaded"] if m.illicit else ["benign"])
        check(m, keys)
        if m.orig is not None:
            check(m.orig, ["original"])
    viol = {}
    n_gamed = 0
    for m in msgs:
        if m.gamed:
            n_gamed += 1
            for v in B.check_invariants(m):
                viol[v] = viol.get(v, 0) + 1
    return {"xsd": {"checked": checked, "valid": valid, "by_primitive": by_prim, "first_errors": errs},
            "invariants": {"gamed_checked": n_gamed, "violations_total": int(sum(viol.values())), "by_kind": viol}}


def summarise(a, n, mains, loos, sweep, abl, prev, shifts, val, aud, grid):
    def mean(v): return float(np.mean(v))
    def sd(v): return float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    S = {"git_commit": GIT_SHA, "seeds": a.seeds, "n_each": n, "config": {k: v for k, v in mains[0]["config"].items() if k != "seed"},
         "n_gamed_test": [r["n_gamed_test"] for r in mains], "n_gamed": [r["n_gamed"] for r in mains],
         "n_illicit_test": [r["n_illicit_test"] for r in mains], "n_pairs_test": [r["n_pairs_test"] for r in mains],
         "prevalence_test": mean([r["prevalence_test"] for r in mains]),
         "tpr_ceiling@0.01": mean([r["tpr_ceiling@0.01"] for r in mains]), "tpr_ceiling@0.001": mean([r["tpr_ceiling@0.001"] for r in mains]),
         "primitive_counts": {p: mean([r["primitive_counts"][p] for r in mains]) for p in B.PRIMITIVES},
         "primitive_counts_test": {p: mean([r["primitive_counts_test"][p] for r in mains]) for p in B.PRIMITIVES},
         "detectors": {}, "sel": {}, "loo": {}, "eta_sweep": sweep, "ablations": abl, "prevalence": {}, "shift": {},
         "validity": val, "artefact_audit": aud, "grid": grid}
    mets = ["auc", "ap", "recovery@0.01", "precision@0.01", "alert_rate@0.01", "alerts_per_detection@0.01",
            "topq_recovery@0.01", "recovery@0.001", "precision@0.001", "alert_rate@0.001"]
    for d in DETS:
        e = {}
        for met in mets:
            vals = [r["detectors"][d][met] for r in mains]
            e[met] = mean(vals); e[met + "_sd"] = sd(vals); e[met + "_per_seed"] = vals
        for cik in ("auc_ci95", "ap_ci95", "recovery@0.01_ci95", "precision@0.01_ci95", "auc_delong_ci95"):
            e[cik + "_per_seed"] = [r["detectors"][d][cik] for r in mains]
            e[cik + "_halfwidth_max"] = max((hi - lo) / 2 for lo, hi in e[cik + "_per_seed"])
        S["detectors"][d] = e
    for p in B.PRIMITIVES + ["all"]:
        rows = [r["sel"][p] for r in mains if "SEL" in r["sel"].get(p, {})]
        if not rows:
            S["sel"][p] = {"n_mean": 0}
            continue
        e = {"n_mean": mean([x["n"] for x in rows]), "n_seeds": len(rows)}
        for key in rows[0]:
            if key == "n" or key.endswith("_ci95"):
                continue
            vals = [x[key] for x in rows if key in x]
            e[key] = mean(vals); e[key + "_sd"] = sd(vals)
        for key in ("SEL_ci95", "SEL_res_D1_ci95", "SEL_res_D2_ci95", "SEL_res_D5_ci95", "SEL_res_D7_ci95"):
            e[key + "_per_seed"] = [x.get(key) for x in rows]
        S["sel"][p] = e
    for fam in ("P1", "P2", "P3"):
        rows = [l[fam] for l in loos if "D2" in l.get(fam, {})]
        if not rows:
            S["loo"][fam] = {"skipped": [l.get(fam) for l in loos]}
            continue
        e = {"n_seeds": len(rows), "n_pure": mean([x["n_pure"] for x in rows])}
        for key in rows[0]:
            if key == "n_pure":
                continue
            vals = [x[key] for x in rows if key in x]
            if vals and isinstance(vals[0], (int, float)):
                e[key] = mean(vals); e[key + "_sd"] = sd(vals); e[key + "_per_seed"] = vals
        S["loo"][fam] = e
    for rho, rows in prev.items():
        S["prevalence"][rho] = {"n_gamed_test": mean([x["n_gamed_test"] for x in rows]), "ceiling@0.01": mean([x["ceiling@0.01"] for x in rows]),
                                **{d: {k: mean([x[d][k] for x in rows]) for k in rows[0][d]} for d in DETS}}
    for d in DETS:
        S["shift"][d] = {side: {k: mean([s["detectors"][d][side][k] for s in shifts]) for k in shifts[0]["detectors"][d][side]} for side in ("A_to_B", "B_to_B")}
    S["shift"]["n_gamed_test_B"] = mean([s["n_gamed_test_B"] for s in shifts])
    return S


if __name__ == "__main__":
    main()
