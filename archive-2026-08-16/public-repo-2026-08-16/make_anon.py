#!/usr/bin/env python3
"""
make_anon.py -- regenerate paper_F7_IEEEtran_ANON.tex from the named paper.

Keeps the two versions in lockstep. Every edit lands in the named .tex; the
anonymous version is derived, never hand-edited, so the double-blind copy can
never drift from the copy that carries the results.

Three transformations, and nothing else:
  1. header comment gains the DOUBLE-BLIND banner;
  2. a \\hypersetup line strips the identifying PDF metadata
     (Author/Title/Subject/Creator/Producer/Keywords);
  3. the author block becomes "Anonymous Author(s)".

Verify afterwards with:
    pdftotext paper_F7_IEEEtran_ANON.pdf - | grep -i sharma     # expect nothing
"""

from __future__ import annotations

import sys

SRC = "paper_F7_IEEEtran.tex"
DST = "paper_F7_IEEEtran_ANON.tex"

HEADER_FROM = """%% Detecting Purpose-Code Gaming in ISO 20022 Payments
%% CEEE 2026 submission -- IEEEtran conference format, 6 pages"""

HEADER_TO = """%% Detecting Purpose-Code Gaming in ISO 20022 Payments
%% CEEE 2026 submission -- DOUBLE-BLIND ANONYMIZED VERSION
%% IEEEtran conference format, 6 pages"""

HYPER_FROM = r"""\usepackage[hidelinks]{hyperref}"""

HYPER_TO = r"""\usepackage[hidelinks]{hyperref}
% Double-blind: strip identifying PDF metadata.
\hypersetup{pdfauthor={},pdftitle={},pdfsubject={},pdfcreator={},pdfproducer={},pdfkeywords={}}"""

AUTHOR_FROM = r"""\author{\IEEEauthorblockN{Abhishek Sharma}
\IEEEauthorblockA{\textit{Senior Member, IEEE}\\
Independent Researcher\\
Email: abhishek.sharma@ieee.org}}"""

AUTHOR_TO = r"""\author{\IEEEauthorblockN{Anonymous Author(s)}
\IEEEauthorblockA{Paper ID: \textit{(assigned at submission)}\\
Affiliation withheld for double-blind review}}"""

# Strings that must not survive into the anonymous source. The PDF is checked
# separately with pdftotext; this catches them one step earlier.
FORBIDDEN = ("Sharma", "abhishek", "Senior Member, IEEE", "Independent Researcher")


def substitute(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        sys.exit(f"make_anon: expected exactly 1 occurrence of {label}, found {n}. "
                 f"The named paper changed shape -- update make_anon.py.")
    return text.replace(old, new)


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        text = f.read()

    text = substitute(text, HEADER_FROM, HEADER_TO, "the header comment")
    text = substitute(text, HYPER_FROM, HYPER_TO, "the hyperref line")
    text = substitute(text, AUTHOR_FROM, AUTHOR_TO, "the author block")

    leaked = [s for s in FORBIDDEN if s.lower() in text.lower()]
    if leaked:
        sys.exit(f"make_anon: identifying strings survived: {leaked}")

    with open(DST, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"make_anon: wrote {DST} ({len(text)} chars); no identifying strings remain")


if __name__ == "__main__":
    main()
