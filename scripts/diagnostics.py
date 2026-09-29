#!/usr/bin/env python3
"""Two diagnostics behind statements in the Results section, seed 7.

1. Artefact audit of the reference method D5 (LOF) and the other detectors:
   what share of each detector's 1%-capacity alert mass falls on records whose
   remittance length or split count lies outside the range that benign
   synthetic traffic produces, and how a trivial out-of-range rule performs.
2. Mechanism of the below-chance held-out P1 score of the supervised model:
   with P1 withheld, an absent ultimate debtor occurs only in benign training
   rows, so the model learns it as benign evidence.

Writes results/diagnostics_seed7.json. Runs from the repository root.
"""
import json, os, sys
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import iso20022_gaming_bench as B
from sklearn.metrics import roc_auc_score

CFG = dict(n=200_000, eta=0.15, rho=0.05, seed=7, k=2, lam=0.18, temp=0.10,
           pi_floor=0.10, target_pi0=0.45, name_share=0.6)
out = {"config": CFG}

def setup():
    B.PI_FLOOR = CFG["pi_floor"]; B.TEMP = CFG["temp"]; B.P_NAME, B.TAU = 0.90, 0.55
    B.calibrate_p_name(CFG["target_pi0"], CFG["eta"], CFG["seed"], "grey",
                       name_share=CFG["name_share"], n_probe=4000, verbose=False)

# ---- 1. artefact audit at the main setting --------------------------------
setup()
msgs = B.generate(CFG["n"], CFG["eta"], CFG["rho"], CFG["seed"], CFG["k"], CFG["lam"], "grey")
sc, y = B.detector_scores(msgs, seed=CFG["seed"], extra=True)
benign = y == 0
len_rmt = np.array([len(m.rmt_ustrd) for m in msgs])
splits = np.array([m.n_splits for m in msgs])
ben_lens = sorted(set(len_rmt[benign].tolist()))
max_ben_split = int(splits[benign].max())
out_len = ~np.isin(len_rmt, ben_lens)
out_split = splits > max_ben_split
art = out_len | out_split
c4 = np.array([m.purpose == "SALA" and any(w in m.rmt_ustrd for w in ("GOODS", "INVOICE", "SHIPMENT")) for m in msgs])
a = {"benign_remittance_lengths": ben_lens, "max_benign_splits": max_ben_split,
     "share_gamed_out_of_range": float(art[y == 1].mean()),
     "share_benign_out_of_range": float(art[benign].mean()),
     "share_gamed_out_of_range_length": float(out_len[y == 1].mean()),
     "share_gamed_out_of_range_splits": float(out_split[y == 1].mean()),
     "alert_mass_on_out_of_range": {}, "alert_precision": {}}
for d in ("D1", "D2", "D4", "D5", "D6"):
    w = B.alert_weights(sc[d], 0.01)
    a["alert_mass_on_out_of_range"][d] = float((w * art).sum() / w.sum())
    a["alert_precision"][d] = float((w * y).sum() / w.sum())
rule = art.astype(float) + 0.5 * c4.astype(float)
a["out_of_range_rule"] = {"auc": float(roc_auc_score(y, rule)),
                          "rec@0.01": float(B.tpr_at_budget(rule, y, 0.01)),
                          "rec@0.001": float(B.tpr_at_budget(rule, y, 0.001)),
                          "benign_alerts_per_M@0.01": float(B.alerts_per_million_benign(rule, y, 0.01))}
mask = ~art
a["in_range_subset"] = {"n_gamed": int((y[mask] == 1).sum()), "n_benign": int((y[mask] == 0).sum()),
                        "auc": {d: float(roc_auc_score(y[mask], sc[d][mask])) for d in ("D1", "D2", "D4", "D5", "D6")},
                        "rec@0.01": {d: float(B.tpr_at_budget(sc[d][mask], y[mask], 0.01)) for d in ("D1", "D2", "D4", "D5", "D6")}}
# which primitives sit in the out-of-range set
prim_counts = Counter(p for i, m in enumerate(msgs) if art[i] for p in m.primitives)
tot = Counter(p for m in msgs for p in m.primitives)
a["out_of_range_share_by_primitive"] = {p: prim_counts[p] / tot[p] for p in B.PRIMITIVES}
out["artefact_audit"] = a
del msgs, sc

# ---- 2. held-out P1 inversion mechanism (k=1, pure families, as in LOO) ----
setup()
n2 = CFG["n"] // 2
msgs = B.generate(n2, CFG["eta"], CFG["rho"], CFG["seed"], 1, CFG["lam"], "grey")
gamed = np.array([m.gamed for m in msgs])
fam = [set(B.FAMILY[p] for p in m.primitives) for m in msgs]
pure_p1 = np.array([m.gamed and f == {"P1"} for m, f in zip(msgs, fam)])
any_p1 = np.array(["P1" in f for f in fam])
held, y = B.detector_scores(msgs, seed=CFG["seed"], train_mask=~any_p1)
keep = (~gamed) | pure_p1
ult = np.array([m.ultmt_dbtr_nm is None for m in msgs])
tr = ~any_p1
m2 = {"n": n2, "heldout_P1_auc_D2": float(roc_auc_score(y[keep], held["D2"][keep])),
      "heldout_P1_auc_D6": float(roc_auc_score(y[keep], held["D6"][keep])) if "D6" in held else None,
      "train_P_gamed_given_ultimate_absent": float(y[tr & ult].mean()),
      "train_P_gamed_given_ultimate_present": float(y[tr & ~ult].mean()),
      "benign_share_ultimate_absent": float(ult[~gamed].mean()),
      "median_D2_benign_ultimate_present": float(np.median(held["D2"][(~gamed) & ~ult])),
      "median_D2_benign_ultimate_absent": float(np.median(held["D2"][(~gamed) & ult])),
      "per_primitive": {}}
for prim in ("P1a", "P1b", "P1c", "P1d"):
    mk = np.array([m.gamed and m.primitives == (prim,) for m in msgs])
    if mk.sum() >= 30:
        sel = (~gamed) | mk
        m2["per_primitive"][prim] = {"n": int(mk.sum()),
                                     "heldout_auc_vs_benign_D2": float(roc_auc_score(y[sel], held["D2"][sel])),
                                     "ultimate_absent_share": float(ult[mk].mean())}
    else:
        m2["per_primitive"][prim] = {"n": int(mk.sum()), "note": "too few pure selections"}
out["p1_inversion"] = m2
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/diagnostics_seed7.json", "w"), indent=2)
print(json.dumps(out, indent=1)[:6000])
