# Pre-registered analysis plan for the v3 protocol (30 September 2026)

Recorded before the first full-scale v3 run. The commit that adds this file
precedes every result file in `results/` produced by the v3 harness.

1. **Protocol.** Each corpus is generated in time order. The earliest 60% of
   records trains every learned detector; the next 20% is the validation
   window on which the alert threshold for each capacity (1%, 0.1%) is frozen;
   the latest 20% is the test window on which every reported number is
   computed. History features use strictly earlier messages of the same
   debtor-creditor pair and no label. Uncertainty is a pair-clustered
   bootstrap (200 resamples) on the test window; seeds 7 to 16 give the
   between-run spread.
2. **Paired SEL.** Every gamed record keeps its unmanipulated original, scored
   by the same detector with the same prior history. SEL and residual SEL are
   ratios of sums over gamed test records; no separate no-edit control group
   is used. Attempt-level SEL treats the name leg and residual floor once per
   attempt and the score leg once per child transaction.
3. **Contradiction versus family.** Labels and outcome are fixed in
   `primitive_labels.json`. Primary detectors: D2 and D5. Reference: D1.
   Statistics: R^2 of recovery on the grouping, difference in group means,
   exact permutation p-values, leave-one-primitive-out mean absolute error.
   Competing explanations: family, contradiction, cost, frequency, capability.
4. **Directional expectations** (kept from the reviewed version): P1 and P3
   would behave similarly as coverage changes; P2 would be harder for fixed
   rules. A family AUC near chance or a SEL near 1 counts against that
   framing. Expectation for the history-only control D7: it should improve on
   the message-level detectors for P3 (path, decomposition, party chain),
   since those edits leave no internal contradiction but do break the pair's
   prior pattern.
5. **Robustness.** Prevalence 0.5%, 1%, 5% (seeds 7-9, 200k). Generator shift:
   fit and freeze on configuration A, test on configuration B; B-on-B as
   reference. Conclusions must hold on the A-to-B test window to be reported
   as robust.
6. **Validity.** Every generated pain.001.001.09 and pacs.008.001.08 instance
   in the seed-7 test window, every gamed record and its original, is
   validated against the official XSDs; invariant checks run on every gamed
   record. Target: 100% XSD-valid, 0 invariant violations.
