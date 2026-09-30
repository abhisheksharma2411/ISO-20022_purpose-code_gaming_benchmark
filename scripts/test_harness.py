#!/usr/bin/env python3
"""Harness tests: frozen-threshold capacity, prior-only history, paired
originals, invariants, XSD validity, and the out-of-range regression check."""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import iso20022_gaming_bench as B
val = np.array([3, 3, 3, 2, 2, 1, 1, 1, 1, 0], dtype=float)
for q in (0.1, 0.35, 0.5):
    thr, frac = B.frozen_threshold(val, q)
    assert math.isclose(B.alert_weights_frozen(val, thr, frac).sum(), q * len(val), abs_tol=1e-9), q
print("OK frozen threshold alerts exactly q of the validation window")
B.PI_FLOOR, B.TEMP = 0.10, 0.10; B.calibrate(0.45, 0.15, 7, "grey", 0.6, n_probe=1000, verbose=False)
msgs = B.generate(6000, 0.15, 0.05, 7, 2, 0.18, "grey")
assert all(msgs[i].t == i for i in range(len(msgs))), "time order"
F = B.build_features(msgs)
# prior-only history: the first message of every pair has all-zero history features
first = {}
for i, m in enumerate(msgs):
    if m.pair_id not in first: first[m.pair_id] = i
assert all(np.all(F["H"][i] == 0) for i in first.values()), "history leaked into a pair's first message"
print("OK history features are prior-only")
assert all((m.orig is not None) == m.gamed for m in msgs) and F["has_orig"].sum() == sum(m.gamed for m in msgs)
assert all(not B.check_invariants(m) for m in msgs if m.gamed), "invariant violation"
print("OK every gamed record keeps an original and passes its invariants")
if os.path.isdir("xsd"):
    n, ok, errs = B.validate_corpus(msgs, "xsd", limit=300); assert ok == n, errs[:3]; print(f"OK XSD valid {ok}/{n}")
aud = B.artefact_audit(msgs[:6000], seed=7)
assert aud["share_benign_test_out_of_range"] < 0.02, aud   # exact zero is checked at full scale by fill_paper.py
print(f"OK artefact audit runs (gamed out of range {aud['share_gamed_test_out_of_range']:.3f} at this small size)")
tr, va, te = B.temporal_split(len(msgs)); assert tr.sum() + va.sum() + te.sum() == len(msgs) and not (tr & te).any()
print("OK temporal split is disjoint and ordered")
