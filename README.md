# Gaming ISO 20022 Payment Messages: A Temporal Adversarial Benchmark for Purpose Codes, Party Fields, and Message Paths

Benchmark, harness, results and manuscript. Public repository:
<https://github.com/abhisheksharma2411/ISO-20022_purpose-code_gaming_benchmark>.
Archived at Zenodo, concept DOI [10.5281/zenodo.23049366](https://doi.org/10.5281/zenodo.23049366). Licence: MIT.

Version 3 (30 September 2026) replaces the cross-fitted protocol of version 2
with a temporal one and answers the second-round review point by point
(`verification/RESPONSE_ROUND2.md`).

## What the harness does

- **Generator** (`iso20022_gaming_bench.py`): debtor-creditor pairs with latent
  behaviour emit pain.001 and pacs.008 records in time order; a fraction gets
  one ordinary defect; illicit records are edited by a cost-bounded evader that
  keeps the unmanipulated original. Every record serialises to schema-valid XML.
- **Screening abstraction**: path-dependent name coverage, a score leg whose
  amount term alone is diluted by splitting, per-message and attempt-level forms.
- **Protocol** (`run_protocol.py`): earliest 60% trains, next 20% freezes alert
  thresholds, latest 20% is scored; history features are strictly prior;
  pair-clustered bootstrap; ten seeds; paired SEL; leave-one-family-out;
  defect-rate sweep; ablations; prevalence sensitivity; generator shift A->B;
  XSD validation and invariants; artefact audit.
- **Pre-registered analysis** (`analysis/`): contradiction labels, primary
  outcome and tests fixed before the first full-scale run;
  `scripts/contradiction_test.py` runs exact permutation tests.

## Reproduce

```bash
PY="uv run --quiet --with numpy --with scipy --with scikit-learn --with lxml python"
scripts/fetch_xsd.sh                    # official schemas into xsd/ (not redistributed)
$PY run_protocol.py --full              # ~1 h; results/*.json, results/summary.json
PY="$PY" scripts/make_paper.sh          # contradiction test, fill, build, every gate
$PY scripts/validate_release.py         # XSD + invariants, one command
$PY scripts/test_harness.py
```

`run_protocol.py --quick --out /tmp/q` exercises every phase in about two
minutes. Every result file records the git commit that produced it.

## Layout

| Path | Contents |
|---|---|
| `paper/draft_tokenised.tex`, `paper/supplement_tokenised.tex` | manuscript sources; every result number is a token filled from `results/summary.json` |
| `paper/F7_ISO20022_Gaming_v3{,_Anonymous}.{tex,pdf}` and `_Supplement` | filled paper and supplement, named and anonymous |
| `scripts/` | fill, verify from raw runs, prose-number check, bibliography order, build, gates, harness tests, validation, diagnostics, contradiction test |
| `analysis/` | pre-registration, primitive labels with rationale, rater questionnaire |
| `results/` | v3 results; v2 under `archive-v2-2026-09-30/`; August material under `archive-2026-08-16/` |
| `verification/` | revision reports and responses to reviewers |

Synthetic data only. The screening abstraction is not any institution's
controls; XSD validity is not scheme or business acceptance.
