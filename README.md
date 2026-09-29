# F7 ISO 20022 Purpose-Code Gaming - Verified Five-Page Release

This package contains the revised paper:

**Detecting Purpose-Code Gaming in ISO 20022 Payments: A Synthetic Data-Quality Benchmark**

## Paper files

- `F7_ISO20022_Purpose_Code_Gaming_Revised.pdf` - named submission version, 5 pages
- `F7_ISO20022_Purpose_Code_Gaming_Revised_Anonymous.pdf` - anonymous version, 5 pages
- Matching LaTeX sources are included beside the PDFs.

## Main verification results

- Both PDFs are 5 pages on US Letter paper in standard IEEE conference format.
- Both compile without overfull boxes, undefined references, or undefined control sequences.
- The anonymous PDF contains no author name or email and uses anonymous PDF metadata.
- Detector values printed in the paper match `results/verified_summary.json`.
- The exact alert-capacity tie test and XML structure tests pass.
- Internal prose-style risk is 1.23/10. This is a reproducible editorial heuristic, not a commercial AI-detector result and not a guarantee about any vendor detector.

See `verification/F7_VERIFICATION_REPORT.md` and `verification/package_verification.json` for details.

## Reproducing the benchmark

Requirements:

- Python 3.10 or later
- NumPy
- scikit-learn
- lxml

Typical commands:

```bash
python run_protocol.py --quick
python run_protocol.py --full
```

The benchmark uses synthetic data only. It does not model a named institution's production controls, estimate real-world loss, or establish that generated XML would be accepted by a particular payment scheme. XSD validation is optional when an external schema set is supplied.
