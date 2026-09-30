# Response to the second-round review (30 September 2026)

The review asked for a revision whose bottleneck is experimental and domain
validity rather than language. We rebuilt the harness and the paper around
the nine points it listed. Every number in the revised paper is regenerated
from the new protocol; none is carried over.

## 1. Page limit
The paper is five IEEEtran pages with no change to font, margins or table
text. The scope table, the full ablations, the calibration grid, the
artefact-range audit, hyperparameters, per-primitive tables, the ethics
discussion and the rater questionnaire moved to a supplement built from the
same result files. Related work and the gap are one section; discussion,
limitations and conclusion are one section; the abstract is about 200 words.

## 2. Factual and internal-consistency errors
- Swift's 27 August 2026 controlled extension of Standards Release 2026 is
  cited; November 2026 is described as the deferred milestone.
- Equation (2) and the code now agree: splitting dilutes only the amount term,
  one child at a time. P3b was redesigned as decomposition into children that
  sum to the amount, with per-message and attempt-level alerting both
  evaluated (Section IV-B, Fig. 1).
- Label-free ranges are stated for the named detectors; "benign-only" became
  "more common among benign training records", with the measured rates; the
  P3 claim is the narrower one the review proposed.
- The bibliography is in citation order.

## 3. Temporal, pair-aware protocol
Pairs have latent behaviour (purpose profile, preferred path, batching habit,
party-chain pattern, amount scale, volume weight); messages are emitted in
time order. Each run trains on the earliest 60%, freezes alert thresholds on
the next 20% and scores the latest 20%. History features use only strictly
earlier messages of the pair. Uncertainty is a pair-clustered bootstrap; the
main table averages ten seeds.

## 4. Paired counterfactual SEL
Every gamed record keeps its original, scored by the same detector with the
same prior history. SEL and residual SEL are the ratio-of-sums form the review
proposed; no separate no-edit control group is used.

## 5. Formal test of the central finding
Contradiction labels, the outcome, the competing explanations and the tests
were pre-registered in `analysis/` before the first full-scale run (the commit
precedes every result file). The test uses exact permutation over all
relabellings, variance explained, and leave-one-primitive-out error, for the
supervised model (no hand-built check in its features) and the label-free LOF.

## 6. Domain validity
Admissibility is checked per record; invariants are stated per primitive and
checked on every gamed record (0 violations). P3a is a route realisation of
the same single payment for an actor with route choice; P3c's invariant is
stated explicitly (economic parties, amount and currency unchanged; the
represented chain changes). Every instance in the seed-7 test window, every
gamed record and every original was validated against the official
pain.001.001.09 and pacs.008.001.08 XSDs (100% valid). The expert rating was
not performed: the questionnaire and the blinded procedure are in the
supplement and `analysis/`, and the pre-registered test reruns unchanged on
raters' labels.

## 7. Robustness
Prevalence 0.5%, 1% and 5% (seeds 7-9) and an independently parameterised
generator B, with detectors fitted and thresholds frozen on A and scored on
B's test window, are in the results and the supplement.

## 8. History-aware positive control
D7 uses only prior pair behaviour (purpose, path, split-count, party-chain and
amount deviations). Its P3 result under the temporal protocol is reported.

## 9. Artifact
One command regenerates every table and figure; one command validates XSDs
and invariants; result files carry the commit; the harness test suite
includes the out-of-range regression check, the prior-only history check and
the frozen-threshold capacity check. The anonymous variant carries no
identifying information; the named variant cites the repository and DOI.
