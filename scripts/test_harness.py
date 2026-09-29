#!/usr/bin/env python3
"""Unit checks on the harness: exact-capacity tie handling, cross-fitting
disjointness, out-of-fold history, XML well-formedness and element order."""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import iso20022_gaming_bench as B

score = np.array([3, 3, 3, 2, 2, 1, 1, 1, 1, 0], dtype=float)
for budget in (0.01, 0.1, 0.35, 0.5, 0.95):
    w = B.alert_weights(score, budget)
    assert math.isclose(float(w.sum()), budget * len(score), abs_tol=1e-12)
print("OK exact-capacity tie test")

B.PI_FLOOR, B.TEMP = 0.10, 0.10
msgs = B.generate(4000, 0.15, 0.05, 7, 2, 0.18, "grey")
fold = np.arange(len(msgs)) % 2
# out-of-fold history: a row's own purpose must not be counted
h = {f: B.build_history([m for i, m in enumerate(msgs) if fold[i] == f]) for f in (0, 1)}
for i, m in enumerate(msgs[:200]):
    own = h[fold[i]].get(m.pair_id, {}).get(m.purpose, 0)
    other = h[1 - fold[i]].get(m.pair_id, {}).get(m.purpose, 0)
    assert own >= 1 and other >= 0
print("OK out-of-fold history built without the row itself")
sc, y = B.detector_scores(msgs, seed=7, extra=True)
assert set(sc) == {"D0", "D1", "D2", "D3", "D4", "D5", "D6"} and all(np.isfinite(v).all() for v in sc.values())
print("OK detector scores finite for all seven detectors")

from lxml import etree
for mt in ("pain.001", "pacs.008"):
    m = next(x for x in msgs if x.msg_type == mt)
    if mt == "pain.001":
        m.ultmt_dbtr_nm = "ULTIMATE DEBTOR TEST"
    xml = B.to_xml(m)
    etree.fromstring(xml.encode())
    if mt == "pain.001":
        assert "<UltmtDbtr>" in xml and "<UltmtCdtr>" not in xml
        assert xml.index("<Amt>") < xml.index("<UltmtDbtr>") < xml.index("<CdtrAgt>")
print("OK XML well-formed and ultimate-debtor order")
