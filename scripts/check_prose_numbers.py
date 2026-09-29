#!/usr/bin/env python3
"""Every numeric literal in the filled manuscript must either be a design
constant that already appears in the tokenised draft, or the value of a token
filled from results (tokens.json written by fill_paper.py).

Usage: check_prose_numbers.py <draft.tex> <filled.tex> <tokens.json>
"""
import json, re, sys
draft, filled, tokens = sys.argv[1:4]
NUM = re.compile(r"(?<![A-Za-z\d.])\d[\d,]*(?:\.\d+)?")
def nums(t):
    t = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "", t, flags=re.S)
    t = re.sub(r"%.*", "", t)
    t = re.sub(r"\\texttt\{[0-9a-f]{7,40}\}", "", t)   # commit hashes
    return set(NUM.findall(t))
d, f = nums(open(draft).read()), nums(open(filled).read())
tok = json.load(open(tokens))
tokvals = set()
for v in tok.values():
    tokvals |= set(NUM.findall(str(v)))
unsupported = sorted(x for x in f - d if x not in tokvals)
print(f"{len(f)} distinct numerals in filled tex; {len(f - d)} not in draft; "
      f"{len(unsupported)} unsupported")
for x in unsupported: print("  UNSUPPORTED", x)
sys.exit(1 if unsupported else 0)
