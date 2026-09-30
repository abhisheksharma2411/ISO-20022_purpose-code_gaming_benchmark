#!/usr/bin/env python3
"""Validate EVERY generated record and every counterfactual original of the
ten main runs against the official XSDs, and check every gamed record's
invariants. Regenerates each seed's corpus with the main-run calibration
(deterministic). One process per seed. Writes results/validity_all_runs.json."""
import json, os, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import iso20022_gaming_bench as B

N, ETA, RHO, K, LAM, PI0, SHARE = 200_000, 0.15, 0.05, 2, 0.18, 0.45, 0.6
XSD = "xsd"


def one(seed):
    from lxml import etree
    schemas = {k: etree.XMLSchema(etree.parse(os.path.join(XSD, f))) for k, f in
               (("pain.001", "pain.001.001.09.xsd"), ("pacs.008", "pacs.008.001.08.xsd"))}
    B.PI_FLOOR, B.TEMP = 0.10, 0.10; B.P_NAME, B.TAU = 0.90, 0.55
    B.calibrate(PI0, ETA, seed, "grey", SHARE, n_probe=4000, verbose=False)
    msgs = B.generate(N, ETA, RHO, seed, K, LAM, "grey")
    checked = valid = originals = inv_viol = gamed = 0
    errs = []
    for m in msgs:
        for rec, is_orig in ((m, False), (m.orig, True)):
            if rec is None:
                continue
            checked += 1; originals += is_orig
            try:
                schemas[rec.msg_type].assertValid(etree.fromstring(B.to_xml(rec).encode())); valid += 1
            except Exception as e:      # noqa: BLE001
                if len(errs) < 5: errs.append(f"{rec.msg_id} {list(m.primitives)} {str(e)[:120]}")
        if m.gamed:
            gamed += 1
            inv_viol += len(B.check_invariants(m))
    return {"seed": seed, "records": N, "originals": originals, "xsd_checked": checked, "xsd_valid": valid,
            "gamed": gamed, "invariant_violations": inv_viol, "first_errors": errs,
            "solved_P_NAME": B.P_NAME, "solved_TAU": B.TAU}


if __name__ == "__main__":
    t = time.time()
    seeds = list(range(7, 17))
    with Pool(min(len(seeds), os.cpu_count() or 2)) as p:
        rows = p.map(one, seeds)
    out = {"seeds": seeds, "per_seed": rows,
           "xsd_checked": sum(r["xsd_checked"] for r in rows), "xsd_valid": sum(r["xsd_valid"] for r in rows),
           "records": sum(r["records"] for r in rows), "originals": sum(r["originals"] for r in rows),
           "gamed": sum(r["gamed"] for r in rows), "invariant_violations": sum(r["invariant_violations"] for r in rows),
           "elapsed_s": time.time() - t}
    json.dump(out, open("results/validity_all_runs.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "per_seed"}, indent=1))
