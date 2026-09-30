#!/usr/bin/env python3
"""Pre-registered test: does per-primitive recovery at the frozen 1% threshold
follow the action family or the contradiction label? Exact permutation tests
over all relabellings, variance explained, and leave-one-primitive-out error.

Usage: contradiction_test.py <repo> [<results-dir>]   -> <results-dir>/contradiction_test.json
"""
import glob, itertools, json, os, sys
import numpy as np

repo = sys.argv[1]
RES = sys.argv[2] if len(sys.argv) > 2 else os.path.join(repo, "results")
S = json.load(open(os.path.join(RES, "summary.json")))
L = json.load(open(os.path.join(repo, "analysis", "primitive_labels.json")))["labels"]
sys.path.insert(0, repo)
import iso20022_gaming_bench as B

prims = B.PRIMITIVES
contra = np.array([L[p]["contradiction"] for p in prims])
fam = np.array([{"P1": 0, "P2": 1, "P3": 2}[L[p]["family"]] for p in prims])
cost = np.array([B.PRIM_COST[p] for p in prims])
freq = np.array([S["primitive_counts"][p] for p in prims], float)
capab = np.array([1 if p == "P3a" else 0 for p in prims])
mains = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(RES, "phase1_main_seed*.json")))]


def r2(y, g):
    mu = y.mean(); sst = ((y - mu) ** 2).sum()
    ssw = sum(((y[g == k] - y[g == k].mean()) ** 2).sum() for k in np.unique(g))
    return 1 - ssw / sst if sst > 0 else 0.0


def loo_mae(y, g):
    err = []
    for i in range(len(y)):
        others = np.array([j for j in range(len(y)) if j != i and g[j] == g[i]])
        pred = y[others].mean() if len(others) else np.delete(y, i).mean()
        err.append(abs(y[i] - pred))
    return float(np.mean(err))


def exact_binary(y, lab):
    obs_r2 = r2(y, lab); obs_diff = y[lab == 1].mean() - y[lab == 0].mean()
    n1 = int(lab.sum()); cnt_r2 = cnt_diff = tot = 0
    for pos in itertools.combinations(range(len(y)), n1):
        g = np.zeros(len(y), int); g[list(pos)] = 1
        tot += 1
        if r2(y, g) >= obs_r2 - 1e-12: cnt_r2 += 1
        if abs(y[g == 1].mean() - y[g == 0].mean()) >= abs(obs_diff) - 1e-12: cnt_diff += 1
    return {"r2": obs_r2, "p_r2": cnt_r2 / tot, "mean_diff": obs_diff, "p_mean_diff": cnt_diff / tot, "assignments": tot,
            "mean_1": float(y[lab == 1].mean()), "mean_0": float(y[lab == 0].mean()), "loo_mae": loo_mae(y, lab)}


def exact_family(y, lab):
    obs = r2(y, lab); cnt = tot = 0
    idx = list(range(len(y)))
    for a in itertools.combinations(idx, 4):
        rest = [i for i in idx if i not in a]
        for b in itertools.combinations(rest, 4):
            g = np.full(len(y), 2); g[list(a)] = 0; g[list(b)] = 1
            tot += 1
            if r2(y, g) >= obs - 1e-12: cnt += 1
    return {"r2": obs, "p_r2": cnt / tot, "assignments": tot,
            "means": {f: float(y[lab == k].mean()) for f, k in (("P1", 0), ("P2", 1), ("P3", 2))}, "loo_mae": loo_mae(y, lab)}


def spearman_perm(y, x, n_perm=50000, seed=0):
    from scipy.stats import spearmanr
    rng = np.random.default_rng(seed)
    obs = spearmanr(y, x).correlation
    cnt = sum(abs(spearmanr(y, rng.permutation(x)).correlation) >= abs(obs) - 1e-12 for _ in range(n_perm))
    return {"rho": float(obs), "p": (cnt + 1) / (n_perm + 1)}


# Exploratory (not pre-specified): does the tested detector observe the evidence
# source the primitive modifies? 1 = current-message content (P1, P2);
# 0 = route, attempt aggregation or party chain (P3a, P3b, P3c).
evsrc = np.array([0 if p.startswith("P3") else 1 for p in prims])
out = {"labels": {p: int(L[p]["contradiction"]) for p in prims}, "evidence_source_labels": {p: int(v) for p, v in zip(prims, evsrc)}, "detectors": {}}
for d in ("D2", "D5", "D1", "D7"):
    y = np.array([S["sel"][p][f"detect_rate_{d}"] for p in prims])
    per_seed = np.array([[m["sel"][p].get(f"detect_rate_{d}", np.nan) for p in prims] for m in mains])
    row = {"recovery_by_primitive": {p: float(v) for p, v in zip(prims, y)},
           "contradiction": exact_binary(y, contra), "family": exact_family(y, fam),
           "cost": spearman_perm(y, cost), "frequency": spearman_perm(y, freq),
           "capability_r2": r2(y, capab),
           "evidence_source_exploratory": exact_binary(y, evsrc),
           "baseline_loo_mae": float(np.mean([abs(y[i] - np.delete(y, i).mean()) for i in range(len(y))])),
           "per_seed_r2_contradiction": [r2(s, contra) for s in per_seed if not np.isnan(s).any()],
           "per_seed_r2_family": [r2(s, fam) for s in per_seed if not np.isnan(s).any()]}
    for k in ("per_seed_r2_contradiction", "per_seed_r2_family"):
        row[k + "_mean"] = float(np.mean(row[k])) if row[k] else float("nan")
        row[k + "_sd"] = float(np.std(row[k], ddof=1)) if len(row[k]) > 1 else 0.0
    out["detectors"][d] = row
    print(f"{d}: contradiction R2={row['contradiction']['r2']:.3f} (p={row['contradiction']['p_r2']:.4f}, "
          f"means {row['contradiction']['mean_1']:.3f} vs {row['contradiction']['mean_0']:.3f}) | "
          f"family R2={row['family']['r2']:.3f} (p={row['family']['p_r2']:.4f}) | cost rho={row['cost']['rho']:.2f} p={row['cost']['p']:.3f} | "
          f"freq rho={row['frequency']['rho']:.2f} p={row['frequency']['p']:.3f} | LOO MAE contra {row['contradiction']['loo_mae']:.3f} fam {row['family']['loo_mae']:.3f} base {row['baseline_loo_mae']:.3f}")
json.dump(out, open(os.path.join(RES, "contradiction_test.json"), "w"), indent=1)
print("->", os.path.join(RES, "contradiction_test.json"))
