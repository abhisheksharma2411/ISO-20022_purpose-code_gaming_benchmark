# F7 Verification and Revision Report

**Paper:** *Detecting Purpose-Code Gaming in ISO 20022 Payments: A Synthetic Data-Quality Benchmark*  
**Review date:** 16 August 2026  
**Final formats:** named and anonymous IEEE conference PDFs, LaTeX source, benchmark code, verified result files, and sample XML.

## 1. Final decision

The revised paper passes the release checks used for this review. The original package contained a six-page named PDF and a six-page anonymous PDF. The revised versions are **five pages each**, on US Letter paper in standard IEEE conference formatting. The reduction was achieved by rewriting and consolidating material rather than by shrinking margins or using an unusually small body font.

| Check | Final status |
|---|---:|
| Named PDF page count | 5 pages |
| Anonymous PDF page count | 5 pages |
| LaTeX build warnings / overfull boxes | None |
| Embedded fonts | Yes; Type 1 fonts |
| Anonymous author/details scrub | Pass |
| PDF preflight | Openable, unencrypted, text-based, 5 pages |
| Exact-capacity tie test | Pass |
| XML well-formedness and ultimate-debtor order | Pass |
| Paper values vs. verified result summary | Pass |
| End-to-end quick protocol smoke test | Pass |
| Internal prose-style risk | **1.23 / 10** |

The style score is an internal, reproducible prose heuristic, not a score from Turnitin, GPTZero, or another commercial detector. It is therefore evidence that the prose no longer shows strong formulaic patterns under the stated checks, but it cannot guarantee how every external detector will classify the paper.

## 2. Most important technical corrections

### 2.1 Exact alert capacity under tied detector scores

The earlier implementation used a quantile cutoff followed by `score >= threshold`. Several detector outputs are discrete, so a large tied group at the cutoff could cause the number of alerts to exceed the stated 1% or 0.1% capacity.

The revised implementation now:

1. selects every record strictly above the boundary;
2. assigns the boundary tie group a label-blind fractional alert weight; and
3. enforces the exact expected alert capacity.

This matters because recovery at a fixed operational capacity is a headline result. The main three-seed metrics were recomputed with the corrected rule. AUC-only sweeps and ablations were retained because the tie-handling change does not change detector scores or their ranking, and therefore cannot change ROC-AUC.

### 2.2 pain.001 ultimate-debtor serialization

The original pain.001 serializer wrote an ultimate debtor into an `UltmtCdtr` element. It now writes `UltmtDbtr` and places it before creditor-agent data in the transaction sequence used by the generator. The release tests XML well-formedness and element order. It does **not** claim production acceptance or XSD validity unless external schemas are supplied to the validation hook.

### 2.3 Method and result alignment

The paper and code now agree on the following points:

- `D4` is the sum of standardized `D1` and `D3` scores.
- The generalisation experiment is leave-one-**family**-out at `k = 1`, using pure-family records.
- Only the supervised detector is retrained in the held-out-family experiment.
- The unsupported aggregate `AUC_LOO` column was removed.
- The SEL figure reports three-seed means rather than a single seed.
- Alert recovery is described as an expectation under uniform, label-blind tie-breaking.
- Residual SEL for very small illicit baseline samples is explicitly qualified.

### 2.4 Claims narrowed to the available evidence

Several statements were rewritten so the paper does not imply more than the experiment establishes:

- XML is described as well-formed, with optional XSD validation when schemas are supplied; XSD validity is not treated as proof of settlement or business acceptance.
- The route-changing primitive is described as capability-dependent rather than something available to every corporate originator.
- Synthetic SEL is described as model-relative, not an estimate of real fraud, sanctions evasion, losses, or bank-control performance.
- CPMI requirements are described as harmonisation guidance rather than a regulatory mandate.
- The CBPR+ address transition is scoped to the official November 2026 requirement for town and country in designated fields and the removal of purely unstructured addresses.

## 3. Verified headline results

The main setting uses three deterministic seeds, with 200,000 synthetic records per seed.

| Detector | Mean AUC | TPR at exact 1% capacity | TPR at exact 0.1% capacity |
|---|---:|---:|---:|
| D0 | 0.497 | 0.009 | 0.001 |
| D1 | 0.750 | 0.105 | 0.020 |
| D2 | 0.918 | 0.201 | 0.020 |
| D3 | 0.752 | 0.040 | 0.007 |
| D4 | 0.774 | 0.099 | 0.018 |

