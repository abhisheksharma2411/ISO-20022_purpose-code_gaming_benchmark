#!/bin/bash
# make_paper.sh : contradiction test, fill both documents, order bibliography,
# build named and anonymous variants, run every gate.
set -e
cd "$(dirname "$0")/.."
PY="${PY:-python3}"
$PY scripts/contradiction_test.py . results
ANON=paper/F7_ISO20022_Gaming_v3_Anonymous.tex; NAMED=paper/F7_ISO20022_Gaming_v3.tex
SANON=paper/F7_ISO20022_Gaming_v3_Supplement_Anonymous.tex; SNAMED=paper/F7_ISO20022_Gaming_v3_Supplement.tex
$PY scripts/fill_paper.py . results paper/draft_tokenised.tex "$ANON" paper/supplement_tokenised.tex "$SANON"
$PY scripts/order_bib.py "$ANON"
sed 's/^\\anonymoustrue$/\\anonymousfalse/' "$ANON" > "$NAMED"; sed 's/^\\anonymoustrue$/\\anonymousfalse/' "$SANON" > "$SNAMED"
for f in "$ANON" "$NAMED" "$SANON" "$SNAMED"; do scripts/build_paper.sh "$f"; done
for f in "$ANON" "$NAMED"; do
  log="${f%.tex}.log"
  test "$(grep -c "Overfull .hbox" "$log")" = 0 || { echo "overfull boxes in $f"; exit 1; }
  test "$(grep -c undefined "$log")" = 0 || { echo "undefined references in $f"; exit 1; }
  test "$(pdfinfo "${f%.tex}.pdf" | awk '/^Pages/{print $2}')" -le 5 || { echo "$f exceeds five pages"; exit 1; }
done
$PY scripts/check_prose_numbers.py paper/draft_tokenised.tex "$NAMED" "${ANON%.tex}.tokens.json"
$PY scripts/verify_claims.py . results "$NAMED" "$SNAMED" | tail -1 | grep -q "^0 failure"
$PY - <<'PYEOF'
import sys; from pathlib import Path; sys.path.insert(0, "."); import style_risk_review as s
r = s.analyse(Path("paper/F7_ISO20022_Gaming_v3.tex")); print("style risk", r["style_risk_score_out_of_10"]); assert r["style_risk_score_out_of_10"] < 2.0
PYEOF
t=$(pdftotext "${ANON%.tex}.pdf" - | tr 'A-Z' 'a-z'); echo "$t" | grep -q -E "abhishek|abhisheksharma2411|zenodo" && { echo "anonymous PDF leaks identity"; exit 1; }
echo "$t" | grep -q -E "author:|todo|placeholder|@@|pending\]\]" && { echo "placeholder text in PDF"; exit 1; }
pdftotext "${NAMED%.tex}.pdf" - | grep -q "Abhishek Sharma" || { echo "named PDF lacks the author"; exit 1; }
echo "all gates passed"
