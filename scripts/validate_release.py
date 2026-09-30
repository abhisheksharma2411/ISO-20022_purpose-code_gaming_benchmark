#!/usr/bin/env python3
"""One command: XSD-validate every message of a seed-7 corpus (test window,
gamed records, originals) and check every primitive's invariants.
Usage: validate_release.py [--n 200000] [--seed 7] [--xsd-dir xsd]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import iso20022_gaming_bench as B
import run_protocol as P
ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=200_000); ap.add_argument("--seed", type=int, default=7); ap.add_argument("--xsd-dir", default="xsd")
a = ap.parse_args()
B.PI_FLOOR, B.TEMP = 0.10, 0.10; B.calibrate(0.45, 0.15, a.seed, "grey", 0.6, n_probe=4000, verbose=False)
msgs = B.generate(a.n, 0.15, 0.05, a.seed, 2, 0.18, "grey")
v = P.validate_all(msgs, a.xsd_dir, a.n)
print(json.dumps({"xsd_valid": v["xsd"]["valid"], "xsd_checked": v["xsd"]["checked"], "invariant_violations": v["invariants"]["violations_total"], "first_errors": v["xsd"]["first_errors"]}, indent=1))
sys.exit(0 if v["xsd"]["valid"] == v["xsd"]["checked"] and v["invariants"]["violations_total"] == 0 else 1)
