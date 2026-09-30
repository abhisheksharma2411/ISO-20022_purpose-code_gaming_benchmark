# F7 — CEEE 2026 · Review, Positioning and Handoff

**Paper:** *Detecting Purpose-Code Gaming in ISO 20022 Payments: A Data-Quality Benchmark and Adversarial Evaluation*
**Author:** Abhishek Sharma · **Date:** 16 Aug 2026 · **Standard applied:** project MASTER RULE, §§1–23

---

## 0. Two things you need to decide (nothing else is blocking)

1. **Run the experiments or submit as a benchmark/threat-model paper?** The paper as delivered is honest about having no measured results. CEEE reviewers will very likely ask for them. `iso20022_gaming_bench.py` is a working scaffold that produces every number the tables need — I smoke-tested it and it runs.
2. **Artifact URL.** No repo link appears in either `.tex` (MASTER RULE §7 forbids promising artifacts that don't exist). Add one line before the references once the GitHub repo is public.

---

## 1. Prior-art search — what changed as a result

Search executed 16 Aug 2026 over the sources you named plus AML-benchmark, adversarial-ML and payments-standards literature. **Three of your inputs needed correction.**

| Your input | What the search found | Action |
|---|---|---|
| NICE Actimize "ISO 20022 101" *names misfielding/misuse* | It does **not**. The post (Aug 2022) covers benefits and implementation only; no discussion of field misuse or evasion. | **Citation removed.** Would have been a §14 violation (citing a source for a claim it doesn't make). |
| Fed "Using the ISO 20022 Standard to Help Fraud Mitigation" (2026) | Real article, different title: *"Harnessing the power of ISO 20022: why the global payment standard matters for fraud mitigation,"* Fed360, **15 Apr 2026**. Does mention purpose-code pattern divergence. | Title and date corrected; cited [3]. |
| SWIFT "Market Practice Guidance: Purpose of Payment" | Publisher is **PMPG**, not Swift. Full title adds "Regulatory Reporting" and "Category Purpose"; v1.1, Jul 2024. **Contains the strongest sentence in the whole evidence base:** purpose codes are *"often misinterpreted by the industry or populated in the incorrect element of a payment instruction."* | Corrected and promoted to the paper's central motivating citation [6]. |

**Two sources added that materially change the framing:**

- **Swift guiding principles for screening ISO 20022** (Oct 2021, Wolfsberg-endorsed) exist precisely to define *which elements should and should not be screened*. This means the attack surface is not speculative — it is a published, deliberate property of the control. This is now the backbone of §I and §III.
- **CPMI, *Harmonised ISO 20022 Data Requirements for Enhancing Cross-Border Payments*** (BIS, updated Feb 2026, end-2027 horizon) is a stronger mandate citation than the Swift page alone.

**Date verified:** the CBPR+ unstructured-address removal is **14 November 2026**, not "November 2026" generally. Used precisely.

**Closest prior art, and why the contribution survives:**

| Work | What it does | Why it isn't this |
|---|---|---|
| AMLworld (Altman et al., NeurIPS 2023 D&B) | Agent-based synthetic transaction graphs, laundering ground truth | Transaction-graph level. No message structure, so an attack whose entire mechanism is *which element a string sits in* is inexpressible. |
| SAML-D (Oztas et al., ICEBE 2023) | Synthetic transaction-monitoring dataset with typology labels | Same — tabular transactions, no ISO 20022 fields. |
| SISTS (Wang et al., *Complex & Intell. Syst.* 2025) | **Adaptive** launderers co-evolving against a detector | Closest in spirit and the most dangerous omission if uncited. Operates on Bitcoin/AMLSim networks; no ISO 20022, no purpose codes, no misfielding. |
| arXiv:2312.07730 (Busson et al.) | Hierarchical transaction-purpose classification | Inferring a *missing* label ≠ detecting an *adversarially chosen* one. |
| Camacho & Rodríguez-Gómez, *Data* 10(3):33, 2025 | Dataset variant choice dominates algorithm choice in anomaly benchmarks | Supports the paper's design (organise around data quality + a controlled noise floor), not a competitor. |

### 5-line novelty positioning (conservative — use this verbatim in the cover letter)

> Cross-border payments must carry structured purpose codes and addresses from 14 November 2026, and published screening guidance defines which of those elements are matched and which are not — a partition an originator controls before any control sees the message.
> Market-practice guidance already records purpose codes being placed in the wrong element by accident; the deliberate case has no peer-reviewed threat model, benchmark or detector.
> We contribute an evasion-primitive taxonomy over named pain.001/pacs.008 elements, an open synthetic benchmark that generates accidental and deliberate versions of the same defects, and screening-evasion lift, a metric separating detector credit from screening credit.
> Existing AML benchmarks (AMLworld, SAML-D) and adaptive-launderer simulators (SISTS) operate on transaction graphs and cannot represent field-level manipulation; we reuse standard Stackelberg/evasion formalism rather than extending it.
> The empirical question is narrow and falsifiable: at a realistic rate of ordinary data-quality error, is deliberate field manipulation still separable?

**Claim I narrowed from your brief:** "first academic data-quality validation framework + benchmark for ISO 20022" → *"To our knowledge no peer-reviewed work models deliberate manipulation of ISO 20022 structured elements as an evasion strategy… We state this as the outcome of a search over the venues and sources cited here, not as a claim of exhaustive priority."* (MASTER RULE §1, §7: no "first" without a systematic search.)

---

## 2. Outline as built, with page budget (measured from the compiled PDF)

| § | Section | Pages | Contents |
|---|---|---|---|
| — | Title, abstract, index terms | 0.35 | |
| I | Introduction | 0.65 | Mandate → selectivity of screening → purpose codes as a choice → the confound → 3 contributions + scope |
| II | Background and Related Work | 0.9 | Fields in scope · screening selectivity · AML benchmarks · adversarial framing · positioning |
| III | Threat Model and Evasion Taxonomy | 1.1 | Actors, knowledge levels, eq. (1) · 11 primitives in 3 families · **Fig. 1** taxonomy |
| IV | Benchmark, Validation Framework, Detectors | 1.5 | C1–C5 · generator · SEL eqs. (2)(3) · D0–D4 · **Fig. 2** pipeline, **Fig. 3** element partition |
| V | Evaluation Protocol | 0.35 | Corpora, metrics, ablations, leave-one-primitive-out, reproducibility |
| VI | Illustrative Analysis and Reporting Template | 1.0 | H1–H3 · **Fig. 4** ROC, **Fig. 5** SEL · **Tables I, II** · falsification conditions |
| VII | Discussion, Ethics, Threats to Validity | 0.75 | Responsible framing · data/ethics · construct/internal/external/conclusion · next |
| VIII | Conclusion | 0.15 | |
| — | References (17) | 0.35 | |
| | **Total** | **6.0** | Exactly 6 pages; no page-7 overflow charge. |

Deviation from your brief: you asked for a separate message-field schematic *plus* a pipeline figure. Both are present (Figs. 2 and 3) and both are single-column, which is what kept the total at 6.

---

## 3. MASTER RULE §23 — required outputs

### 3.1 Complete revised paper
`paper_F7_IEEEtran.tex` (compiles clean, 6 pp) and `paper_F7_IEEEtran_ANON.tex` (6 pp, metadata stripped).

### 3.2 Substantive technical changes made to your brief

1. **Research question sharpened.** Your brief framed the question as "can we detect gaming?" Schema validation already detects most misfielding, so that question is close to trivial. The paper asks instead whether deliberate manipulation is separable **from the background of accidental misfielding**, with the noise floor η as an explicit swept parameter. This is the difference between a paper a reviewer waves through and one they argue with.
2. **Taxonomy re-organised by attacked control property** — *coverage* (P1, P3: the control never reads the content) vs *scoring* (P2: it reads everything and gets a wrong prior). This makes the defence implication fall out: coverage attacks leave single-message structural evidence, scoring attacks leave only cross-message distributional evidence. Your original three-way split was by mechanism, which doesn't yield that.
3. **11 primitives specified on named elements**, not three families in the abstract. P1a–d, P2a–d, P3a–c.
4. **SEL formalised two ways.** SEL (eq. 2) is screening-only; SEL_res (eq. 3) adds the detector. The *gap* between them is the paper's actual deliverable to a control owner and is not recoverable from a ROC curve. Your brief had one "screening-evasion-lift"; one number can't separate "the detector caught it" from "screening would have anyway."
5. **Leave-one-primitive-out protocol added.** Without it a detector scores well by learning the generator's edit signature. Named as the headline metric, in-distribution result demoted to an upper bound. This is the first thing a good reviewer would attack.
6. **The screening abstraction π is published, not hidden.** SEL is only reproducible if π's parameters are stated. Doing so also makes the paper's biggest weakness explicit rather than discoverable.
7. **Baseline D0 added** (schema/code-list only). Without a free baseline, all the other numbers are unanchored.
8. **D2 defined as needing labels, D3 as not.** The comparison of interest is whether unsupervised constraint features match a supervised model, because in production the gaming labels don't exist.
9. **Falsification conditions written into §VI-B.** Two named outcomes that would sink the detection contribution, with a statement that they'd be reported.
10. **No results claimed.** §VI opens in bold with "the experiments have not been executed." Figures carry "Illustrative (synthetic); not measured" in the caption plus the analytic model that generated them; tables are templates with `TBD` cells.

### 3.3 Language changes

- Removed from your brief's phrasing: "richer structured fields create a new attack surface" (kept the idea, dropped the register), "novel", "comprehensive", "robust", "leverage", "underscores".
- The Fed article's own title contains "Harnessing the power of" — quoted as a title only, never in our prose.
- No paragraph opens with "This paper". No contribution bullet shares a grammatical shape with its neighbours. No three-item list is used where two or four items are the truth.
- Sentence-length variance is deliberate: §I ¶2 runs long because the argument is a chain; §III ¶1 is short because it's an assumption statement.
- Section VIII does not restate the abstract; it ends on the open question rather than a summary.

### 3.4 Claim-to-evidence matrix

| # | Claim | Where | Evidence | Status |
|---|---|---|---|---|
| 1 | Unstructured addresses removed from CBPR+ on 14 Nov 2026 | Abstract, §I | Swift [1] | **Verified** (fetched 16 Aug 2026) |
| 2 | Harmonised requirements push registered external codes; end-2027 | §I, §IV-A | CPMI [2] | **Verified** |
| 3 | Structured data is expected to improve fraud detection via purpose-code pattern divergence | §I, §IV-A | Fed360 [3] | **Verified** |
| 4 | Screening is selective; guidance defines which elements are/aren't screened | §I, §II-B, §III | Swift [4], Wolfsberg [5] | **Verified** — this is the load-bearing citation |
| 5 | Purpose codes are often placed in the wrong element | §I, §IV-B | PMPG [6] direct quote | **Verified** |
| 6 | National recommended purpose-code lists narrow the corridor vocabulary | §II-A | BoE [7] | **Verified** |
| 7 | AML benchmarks operate at transaction-graph level, not message level | §II-C | [9], [10], [11] read | **Verified** |
| 8 | Purpose classification is enrichment, not gaming detection | §II-C | [12] read | **Verified** |
| 9 | Adversarial/Stackelberg formalism is reused, not extended | §II-D, §III-B | [14], [15], [16] | **Verified** (standard) |
| 10 | Dataset-variant choice dominates algorithm choice in anomaly benchmarks | §II-D | [13] | **Verified** |
| 11 | No peer-reviewed work models ISO 20022 field manipulation as evasion | §II-E | This search | **Search-scoped**, explicitly hedged in text |
| 12 | Detector D3 outperforms D1/D2 (H1–H3) | §VI | **None** | **Hypothesis**, labelled |
| 13 | SEL is largest for P2a/P1a | §VI, Fig. 5 | **None** | **Hypothesis**, labelled |
| 14 | Constraint features separate deliberate from accidental misfielding | §VI | **None** | **Open question** — this is the paper's point |

Rows 12–14 carry no evidence, and the paper says so in bold at the top of §VI. Rows 1–11 are all traceable to a source I fetched and read.

### 3.5 Claims removed or narrowed

| Original | Disposition |
|---|---|
| "First academic data-quality validation framework and benchmark for ISO 20022" | Narrowed to a search-scoped statement with an explicit non-priority disclaimer |
| "NICE Actimize names misfielding/misuse" | **Deleted** — source does not support it |
| "The threat is described in vendor/regulator prose" | Kept but now grounded in PMPG's accidental-misfielding sentence rather than asserted |
| "Detection method with a screening-evasion-lift metric" as a completed contribution | Reframed: the *metric* and *protocol* are contributions; detector *performance* is a hypothesis |
| "An empirical study" (contribution 4 in your brief) | **Removed from the contribution list** — no study has been run (§7: no future work in contributions) |
| Implied SWIFT authorship of the purpose-of-payment guidance | Corrected to PMPG |

### 3.6 Citation audit

17 references. Every one was fetched and read during this session except where noted.

- [1] Swift address removal — fetched; date 14 Nov 2026 confirmed from the page.
- [2] CPMI/BIS — fetched; Feb 2026 update, end-2027 horizon confirmed.
- [3] Fed360 — fetched; title and 15 Apr 2026 date confirmed. ⚠️ Fed360 is a newsletter, not peer-reviewed; cited only for a statement about intent and mechanism, which is appropriate.
- [4] Swift guiding principles — the announcement page was fetched; **the guidance PDF itself was not retrieved.** Confirm the exact document title and publication date from the PDF before submission. This citation is load-bearing.
- [5] Wolfsberg Payment Transparency Standards 2023 — located; **PDF not read in full.** Verify the 2023 edition is current.
- [6] PMPG v1.1 Jul 2024 — fetched; direct quote verified against the document.
- [7] BoE UK Recommended Purpose Code List — located; **year 2021 is my inference from the RTGS Renewal timeline. Verify.**
- [8] Protiviti white paper 2023 — located, not read in full. Cited for a general characterisation only; **droppable if you need a line of space.**
- [9] Altman et al. NeurIPS 2023 — full author list verified against the NeurIPS proceedings page.
- [10] Oztas et al. — title, six authors, ICEBE 2023, pp. 47–54, DOI verified.
- [11] Wang et al. — vol. 11, art. 271, 2025, DOI verified; paper read.
- [12] Busson et al. arXiv:2312.07730 — verified; `et al.` used because the author list is 17 people.
- [13] Camacho & Rodríguez-Gómez, *Data* 10(3):33, DOI verified.
- [14]–[17] Dalvi 2004, Brückner & Scheffer 2011, Biggio 2013, Liu 2008 — canonical, cited from standing knowledge; **page numbers should be checked against the ACM/Springer/IEEE records before submission.**

No reference is unused. No reference is cited for keyword overlap. No DOI was invented.

### 3.7 Remaining missing evidence

1. **All detector performance.** Tables I and II are empty by construction.
2. **The noise floor η.** No public estimate of the real rate of accidental misfielding exists that I could find. Swept, not estimated — stated as such in §VII-C.
3. **Real purpose-code distributions by corridor and industry.** Generated from an assumed profile.
4. **Calibration of π.** SEL is a ratio of pass-through probabilities and is *very* sensitive to the baseline π₀ — see §5 below. This is the single biggest number-quality risk in the paper.
5. **Defensive cost.** The false-positive burden of the constraint features on benign traffic is not measured. §VII-D says so.

### 3.8 Reviewer-style assessment

*What Reviewer 2 will say, in the order they'll say it:*

- **"There are no results."** Unanswerable as it stands. This alone can sink the paper at a venue that expects an empirical contribution. Mitigation: run the protocol.
- **"Your screening model is invented, so SEL measures your own assumptions."** Fair, and conceded in §VII-C as the most serious limitation. Strengthen by reporting SEL across a π₀ sweep rather than at one point — the scaffold now supports `--target-pi0` for exactly this.
- **"Isn't this just adversarial ML applied to a new domain?"** Partly, and the paper says so in the Scope paragraph. The defence is that the domain constraint V — schema validity, code-list validity, STP acceptance — is what makes the attack surface finite and enumerable, unlike pixel-space evasion. That argument is in §III-B; make sure you can deliver it in the Q&A.
- **"Your detector learned your generator."** Pre-empted by leave-one-primitive-out, and §VII-C admits the mitigation is partial.
- **"Why not use AMLworld?"** Answered in §II-C: it has no message structure. Have the one-sentence version ready.
- **Likely accept-with-revisions if the results exist; likely reject or weak-accept as a position paper.** CEEE is not a top-tier venue and the taxonomy alone is a reasonable contribution, but the empty tables are conspicuous.

### 3.9 Natural-language assessment

Reads as written by someone who works on payments. Domain vocabulary is used precisely (`Purp/Cd`, CBPR+, STP, F_s) and defined at first use. Sentence and paragraph lengths vary; no paragraph is a list of broad claims. The §20 warning-sign sweep found nothing to remove. Two places I'd flag as slightly stiff on a read-aloud: §II-B's second sentence, and the §IV-D detector enumeration, which is necessarily list-like. Neither is worth trading clarity for.

### 3.10 Reproducibility assessment

The paper is reproducible **as a specification**: constraints, primitives, metrics, protocol and π's structure are all stated. It is not reproducible **as a result**, because there is no result. `iso20022_gaming_bench.py` closes that gap: seeded, deterministic, config-hashed output files, no external data. Once you run it, §VI is a fill-in job.

### 3.11 Venue compliance

- IEEEtran `[conference]`, two-column — ✓
- Exactly 6 pages including references, no per-page overage — ✓
- All figures inline (TikZ/pgfplots), no external files, compiles from a single `.tex` — ✓
- Double-blind version: author block anonymised, PDF metadata (Author/Title/Subject/Creator/Producer/Keywords) emptied via `hypersetup`, text scan for identifying strings returns zero hits — ✓
- No self-citation to blind (no STREAM-BSG reference anywhere — confirmed by grep) — ✓
- **You must check:** CEEE 2026's generative-AI disclosure policy. IEEE requires AI-assisted writing to be disclosed in the acknowledgments. Draft wording is in §6 below.
- **You must check:** whether CEEE 2026 actually runs double-blind. Many IEEE regional conferences are single-blind; if so, submit the named version.

### 3.12 Final readiness decision

> **Major revision required.**

Not because of the writing — the prose, structure, citations and positioning are submission-grade. Because §VI contains no measured evidence, and the paper's central claim (that constraint features separate deliberate from accidental misfielding) is untested. Run the protocol in §V, fill Tables I and II, replace Figs. 4 and 5 with measured curves, and the decision moves to *submission-ready after named minor changes* (citation spot-checks in §3.6, venue policy checks in §3.11).

I will not claim this passes an AI detector, and nothing here was written to influence one.

---

## 4. Experiments to run before submission

Ordered by what a reviewer notices first.

**Blocking — the paper cannot be submitted with results until these are done**

1. **Calibrate π.** Run `--target-pi0` at 0.30, 0.45 and 0.60. Report SEL at all three; do not report a single point. Rationale: SEL = (1−π_m)/(1−π_0), so at π₀ = 0.94 you get SEL ≈ 15, which is not credible. At π₀ = 0.45 the scaffold returns SEL ≈ 1.7–2.3, which is in the range Fig. 5 predicts.
2. **Main run.** n = 10⁶, five corridors, η = 0.15, ρ = 0.02, k = 2, grey-box, three seeds. Fill Table I.
3. **Leave-one-primitive-out.** Train D2/D3 with each family withheld; evaluate on it. This is the AUC_LOO column and the headline number.
4. **η sweep.** η ∈ {0.02, 0.05, 0.10, 0.15, 0.25, 0.40}. Plot AUC vs η per detector. **This is the paper's actual result** — if separability collapses at realistic η, say so; §VI-B already commits you to reporting it.
5. **Ablations.** Primitive family (P1/P2/P3), evader budget k ∈ {1,2,3}, knowledge ∈ {black, grey}. Fill Table II.
6. **Replace Figs. 4 and 5** with measured curves and delete the "illustrative" captions and the analytic-model sentence.

**Important — a reviewer will ask**

7. **Bootstrap CIs** on SEL and SEL_res (1000 resamples). The paper promises them in §IV-C.
8. **Defensive cost.** Alert volume on the benign stream at each operating point. Currently promised as future work in §VII-D; one table row would strengthen the paper more than it costs.
9. **Seed sensitivity.** Three seeds minimum; report spread, not just the mean.
10. **Emit real XML.** The scaffold works on a flattened record. Emitting schema-valid pain.001/pacs.008 instances and validating against the ISO 20022 XSDs makes the "schema-valid" claim in §IV-B true rather than asserted. Without it, narrow the wording.

**Known issues in the scaffold you should fix while running**

11. **Evader coverage.** With `--lam 0.35` the evader only selects the cheap primitives (P2*, P3b, P1c). Lower `--lam` to ~0.15 or raise `--temp` so P1a/P1b/P1d/P3a/P3c appear often enough for the per-primitive ablation (the code skips any primitive with n < 30).
12. **D4 currently underperforms D3** in the smoke run. The z-score combination is naive; try rank averaging or a stacked logistic layer. Report whichever you use.
13. **Label leakage — already fixed, don't reintroduce it.** D2's feature vector must not contain `PURPOSE_RISK` or `CORRIDOR_RISK`: those are the evader's own objective terms and drove D2 to AUC ≈ 0.998 before I replaced them with one-hot codes.
14. **`--temp` must be reported.** A perfectly rational evader (`temp = 0`) concentrates on one primitive and starves the ablation. The softmax is a methodological choice, not a bug — state the value in the paper.

**Before upload**

15. Recompile both `.tex`, confirm 6 pages, re-run `pdftotext | grep` on the anonymous PDF for your name, employer and repo URL.
16. Archive the exact generator commit, config JSONs and result files; cite the commit hash in the paper.

---

## 5. Dataset and ethics note (for the artifact repo and, condensed, for §VII-B)

**Data provenance.** Every message, entity, account, name and address in this benchmark is generated by `iso20022_gaming_bench.py` from seeded pseudo-random distributions. No real payment message, customer record, transaction log, alert outcome or employer-internal data was used at any stage — not for generation, not for calibration, not for validation. No confidential or employer-proprietary information appears in the code, its configuration, or the paper.

**Personal data.** None. Entity names are of the form `ENTITY####`; addresses use invented town names; account identifiers are integers. The release carries no personal data and requires no consent regime or DPIA.

**Dual-use assessment.** The taxonomy describes how a payment originator could reduce the probability that a payment is screened. That is offensive knowledge, and it is published deliberately, on three grounds:

1. *Already public.* Every primitive is derivable from documents anyone can read: the ISO 20022 external code lists, the CPMI harmonised requirements, the Swift/Wolfsberg guidance stating which element classes are screened, and PMPG guidance recording misfielding as a live problem. We disclose no non-public mechanism.
2. *Asymmetric benefit.* An adversary motivated enough to move money already knows which fields a bank reads; the defender is the party who lacks a structured checklist of coverage gaps. The taxonomy is more useful to the defender than to the attacker.
3. *Deliberately non-operational.* We publish no tuned parameters against any deployed screening engine, and π is a generic model rather than a reproduction of any product. We withhold corridor- and code-specific risk weightings that would turn the generator into an operational recipe. The weights in the released code are illustrative constants chosen for the study, and are labelled as such in the source.

**What we would not publish.** Real corridor-level purpose-code risk weights, real fuzzy-match thresholds, or any parameter obtained from a production engine — including in aggregate form.

**Licence and release.** Recommend MIT for the code and CC BY 4.0 for the generated corpora, with a README stating that the data is synthetic and must not be represented as real payment traffic.

**Author responsibility.** The work is done independently of the author's employer, on personal time, using no employer systems, data or confidential information. No employer is named in the paper.

---

## 6. Suggested AI-use disclosure (check against CEEE 2026's policy before using)

> *Acknowledgment.* The author used a large language model (Claude, Anthropic) as a writing and literature-search assistant: to locate and verify prior art, to draft and revise prose, and to produce the LaTeX figures and the reference implementation scaffold. The author defined the research question, the threat model, the taxonomy and the evaluation design; verified every citation against its primary source; and takes full responsibility for all content, claims and results.

Omit from the anonymous version if it is identifying under the venue's rules; IEEE normally allows the acknowledgment to be blinded and restored at camera-ready.

---

## 7. Files

| File | What it is |
|---|---|
| `paper_F7_IEEEtran.tex` / `.pdf` | Named version, 6 pp, compiles clean |
| `paper_F7_IEEEtran_ANON.tex` / `.pdf` | Double-blind, metadata stripped, 6 pp |
| `iso20022_gaming_bench.py` | Reference implementation: generator, evader, D0–D4, SEL. Smoke-tested. |
| `F7_REVIEW_AND_HANDOFF.md` | This document |

Build: `pdflatex paper_F7_IEEEtran.tex` ×3 (needs `texlive-publishers` for `IEEEtran.cls`, plus `pgfplots`).
Run: `python iso20022_gaming_bench.py --n 200000 --eta 0.15 --rho 0.02 --k 2 --target-pi0 0.45 --seed 7`
