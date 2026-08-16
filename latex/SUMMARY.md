# Protocol run summary

n per run: 200000 · seeds: [7, 8, 9] · eta: 0.15 · rho: 0.05
lambda: 0.18 · temp: 0.1 · pi_floor: 0.1 · target pi_0: 0.45
elapsed: 323s

## Paste into paper_F7_IEEEtran.tex, in this order

1. **Table I** — replace the five `\tbd` rows with `latex/table1.tex`.
   Delete "No values are given because the run has not been performed."
2. **Table II** — replace the body with `latex/table2.tex`.
3. **Fig. 4 (ROC)** — replace the whole `tikzpicture` with `latex/fig_roc.tex`.
   Rewrite the caption: drop "Illustrative (synthetic); not measured" and the
   analytic-model sentence; state n, seeds, eta and the calibrated pi_0.
4. **Fig. 5 (SEL)** — replace with `latex/fig_sel.tex`. Same caption surgery.
   Report the bootstrap intervals in the caption (they are in the JSON and as
   a comment in the .tex fragment).
5. **Add Fig. 6 (eta sweep)** from `latex/fig_eta.tex`. This is the paper's
   actual result. If you are over 6 pages, drop Fig. 2 (pipeline) — it is the
   most expendable figure — rather than this one.
6. **Section VI** — delete the bold "have not been executed" sentence and the
   "Illustrative Analysis and Reporting Template" title; rename to "Results".
   Keep H1--H3 but rewrite each as confirmed / not confirmed against the data.
   Keep §VI-B (falsification) and state which outcome occurred.
7. **Section VII-C Conclusion threat** — rewrite; results now exist.
8. **Abstract** — replace the last sentence with the measured headline.
9. **Section IV-B** — state the calibrated P_NAME, TAU and PI_FLOOR, and note
   that SEL is reported at target pi_0 = 0.45 with the sweep in phase 0.
10. **Section V** — add the TEMP value (0.1) and the lambda (0.18).

## Calibration sweep (phase 0) — cite this, do not report SEL at one point
{
  "0.3": {
    "P_NAME": 0.00390625,
    "TAU": 0.7609375,
    "SEL_mean": 1.3951952521465574,
    "SEL_by_primitive": {
      "P1a": 1.5290382862740777,
      "P1b": 1.4132508269064994,
      "P1c": 1.35598746949387,
      "P1d": 1.4015081779273577,
      "P2a": 1.2309588364127548,
      "P2b": 1.2553903978037242,
      "P2c": 1.3296944032039872,
      "P2d": 1.265408056304936,
      "P3a": 1.5052138697469275,
      "P3b": 1.454636673657722,
      "P3c": 1.6060607758802727
    }
  },
  "0.45": {
    "P_NAME": 0.00390625,
    "TAU": 0.6232421875,
    "SEL_mean": 1.6308959738753197,
    "SEL_by_primitive": {
      "P1a": 1.841320066649228,
      "P1b": 1.6403769326386008,
      "P1c": 1.5714253369695461,
      "P1d": 1.6750883164399197,
      "P2a": 1.4486903413020364,
      "P2b": 1.4791926992292195,
      "P2c": 1.5775749183254701,
      "P2d": 1.4719941964646026,
      "P3a": 1.7143903554287576,
      "P3b": 1.7801744580444006,
      "P3c": 1.739628091136738
    }
  },
  "0.6": {
    "P_NAME": 0.125,
    "TAU": 0.55,
    "SEL_mean": 1.7989748616283656,
    "SEL_by_primitive": {
      "P1a": 1.856279237516743,
      "P1b": 1.9223402994005199,
      "P1c": 1.656132987159795,
      "P1d": 1.744251971006414,
      "P2a": 1.702353889980271,
      "P2b": 1.5478122204222609,
      "P2c": 1.9255000980581025,
      "P2d": 1.7274549931320133,
      "P3a": 1.671710861569574,
      "P3b": 2.1863449935621038,
      "P3c": 1.8485419261042269
    }
  }
}

## Leave-one-primitive-out (the headline)
{
  "P1": {
    "D0": 0.4955319703627241,
    "D1": 0.7846562478977736,
    "D2": 0.9906961938130093,
    "D3": 0.8016498259918848,
    "D4": 0.8115014383114421,
    "n_family": 2562.6666666666665
  },
  "P2": {
    "D0": 0.4958354385646242,
    "D1": 0.8219750633752163,
    "D2": 0.8272686869781888,
    "D3": 0.795595741285045,
    "D4": 0.8253940992893454,
    "n_family": 6102.666666666667
  },
  "P3": {
    "D0": 0.4997517651218968,
    "D1": 0.6958017616419389,
    "D2": 0.7054358085453729,
    "D3": 0.7086985672713845,
    "D4": 0.7139453747194636,
    "n_family": 5876.333333333333
  }
}
