# Domain-rater questionnaire (to be completed blind to any detector result)

For each of the eleven primitives (Table II of the paper, definitions only),
rate on a 1-5 scale and give one sentence of reasoning:

| # | Question |
|---|---|
| Q1 | Actor plausibility: could the stated actor (originator, PSP, or one with route choice) actually make this edit? |
| Q2 | Semantics preservation: does the payment still move the same amount from the same economic originator to the same beneficiary? |
| Q3 | Operational cost ordering: is the stated cost rank relative to the other primitives reasonable? |
| Q4 | Schema plausibility: would the resulting message still be a plausible ISO 20022 instance? |
| Q5 | Already in public guidance: is this failure mode described in Swift, PMPG, CPMI or Wolfsberg material you know of? |
| Q6 | Contradiction label: does the edit make two elements of the same message, or an element and the creditor's static profile, inconsistent (yes/no)? |

Raters: two or three people with payment-message or financial-crime-control
experience. Report agreement (Cohen's kappa for Q6, Kendall's W for Q1-Q5)
and revise or drop any primitive below an agreed threshold. Q6 answers
replace `primitive_labels.json` and the contradiction test is rerun unchanged.