The most important interpretation is retained: ranking quality can look reasonable while recovery at a constrained alert capacity remains low. The supervised detector is strongest in-distribution but is brittle on a withheld manipulation family; for P1, its matched in-distribution AUC of 0.815 falls to 0.366 when that family is excluded from training.

## 4. Source and citation verification

The time-sensitive ISO 20022 statements were checked against current official material during this review:

- Swift states that from 14 November 2026, town and country must be provided in designated fields at minimum for the covered CBPR+ parties and agents, and that unstructured addresses will no longer be supported.
- The February 2026 CPMI report describes the harmonised requirements as guidance, not regulatory requirements, and allows implementation through the end of 2027.
- Federal Reserve Financial Services discusses comparing stated purpose codes and transaction characteristics with historical payment patterns as a fraud-mitigation use case.
- Swift/PMPG material supports the paper's narrower claim that purpose and category-purpose information must be populated in the correct elements and may influence processing or monitoring.
- The full published titles for the Wang et al. and Busson et al. references were restored in the bibliography.

## 5. Language and authorship-style review

The final prose was reviewed for clarity, sentence rhythm, repeated openings, formulaic signposting, overstatement, and unnecessary abstraction. The final internal style measurements are:

- 172 analysed sentences;
- mean sentence length: 17.66 words;
- sentence-length coefficient of variation: 0.524;
- short-sentence share: 0.233;
- long-sentence share: 0.023;
- repeated-opening share: 0.035;
- formulaic phrase `this paper`: 2 occurrences;
- absolute claims using `never` or `proves`: 0;
- overall internal style-risk score: **1.23 / 10**.

The language is now direct and appropriately cautious. It does not rely on deliberate misspellings, awkward grammar, fake anecdotes, or other artificial attempts to manipulate detectors.

## 6. Reviewer-style scorecard

These scores are qualitative editorial judgments, not venue decisions.

| Area | Score | Assessment |
|---|---:|---|
| Problem relevance | 9.0 / 10 | Timely operational question with a clear payments-data angle. |
| Novelty | 8.1 / 10 | Strongest in the gaming taxonomy, exact-capacity evaluation, and SEL framing; the detectors themselves are intentionally conventional. |
| Technical consistency | 9.0 / 10 | Paper, code, tables, and stated evaluation protocol now align. |
| Reproducibility | 8.8 / 10 | Deterministic seeds, raw JSON, code, LaTeX fragments, XML samples, and verification scripts are included. |
| Claims discipline | 9.2 / 10 | Synthetic and model-relative limitations are now explicit. |
| Naturalness and readability | 9.0 / 10 | Clearer flow, fewer mechanical transitions, and better variation without loss of precision. |
| Submission readiness | 8.8 / 10 | Technically ready as a five-page IEEE-style paper, subject to the target venue's anonymity, reference, and generative-AI disclosure rules. |

## 7. Remaining limitations that should stay visible

1. The experiment is synthetic. Code distributions, defect rates, route options, batching, illicit prevalence, and screening weights are assumptions.
2. The incumbent screening abstraction is transparent and reproducible but is not a reconstruction of any bank's production controls.
3. No production payment, customer, employer, or institution-specific alert data is used.
4. The generator and detectors share a feature vocabulary, which may reward recognition of generator artefacts.
5. External XSDs were not supplied for the final release check. The included test verifies well-formedness and the corrected ultimate-debtor placement, not full scheme or business-rule conformance.
6. A stronger follow-up would recalibrate the abstraction against anonymised institution-specific outcomes and test path-aware features without exporting raw messages.

## 8. Release checks executed

- Two-pass `pdflatex` build for named and anonymous sources.
- PDF render and visual inspection of all five pages.
- Original-to-revised render comparison (six pages reduced to five).
- PDF preflight and font-embedding inspection.
- Anonymous text scrub for author name, email, and affiliation.
- Exact-capacity unit test, XML structure test, and paper/result consistency test.
- Python compilation check and an isolated end-to-end quick protocol run.
- Internal natural-language style audit on both source variants.

## 9. Authorship record and venue compliance

Retain the original package, this revised package, dated notes, result JSON, scripts, build logs, and any later reviewer responses. Do not fabricate earlier drafts or research records. Use the named or anonymous version according to the venue's review policy, and follow the venue's current generative-AI disclosure and authorship rules exactly.

## 10. Release file hashes

The package includes `SHA256SUMS.txt` for the final PDFs, sources, and principal result summaries.
