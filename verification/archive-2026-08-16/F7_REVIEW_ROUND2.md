# F7 — Round-2 review against measured results

**Date:** 16 Aug 2026 · **Standard:** MASTER RULE §21 (multi-pass) · **Input:** your run report
**Decision: Major revision — re-run required.** Three defects contaminate the headline
numbers. All three are fixed in the patched `iso20022_gaming_bench.py`; one of them is mine.

---

## 1. Three defects, in order of how much they move the numbers

### 1.1 Calibration killed the name-matching leg — so the benchmark never studied misfielding

This is mine, and it is the worst of the three. I made `P_NAME` the sole free
parameter of the π calibration. The risk-scoring leg alone already exceeded
most π₀ targets, so bisection drove `P_NAME` to **0.0039** — the name-matching
leg went vestigial. P1a, P1c and P1d work by defeating name matching, so under
free choice they bought the evader nothing and the evader stopped picking them:

```
selection at k=1, 20k messages, old calibration:
{P1b: 1, P2a: 205, P2c: 7, P2d: 164, P3b: 420, P3c: 6}     P1 total = 1
```

One P1 selection in 20,000 messages. **Misfielding is the paper's headline attack
family and the main run contains essentially none of it.** Every P1 number you
reported came either from the forced `P1 only` ablation or from mixed-family
messages at k=2.

*Fix:* calibration now splits the survival probability multiplicatively between
the two legs via a stated `--name-share` (default 0.6 — name matching does most
of the baseline detection work, which is how screening is usually configured).
Both legs stay alive and all three π₀ targets hit exactly:

```
[calibrate] P_NAME=0.1400 TAU=0.8848 -> pi_0=0.2999 (name 0.140 / score 0.095) [OK]
[calibrate] P_NAME=0.2558 TAU=0.7676 -> pi_0=0.4489 (name 0.256 / score 0.177) [OK]
[calibrate] P_NAME=0.3853 TAU=0.6650 -> pi_0=0.6001 (name 0.385 / score 0.277) [OK]

selection at k=1, new calibration:
{P1a:148, P1b:1, P1c:123, P1d:139, P2a:104, P2c:24, P2d:76, P3a:144, P3b:88, P3c:145}
P1 411 | P2 204 | P3 377
```

`--name-share` is now a reportable modelling parameter. Sweep it alongside π₀.

### 1.2 Benign traffic never batched

Your finding, and you were right to call it. Fixed rather than left to my call,
because it is not a simplification — it is backwards from reality. pain.001 is a
*file*; corporates submit payroll and supplier runs as one instruction with many
transactions. pacs.008 is single-transaction.

`BENIGN_BATCH_RATE = 0.30` applies batching to pain.001 only, and P3b now
*multiplies* an existing split count rather than creating batching from nothing.
Precision of `n_splits > 1` as a gaming indicator drops **1.000 → 0.131**.

### 1.3 Leave-one-out was contaminated, and the table design was wrong

You found the contamination. There was a second problem underneath it that is
also mine: Table I puts AUC and AUC_LOO in adjacent columns as if comparable.
They are not — in-distribution scores benign + all families, LOO scores benign +
one family. Different test sets. That is why your LOO mean (0.784) came out
*above* in-distribution (0.775), which should be impossible and is the diagnostic
that the design is broken.

`evaluate_loo` now (a) scores only **pure-family** messages, so a held-out family
cannot leak in through a partner primitive, and (b) reports a **matched**
in-distribution AUC on the same rows, so the drop means something.

---

## 2. What the fixes do to your conclusions

Indicative only — n=20,000, k=1, single seed. Your `--full` re-run is the number
that counts.

| Family | n (pure) | D1 in→out | D2 in→out | D4 in→out |
|---|---|---|---|---|
| P1 misfielding | 411 | 0.733 → 0.733 | 0.831 → **0.335** | 0.753 → 0.753 |
| P2 code sub. | 204 | 0.812 → 0.812 | 0.952 → **0.723** | 0.762 → 0.762 |
| P3 structure | 377 | 0.422 → 0.422 | 0.811 → **0.487** | 0.459 → 0.459 |

**Your "D2 leads everywhere; labels still buy a lot" reverses.** Under clean
leave-one-out D2 collapses to 0.335 / 0.723 / 0.487 — two of three below chance.
It learns primitive signatures, not anything that transfers to a manipulation it
has not seen. That is exactly the production situation, and it restores §IV-D's
comparison of interest with a sharper answer than the paper hypothesised: labels
buy a great deal in-distribution and approximately nothing out of it.

**State explicitly that D1, D3 and D4 have a zero holdout gap by construction.**
None of them trains on gaming labels — D3 fits the benign stream only — so
leave-one-out is vacuous for them and the identical in/out figures are a
property of the design, not a measurement. Reporting `drop = 0.000` as though it
were measured would be misleading.

**P3 is below chance, not merely hard.** D1 0.422, D4 0.459. The constraint
features are anti-correlated with structure substitution. This is a clean, strong
negative result and it should be prominent.

---

## 3. The taxonomy's organising claim does not survive, and the replacement is better

§III asserts that coverage attacks (P1, P3) leave single-message structural
evidence while scoring attacks (P2) leave only cross-message distributional
evidence. The data contradicts both halves: P2 is the *most* detectable family
from single-message features (D1 0.812, via C3/C4), and P3 — a coverage family —
is below chance. Your H1 and H2 failures are the same finding seen twice.

