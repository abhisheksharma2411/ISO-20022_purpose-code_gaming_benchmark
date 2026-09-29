#!/bin/bash
# make_paper.sh : fill every number from results/, build both variants, and
# run every gate. Fails on the first gate that does not pass.
#   PY="uv run --quiet --with numpy --with scikit-learn python" scripts/make_paper.sh
set -e
cd "$(dirname "$0")/.."
PY="${PY:-python3}"
ANON=paper/F7_ISO20022_Gaming_Revision_Anonymous.tex
NAMED=paper/F7_ISO20022_Gaming_Revision.tex
$PY scripts/fill_paper.py paper/draft_tokenised.tex . "$ANON"
sed 's/^\\anonymoustrue$/\\anonymousfalse/' "$ANON" > "$NAMED"
grep -q '^\\anonymousfalse$' "$NAMED"
scripts/build_paper.sh "$ANON"
scripts/build_paper.sh "$NAMED"
for f in "$ANON" "$NAMED"; do
  log="${f%.tex}.log"
  test "$(grep -c Overfull "$log")" = 0 || { echo "overfull boxes in $f"; exit 1; }
  test "$(grep -c undefined "$log")" = 0 || { echo "undefined references in $f"; exit 1; }
done
$PY scripts/check_prose_numbers.py paper/draft_tokenised.tex "$NAMED" "${ANON%.tex}.tokens.json"
$PY scripts/verify_claims.py . "$NAMED" | tail -1 | grep -q "^0 failure"
$PY - <<'PYEOF'
import sys; from pathlib import Path; sys.path.insert(0, "."); import style_risk_review as s
r = s.analyse(Path("paper/F7_ISO20022_Gaming_Revision.tex"))
print("style risk", r["style_risk_score_out_of_10"]); assert r["style_risk_score_out_of_10"] < 2.0
PYEOF
t=$(pdftotext "${ANON%.tex}.pdf" - | tr 'A-Z' 'a-z')
echo "$t" | grep -q "abhishek" && { echo "anonymous PDF leaks the author"; exit 1; }
echo "$t" | grep -q -E "author:|todo|placeholder|@@" && { echo "placeholder text in PDF"; exit 1; }
pdftotext "${NAMED%.tex}.pdf" - | grep -q "Abhishek Sharma" || { echo "named PDF lacks the author"; exit 1; }
echo "all gates passed"
