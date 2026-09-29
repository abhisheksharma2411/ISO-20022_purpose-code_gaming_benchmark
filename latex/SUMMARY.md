# Protocol run summary

n per run: 200000 · seeds: [7, 8, 9] · eta: 0.15 · rho: 0.05
lambda: 0.18 · temp: 0.1 · pi_floor: 0.1 · target pi_0: 0.45
elapsed: 815s

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
    "P_NAME": 0.13997055931729052,
    "TAU": 0.884765625,
    "SEL_mean": 1.2216502664869724,
    "SEL_by_primitive": {
      "P1a": 1.207269522135207,
      "P1b": 1.1986062720464434,
      "P1c": 1.15561055145421,
      "P1d": 1.196597867780172,
      "P2a": 1.23741771223643,
      "P2b": 1.1663523322183227,
      "P2c": 1.1844720520807328,
      "P2d": 1.2488310395018754,
      "P3a": 1.2314974743304272,
      "P3b": 1.3540647678798148,
      "P3c": 1.2574333396930626
    }
  },
  "0.45": {
    "P_NAME": 0.2558300859012992,
    "TAU": 0.767578125,
    "SEL_mean": 1.4767573985797824,
    "SEL_by_primitive": {
      "P1a": 1.4730987007108012,
      "P1b": 1.3764194264325145,
      "P1c": 1.3681722290397003,
      "P1d": 1.4637486869345946,
      "P2a": 1.5149856428729402,
      "P2b": 1.330614204457207,
      "P2c": 1.3646153988447283,
      "P2d": 1.5425973524972494,
      "P3a": 1.4892932344720027,
      "P3b": 1.7836318757985548,
      "P3c": 1.5371546323173122
    }
  },
  "0.6": {
    "P_NAME": 0.3852613923455148,
    "TAU": 0.6650390625,
    "SEL_mean": 1.9176236708496612,
    "SEL_by_primitive": {
      "P1a": 1.9642741713952963,
      "P1b": 1.626861957183107,
      "P1c": 1.7256965590366677,
      "P1d": 1.9279206409076575,
      "P2a": 2.00565082226896,
      "P2b": 1.6025582469214184,
      "P2c": 1.6001637615248872,
      "P2d": 1.9837660794222558,
      "P3a": 2.025524893448875,
      "P3b": 2.5956468965557935,
      "P3c": 2.0357963506813603
    }
  }
}

## Leave-one-primitive-out (the headline)
{
  "P1": {
    "D0": 0.4916266869260717,
    "D1": 0.8171120703619991,
    "D2": 0.46463395655184053,
    "D3": 0.8105196601993065,
    "D4": 0.8455570973243646,
    "D0_matched_in": 0.4916266869260717,
    "D0_drop": 0.0,
    "D1_matched_in": 0.8171120703619991,
    "D1_drop": 0.0,
    "D2_matched_in": 0.8489123689622566,
    "D2_drop": 0.3842666666666667,
    "D3_matched_in": 0.8105196601993065,
    "D3_drop": 0.0,
    "D4_matched_in": 0.8455570973243646,
    "D4_drop": 0.0,
    "n_pure": 1328.3333333333333,
    "purity": 0.21166666666666667
  },
  "P2": {
    "D0": 0.5007295135762359,
    "D1": 0.8860963475585933,
    "D2": 0.8496182493974773,
    "D3": 0.7540481922798291,
    "D4": 0.8468880599570063,
    "D0_matched_in": 0.5007295135762359,
    "D0_drop": 0.0,
    "D1_matched_in": 0.8860963475585933,
    "D1_drop": 0.0,
    "D2_matched_in": 0.9904056720520273,
    "D2_drop": 0.1408,
    "D3_matched_in": 0.7540481922798291,
    "D3_drop": 0.0,
    "D4_matched_in": 0.8468880599570063,
    "D4_drop": 0.0,
    "n_pure": 319.0,
    "purity": 0.062
  },
  "P3": {
    "D0": 0.5007931092503225,
    "D1": 0.4408326701733721,
    "D2": 0.47325469436988854,
    "D3": 0.6064294845201014,
    "D4": 0.5377790179309728,
    "D0_matched_in": 0.5007931092503225,
    "D0_drop": 0.0,
    "D1_matched_in": 0.4408326701733721,
    "D1_drop": 0.0,
    "D2_matched_in": 0.8471596682698986,
    "D2_drop": 0.37390000000000007,
    "D3_matched_in": 0.6064294845201014,
    "D3_drop": 0.0,
    "D4_matched_in": 0.5377790179309728,
    "D4_drop": 0.0,
    "n_pure": 1230.6666666666667,
    "purity": 0.21933333333333335
  }
}
