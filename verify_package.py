#!/usr/bin/env python3
"""Verify the packaged five-page F7 release."""
from __future__ import annotations

import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from lxml import etree

ROOT = Path(__file__).resolve().parent
NAMED_TEX = ROOT / "F7_ISO20022_Purpose_Code_Gaming_Revised.tex"
ANON_TEX = ROOT / "F7_ISO20022_Purpose_Code_Gaming_Revised_Anonymous.tex"
NAMED_PDF = ROOT / "F7_ISO20022_Purpose_Code_Gaming_Revised.pdf"
ANON_PDF = ROOT / "F7_ISO20022_Purpose_Code_Gaming_Revised_Anonymous.pdf"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def pdf_pages(path: Path) -> int:
    output = subprocess.check_output(["pdfinfo", str(path)], text=True)
    match = re.search(r"^Pages:\s+(\d+)$", output, re.M)
    if not match:
        raise RuntimeError(f"page count missing for {path}")
    return int(match.group(1))


def pdf_text(path: Path) -> str:
    return subprocess.check_output(["pdftotext", str(path), "-"], text=True)


def main() -> None:
    checks: dict[str, object] = {}
    tex = NAMED_TEX.read_text()
    anon_tex = ANON_TEX.read_text()
    summary = json.loads((ROOT / "results" / "verified_summary.json").read_text())
    bench = load_module(ROOT / "iso20022_gaming_bench.py", "f7_bench")
    style = load_module(ROOT / "style_risk_review.py", "f7_style")

    score = np.array([3, 3, 3, 2, 2, 1, 1, 1, 1, 0], dtype=float)
    for budget in (0.01, 0.1, 0.35, 0.5, 0.95):
        weights = bench.alert_weights(score, budget)
        assert math.isclose(float(weights.sum()), budget * len(score), abs_tol=1e-12)
    checks["exact_capacity_tie_test"] = "pass"

    messages = bench.generate(500, 0.15, 0.05, 7, 2, 0.18, "grey")
    for message_type in ("pain.001", "pacs.008"):
        message = next(item for item in messages if item.msg_type == message_type)
        if message_type == "pain.001":
            message.ultmt_dbtr_nm = "ULTIMATE DEBTOR TEST"
        xml = bench.to_xml(message)
        etree.fromstring(xml.encode())
        if message_type == "pain.001":
            assert "<UltmtDbtr>" in xml and "<UltmtCdtr>" not in xml
            assert xml.index("<Amt>") < xml.index("<UltmtDbtr>") < xml.index("<CdtrAgt>")
    checks["xml_well_formed_and_ultimate_debtor_order"] = "pass"

    expected = {
        name: (
            f"{row['auc']:.3f}",
            f"{row['tpr@0.01']:.3f}",
            f"{row['tpr@0.001']:.3f}",
        )
        for name, row in summary["detectors"].items()
    }
    for values in expected.values():
        for value in values:
            assert value in tex
    checks["paper_values_match_verified_summary"] = expected

    pages = {"named": pdf_pages(NAMED_PDF), "anonymous": pdf_pages(ANON_PDF)}
    assert pages == {"named": 5, "anonymous": 5}
    checks["page_count"] = pages

    anonymous_text = pdf_text(ANON_PDF).lower()
    assert "abhishek sharma" not in anonymous_text
    assert "abhishek.sharma@ieee.org" not in anonymous_text
    assert "\\anonymoustrue" in anon_tex
    metadata = subprocess.check_output(["pdfinfo", str(ANON_PDF)], text=True).lower()
    assert "author:          anonymous" in metadata
    checks["anonymous_scrub"] = "pass"

    style_result = style.analyse(NAMED_TEX)
    assert style_result["style_risk_score_out_of_10"] < 3.0
    checks["internal_style_risk"] = style_result

    output_path = ROOT / "verification" / "package_verification.json"
    output_path.write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
