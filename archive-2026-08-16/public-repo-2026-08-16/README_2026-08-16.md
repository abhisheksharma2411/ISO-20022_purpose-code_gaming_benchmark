# Detecting Purpose-Code Gaming in ISO 20022 Payments

Artifact for the CEEE 2026 submission *Detecting Purpose-Code Gaming in
ISO 20022 Payments: A Data-Quality Benchmark and Adversarial Evaluation*.

**Everything in this repository is synthetic.** No real payment message,
customer record, alert outcome or institution-specific parameter is used
anywhere. The risk weights are illustrative constants chosen for the study and
must not be represented as any institution's. The generated corpora must not
be represented as real payment traffic.

## Contents

| File | What it is |
|---|---|
| `iso20022_gaming_bench.py` | Generator, cost-bounded evader (P1a–P3c), screening abstraction π, detectors D0–D4, SEL/SEL_res, pain.001/pacs.008 XML |
| `run_protocol.py` | Runs the whole Section V protocol; writes `results/*.json` and `latex/*` |
| `make_anon.py` | Derives the double-blind `.tex` from the named one; never hand-edit the ANON file |
| `paper_F7_IEEEtran.tex` | The paper, 6 pages |
| `paper_F7_IEEEtran_ANON.tex` | Double-blind version, PDF metadata stripped |
| `F7_REVIEW_AND_HANDOFF.md` | Review, positioning and experiment checklist |
| `results/` | Raw measured output, one JSON per phase |
| `latex/` | Emitted table/figure fragments and `SUMMARY.md` |

## Reproducing

```bash
python3 -m venv .venv && ./.venv/bin/pip install numpy scikit-learn lxml
./.venv/bin/python run_protocol.py --quick            # ~3 min sanity check
./.venv/bin/python run_protocol.py --full --xsd-dir ./xsd
```

The results in the paper are from `--full` (n=200,000 per run, seeds 7/8/9,
η=0.15, ρ=0.05, k=2, grey-box, λ=0.18, TEMP=0.10, target π₀=0.45). The run is
deterministic: the same configuration and seed reproduce the same corpus
byte-for-byte. Measured wall time was 313 s on an Apple silicon laptop.

### Schemas

`xsd/` is **not committed** — the ISO 20022 schemas are not redistributable.
Download them from iso20022.org before running with `--xsd-dir`:

```bash
mkdir -p xsd
curl -o xsd/pacs.008.001.08.xsd \
  https://www.iso20022.org/sites/default/files/documents/messages/pacs/schemas/pacs.008.001.08.xsd
curl -o /tmp/pain.zip \
  https://www.iso20022.org/sites/default/files/documents/messages/pain/schemas/pain.001.001.09.zip
unzip -j /tmp/pain.zip -d xsd
```

Verified against (SHA-256):

```
de038b373e47b0077b1832ddd81f4b2f1eb25d35721f62da1e38b7f5a09fda24  pain.001.001.09.xsd
cf048155f70cacd03f1f1dfadf66cba8752be93c249c267351782fd6adb023f7  pacs.008.001.08.xsd
```

20,000 messages from the seed-9 corpus, covering all eleven primitives and
every accidental-defect mode, validate without error against both schemas
(`results/phase6_xsd_extended.json`).

## Building the paper

```bash
pdflatex paper_F7_IEEEtran.tex   # ×3; needs IEEEtran.cls and pgfplots
python3 make_anon.py             # regenerate the double-blind version
pdflatex paper_F7_IEEEtran_ANON.tex  # ×3
pdftotext paper_F7_IEEEtran_ANON.pdf - | grep -i sharma   # must return nothing
```

Both versions are exactly 6 pages with no overfull boxes.

## Two known generator artifacts

Reported in the paper (§VII-C) rather than silently fixed, because fixing them
changes the data-generating process and that is the author's call:

1. **The benign stream never batches.** `n_splits = 1` for every un-manipulated
   message while P3b sets 3–7, so `n_splits > 1` implies manipulation with
   precision 1.000 and covers 59.9% of manipulated messages. D2 falls from
   0.997 to 0.901 when the feature is withheld. Real pain.001 files carry
   multi-transaction batches routinely.
2. **Leave-one-primitive-family-out is contaminated at k=2.** A message can
   carry two families, so 99.9% of held-out P1 messages, 77.5% of P3 and 64.1%
   of P2 also carry a primitive the detector trained on. AUC_LOO is an
   optimistic bound; a clean figure needs k=1.

## Licence

Code MIT; generated corpora CC BY 4.0. The ISO 20022 schemas are not covered
by either and are not distributed here.
