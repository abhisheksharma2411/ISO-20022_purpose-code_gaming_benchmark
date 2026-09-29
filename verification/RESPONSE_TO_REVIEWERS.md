# Response to the reviewers

We thank both reviewers. The revision rewrites the manuscript around a
corrected experimental protocol; section numbers below refer to the revised
version. Headline numbers changed because two defects in the evaluation
harness and one in the generator were found and fixed during the revision
(see "Changes not requested by the reviewers"); the conclusions the reviewers
commented on survive, and the changed numbers are now traceable to the
released result files.

## Reviewer #2

**Title.** We agree that "purpose-code gaming" named only four of the eleven
manipulations. The paper is now titled "Gaming ISO 20022 Payment Messages: An
Adversarial Data-Quality Benchmark for Purpose Codes, Party Fields, and
Message Paths". The abstract defines message gaming as the umbrella term and
purpose-code gaming as its best-known case.

**Literature review does not incorporate recent studies.** Section II-B now
positions the work against the transaction-level AML resources (Elliptic,
AMLSim, AMLworld, SAML-D, and the 2025-2026 generators AMLgentex and Tide),
graph detectors built on them (Egressy et al., AAAI 2024), the constrained
tabular adversarial line (Ballet et al. 2019; Cartella et al. 2021; Simonetto
et al., IJCAI 2022, CAA 2024, TabularBench NeurIPS 2024; Fok et al. 2025),
noisy payment-address parsing (Hammami et al., NAACL 2024), and FraudBench
(2026). Table I compares the scope of these resources with ours along seven
dimensions. Eleven references were added; the network-intrusion data-quality
citation was removed as tangential.

**Proposed methodology not presented; insufficient technical detail.**
Sections III and IV now state everything needed to reproduce the numbers:
the population constants (industries, corridors, code lists, amount
distribution, batching, pair structure, remittance text), the cost of every
primitive (Table II), the admissibility condition and the black-box adversary's
admissible set, both legs of the screening abstraction with their functional
form and weight ranges (Eq. 2-3), the calibration procedure and its solved
parameters, the definition of every feature (Table III), each detector's
implementation and hyperparameters, the cross-fitting protocol, how the
history feature is built, the absence of class weighting and of any tuned
hyperparameter, the metrics with their confidence intervals, and the commit of
the harness that produced the results.

**Results not sufficiently discussed, analysed, or compared with existing
methods.** Two standard reference methods were added on identical inputs, a
local outlier factor and a logistic regression (Section V-B), and the results
table now carries average precision, precision at capacity, three-seed
standard deviations and the capacity ceiling; DeLong and record-bootstrap
intervals are reported in the text. Section V-A explains why the ordering of
the label-free detectors by AUC is the reverse of their ordering by recovery.
Section V-C gives the mechanism behind the below-chance held-out score, which
the reviewed version only reported. Section V-B also reports an audit of
whether any detector's alerts rest on generator artefacts.

**Some references are not relevant.** The network-intrusion data-quality
reference was removed. The transaction-classification reference is retained
as an explicit contrast (classification of naturally occurring labels versus
detection of strategically chosen codes). The Swift, CPMI, PMPG and Federal
Reserve documents are retained because they are the primary sources for
ISO 20022 field use and screening practice.

## Reviewer #3

**Class composition.** The abstract states the share of gamed records; Section
IV-F gives the exact composition (about 5.0% gamed per run, 99.4% of illicit
records selecting at least one edit, 53-61 unevaded illicit controls per
seed) and the capacity ceilings that follow from it.

**Confidence intervals.** Table IV reports three-seed standard deviations for
AUC and recovery; the text reports the DeLong interval for AUC and the
record-bootstrap interval for recovery at capacity, and per-seed ranges for
the held-out-family results.

**Synthetic and model-relative nature.** Stated once in the abstract, in the
sentence that introduces the evaluation, and developed in Sections VI-B and
VI-C. We did not add a second disclaimer sentence.

## Changes not requested by the reviewers

While revising we audited the released harness and found that (1) the
supervised detector had been scored on rows it was trained on, which inflated
its in-distribution AUC by about 0.03; (2) the pair-history feature was built
using the gaming label; and (3) benign remittance text in the generator had
exactly two possible lengths, so any appended text was a unique signature and
a one-line rule recovered the whole alert capacity. All three are fixed
(cross-fitting, out-of-fold label-free history, variable-length benign
strings), the audit is retained as a regression check, and every number in
the paper was regenerated from the corrected run. The reviewed version's claim
that the combined detector removed the whole benefit of the code-narrative
mismatch does not survive the correction and has been withdrawn; the other
conclusions do survive.