Keep the three families as a descriptive checklist; that is what makes the
taxonomy citable, and it is unaffected. **Drop the claim that the dichotomy
predicts where evidence lands** and replace it with what the data actually shows:

> Detectability tracks whether a primitive creates a **checkable inconsistency
> inside the message**, not whether it attacks coverage or scoring. P1a, P1b and
> P1d break structural completeness or party consistency; P2a and P2d contradict
> the creditor's industry profile or the remittance narrative. P3a, P3b and P3c
> change the container or the decomposition without producing any internal
> contradiction — there is nothing to check the message against, and no
> single-message detector can help.

This is derived from measurement rather than asserted, and it gives control
owners something actionable: coverage gaps that leave no internal inconsistency
need a cross-message or cross-institution control, not a better validator.

---

## 4. Do not present the SEL ordering as a finding

P3b largest (1.78), P2a smallest (1.45) is a direct consequence of how π is
weighted: P3b attacks the amount term through `n_splits**0.5`, which is a large
additive contributor, while P2a swaps a purpose weight from ~0.18 to 0.08, which
is small. You have measured your own parameterisation. Report SEL to show the
metric discriminates and to quantify the size of the threat, and say in the same
breath that the *ordering across primitives is model-relative*. §VII-C already
concedes this as the construct threat; make §VI consistent with it.

The magnitude claim is fine and is the paper's strongest positive result:
manipulation raises pass-through by **45–78%** at π₀ = 0.45 (1.23–2.19 across the
π₀ sweep). That is a real threat, stated conservatively, with the sensitivity
shown.

---

## 5. The falsification condition was aimed at the wrong family

§VI-B says the detection contribution fails if **P2** detection does not exceed
D0 once η is realistic. P2 clears it comfortably (0.812 vs 0.496), so the
condition did not fire — correctly, as written. But **P3 sits at chance**, which
is the same failure for a different family, and the pre-registered wording lets
it through on a technicality.

Do not let narrow wording launder a negative result. Report: the condition as
written did not fire; the P3 family nonetheless fails it; here is what that
means. That sentence will do more for the paper's credibility than any number in
Table I.

---

## 6. Smaller items

- **P1b is inert.** One selection in 20,000 even after the calibration fix. π has
  no geographic-risk term keyed on the structured address, so destructuring costs
  the evader nothing. Either add such a term or state in §IV-B that P1b is
  present in the taxonomy but not exercised by the current π. Do not leave it
  looking measured.
- **TPR@1% = 2.1% is the headline, not AUC.** AUC ≈ 0.78 reads respectably; 2.1%
  recovery at an operational alert budget is the truth, and it is the number a
  control owner acts on. Lead the abstract with it. Also check it is stable
  across n — my quick run gave 8.2% at n=6,000 versus your 2.1% at n=200,000, and
  a swing that large usually means ties in D1 are dominating the top of the
  ranking and the 1% cut is being decided by tie-break order.
- **Seed-spread self-correction** (0.007 → 0.012 for D3): exactly right, and the
  kind of thing that should be in the paper's reproducibility note.
- **XSD validation with verified negative controls** — good. That makes the
  "schema-valid" claim in §IV-B true. Keep the negative-control detail in the
  artifact README; it is what distinguishes validation from a false pass.
- **Rank averaging for D4** with equal weights and nothing fittable to the test
  set: correct choice, state it in §IV-D.
- **Cuts to hold 6 pages:** accepted. Losing the ROC figure is fine now that
  Table I carries the same information. Losing Fig. 3 hurts, but the η figure
  earns its place. Note that re-running will change §VI's length again.

---

## 7. Framing after the re-run

The results are mostly negative and the paper is better for it, but the framing
has to catch up with them.

- **Contribution 3 must be demoted.** "A detection method" is not supportable
  when D3 does not beat D1 and both recover 2% at budget. The contributions are
  the taxonomy, the benchmark, the SEL metric, and the empirical finding.
- **Consider retitling** to lead with measurement rather than detection —
  *"Purpose-Code Gaming in ISO 20022 Payments: A Data-Quality Benchmark and
  Adversarial Evaluation"* costs one word and stops promising what §VI does not
  deliver. Your call; "Detecting" is defensible since detection is attempted and
  measured.
- **The paper's story is now:** the manipulation is real and worth 45–78% more
  pass-through; message-level data-quality detection recovers almost none of it
  at operational budgets; one whole family is undetectable in principle from a
  single message; and a supervised model that looks excellent in-distribution
  transfers not at all. That is a more useful paper than "our detector works,"
  and it is a legitimate benchmark contribution.

---

## 8. Re-run command

```bash
python run_protocol.py --full --xsd-dir ./xsd          # k=2 main run
python run_protocol.py --full --n 200000 --k 1 --xsd-dir ./xsd   # clean LOO
```

Report both: k=2 for the realistic evader, k=1 for the uncontaminated
leave-one-out. Sweep `--name-share` at 0.4 / 0.6 / 0.8 alongside the π₀ sweep and
report SEL as a range over both.

**Send me back** `latex/SUMMARY.md`, `results/*.json` and the updated `.tex` and I
will do the §21 passes against the corrected numbers and issue a readiness
decision.
