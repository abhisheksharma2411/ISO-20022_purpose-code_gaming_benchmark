#!/usr/bin/env python3
"""Sensitivity of attempt-level SEL to cross-child dependence (seed 7 test
window). Main form: name leg and residual floor once per attempt, score leg
once per child. Independent extreme: every leg drawn independently per child,
pi_att = 1 - (1 - pi_msg)^n. Writes results/attempt_sensitivity_seed7.json."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import iso20022_gaming_bench as B

def pi_indep(m):
    return 1 - (1 - B.screening_prob(m)) ** max(1, m.n_splits)

B.PI_FLOOR, B.TEMP = 0.10, 0.10; B.P_NAME, B.TAU = 0.90, 0.55
B.calibrate(0.45, 0.15, 7, "grey", 0.6, n_probe=4000, verbose=False)
msgs = B.generate(200_000, 0.15, 0.05, 7, 2, 0.18, "grey")
test = [m for m in msgs if m.t >= 160_000 and m.gamed]
out = {}
for p in B.PRIMITIVES + ["all"]:
    rows = [m for m in test if p == "all" or p in m.primitives]
    if len(rows) < 10: continue
    s = lambda f: sum(1 - f(m) for m in rows) / max(1e-9, sum(1 - f(m.orig) for m in rows))
    out[p] = {"n": len(rows), "SEL_message": s(B.screening_prob), "SEL_attempt_main": s(B.screening_prob_attempt), "SEL_attempt_independent": s(pi_indep)}
json.dump(out, open("results/attempt_sensitivity_seed7.json", "w"), indent=1)
for p, v in out.items(): print(p, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items()})
