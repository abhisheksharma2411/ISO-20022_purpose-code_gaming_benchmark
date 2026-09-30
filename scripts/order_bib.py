#!/usr/bin/env python3
"""Reorder \\bibitem entries in a .tex file by first \\cite appearance (IEEE
citation-order style). Unused entries are dropped and reported.
Usage: order_bib.py <tex>"""
import re, sys
p = sys.argv[1]; s = open(p).read()
head, rest = s.split("\\begin{thebibliography}", 1)
pre, body = rest.split("}", 1)          # "{99}"
body, tail = body.split("\\end{thebibliography}", 1)
items = re.split(r"(?=\\bibitem\{)", body)
lead = items[0]; items = items[1:]
keyed = {re.match(r"\\bibitem\{([^}]+)\}", it).group(1): it.rstrip() + "\n" for it in items}
order = []
for m in re.finditer(r"\\cite\{([^}]+)\}", head):
    for k in m.group(1).split(","):
        k = k.strip()
        if k in keyed and k not in order: order.append(k)
unused = [k for k in keyed if k not in order]
if unused: print("dropping unused bibitems:", unused)
new = head + "\\begin{thebibliography}" + pre + "}" + lead + "".join(keyed[k] for k in order) + "\\end{thebibliography}" + tail
open(p, "w").write(new); print(f"bibliography ordered: {len(order)} entries")
