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

---

# Addendum: third-round comments (30 September 2026, v3.0.1)

| Comment | Change |
|---|---|
| "Every message is schema-valid" exceeded the audit | Every generated record and every counterfactual original of all ten runs was validated (`scripts/validate_all_runs.py`, `results/validity_all_runs.json`): 2,089,794 of 2,089,794 valid, 0 invariant violations over 89,794 gamed records. The abstract now states that count. |
| P3 "at or below chance" contradicted D5 at 0.538 | "No message-level detector exceeds AUC 0.538, while the history-only control reaches 0.851." |
| Null-result wording too categorical | "No conclusive evidence that either grouping predicts primitive-level recovery; the contradiction label has almost no explanatory value, the family effect is suggestive but inconclusive with eleven primitives." |
| Leave-one-primitive-out sentence wrong | "The contradiction grouping is worse than the grand mean and the family grouping improves on it only marginally (0.123 and 0.099 against 0.107)." |
| "Pre-registered" overstated | "Pre-specified confirmatory", "specified after the exploratory evaluation and before the corrected rerun", throughout paper and supplement. |
| Table III `Rec.@1%` misleading for the shift | Column renamed "Rec. (A thr.)"; caption states recovery and alert rate are under A's frozen threshold, not at a 1% alert rate on B. |
| Replacement explanation not tested | Phrased as what the case analysis "suggests, without testing it in the same way"; an exploratory evidence-source grouping is reported in the supplement, labelled exploratory (it coincides with P3 versus the rest). |
| Attempt-level dependence assumption | Stated in Section IV-B; the fully independent extreme is reported (P3b 0.94 main, 0.49 independent; every other primitive within 0.06 of its per-message value). |
| Abstract length and detail | 241 words; two R^2 and two p-values removed; "highest-mean-AUC label-free detector". |
| Figure 1 small | Enlarged; page 5 still holds only references. |
| Domain validation | Not performed (requires raters); procedure unchanged. |
| Double-blind hygiene | The anonymous variant (`_Anonymous`) has no author block, "Anonymous" PDF metadata, and cites neither repository nor DOI; the reviewer read the named variant. Artifact links verified from a logged-out client (repository 200, DOI resolves, release page 200). |

# Addendum: fourth-round comments (30 September 2026, v3.0.2)

| Comment | Change |
|---|---|
| "label-free" overstates D5/D7 | "gaming-label-free" throughout, defined once in Section IV-C as using no gaming label while assuming a trusted benign training stream. |
| "unseen by message-level checks" | "not usefully separated by the tested message-level checks". |
| Abstract near 250 words | 235 words. |
| Figure 1 load | Reduced to four series (SEL, residual after D5 and D2, attempt-level) with more height; D1 and D7 residuals remain in the supplement. |
| Double-blind and AI-disclosure compliance | Anonymous variant carries no identifying strings or links; venue policy on the acknowledgment to be checked at submission. |
| Domain ratings | Still not performed; questionnaire and blinded rerun procedure released. |
