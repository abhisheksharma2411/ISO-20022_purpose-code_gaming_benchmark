#!/bin/bash
# build_paper.sh <tex-path> [pages] : clean three-pass pdflatex build; with a
# second argument, also renders PNG pages (into <dir>/pages/) for reading.
set -e
TEX="$1"; DIR=$(cd "$(dirname "$TEX")" && pwd); BASE=$(basename "$TEX" .tex)
cd "$DIR"
rm -f "$BASE".aux "$BASE".log "$BASE".out "$BASE".pdf
for i in 1 2 3; do
  pdflatex -interaction=nonstopmode -halt-on-error "$BASE.tex" > "$BASE.build.log" 2>&1 \
    || { echo "BUILD FAILED: $BASE"; grep -n -A3 "^!" "$BASE.build.log" | head -40; exit 1; }
done
rm -f "$BASE.build.log"
echo "$BASE: pages $(pdfinfo "$BASE.pdf" | awk '/^Pages/{print $2}'), overfull $(grep -c 'Overfull' "$BASE.log"), undefined $(grep -c 'undefined' "$BASE.log")"
if [ -n "$2" ]; then mkdir -p pages; rm -f "pages/$BASE"-*.png; pdftoppm -r 80 -png "$BASE.pdf" "pages/$BASE"; fi
