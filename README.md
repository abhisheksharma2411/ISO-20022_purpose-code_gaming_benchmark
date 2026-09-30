# Gaming ISO 20022 Payment Messages: An Adversarial Data-Quality Benchmark for Purpose Codes, Party Fields, and Message Paths

Benchmark, harness, results and manuscript for the paper. Public repository: <https://github.com/abhisheksharma2411/ISO-20022_purpose-code_gaming_benchmark>. Archived at Zenodo, concept DOI [10.5281/zenodo.23049366](https://doi.org/10.5281/zenodo.23049366). Licence: MIT. This is the
post-review revision of 29 September 2026 of the manuscript that was reviewed
at ICSISCET 2026 (not resubmitted there) under the title "Purpose-Code Gaming in ISO 20022 Payments: An
Adversarial Data-Quality Benchmark" (kept verbatim in `paper/as_reviewed/`).

## Layout

| Path | Contents |
|---|---|
| `iso20022_gaming_bench.py` | generator, evader, screening abstraction, features, detectors D0-D6, metrics |
| `run_protocol.py` | the full protocol (calibration, 3 main seeds, leave-one-family-out, eta sweep, ablations, calibration grid, XML corpus); writes `results/` and `latex/` |
| `scripts/diagnostics.py` | artefact audit and held-out-P1 inversion mechanism, seed 7 -> `results/diagnostics_seed7.json` |
| `scripts/fill_paper.py` | fills every `@@TOKEN@@` in `paper/draft_tokenised.tex` from `results/summary.json` and fails if any qualitative claim in the prose does not hold |
| `scripts/verify_claims.py` | re-derives the paper's numbers from the raw per-run files, independently of the summariser, and checks they appear in the manuscript |
| `scripts/check_prose_numbers.py` | every numeral in the filled manuscript is either a design constant already in the draft or a filled token |
| `scripts/make_paper.sh` | fill, build both variants, run all gates (numbers, claims, style, anonymity, placeholders) |
| `scripts/test_harness.py` | exact-capacity tie handling, out-of-fold history, XML well-formedness and element order |
| `paper/draft_tokenised.tex` | the manuscript source of truth (all result numbers are tokens) |
| `paper/F7_ISO20022_Gaming_Revision{,_Anonymous}.{tex,pdf}` | filled manuscript, named and anonymous |
| `results/` | raw per-run JSON (each records the git commit that produced it), `summary.json`, run logs, diagnostics |
| `verification/` | revision report and the response to the reviewers; August 2026 material under `archive-2026-08-16/` |

## Reproduce

Python 3.10+, `pip install -r requirements.txt` (numpy, scikit-learn, lxml), a TeX distribution with
IEEEtran and pgfplots, poppler (`pdfinfo`, `pdftotext`). With `uv`:

```bash
PY="uv run --quiet --with numpy --with scikit-learn --with lxml python"
$PY run_protocol.py --full            # ~18 min on a laptop; writes results/ and latex/
$PY scripts/diagnostics.py            # ~3 min; writes results/diagnostics_seed7.json
PY="$PY" scripts/make_paper.sh        # fills, builds, and runs every gate
$PY scripts/test_harness.py
```

The numbers in the manuscript were produced at commit `378369d`; every
result file carries the commit in its `config`. `run_protocol.py --quick`
runs the whole pipeline at small size in about 3 minutes (use `--out`/`--tex`
to keep it out of `results/`).

## What changed since the reviewed version

- Learned detectors are two-fold cross-fitted; the reviewed harness scored the
  supervised model on rows it had trained on. The pair-history feature C5 no
  longer uses the gaming label and is built from the other fold; D4 is
  standardised with the other fold's statistics.
- The generator's benign remittance text and party names have variable
  length and benign batches extend to the P3b cap. An artefact audit
  (`scripts/diagnostics.py`; pre-fix output kept as
  `results/diagnostics_seed7_before_generator_fix.json`) had shown that a
  one-line out-of-range rule recovered the entire 1% alert capacity.
- Two reference methods (LOF, logistic regression), average precision,
  precision at capacity, seed spread, DeLong and bootstrap intervals, a
  capacity-ceiling row, a scope comparison with adjacent benchmarks, eleven
  added references, and the mechanism behind the below-chance held-out score.
- Title and abstract scope: "message gaming" is the umbrella term;
  purpose-code gaming names the P2 case.

The benchmark uses synthetic data only. It does not model a named
institution's controls, estimate real-world loss, or establish that generated
XML would be accepted by a payment scheme. XSD validation is optional and is
not used as evidence.
