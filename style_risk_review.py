#!/usr/bin/env python3
"""Transparent prose-style heuristic for the F7 paper.

This is not an AI detector. It flags traits that often make technical prose
sound templated: repetitive sentence openings, low sentence-length variation,
formulaic transitions, inflated certainty, and excessive signposting.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev

FORMULAIC = (
    "this paper", "in conclusion", "in summary", "moreover", "furthermore",
    "it is important to note", "it should be noted", "the results demonstrate",
    "the findings indicate", "a key takeaway", "in today's", "delve into",
    "underscores the importance", "plays a crucial role", "comprehensive",
    "robust framework", "seamlessly", "landscape",
)
ABSOLUTES = (
    "always", "never", "undetectable", "invisible", "guarantees", "proves",
    "definitively", "without doubt", "does not exist", "every bank",
)
SIGNPOSTS = (
    "first", "second", "third", "finally", "the main practical lesson",
    "the lesson is", "in summary", "this paper makes",
)


def strip_latex(source: str) -> str:
    source = re.sub(r"(?s)\\begin\{thebibliography\}.*?\\end\{thebibliography\}", " ", source)
    source = re.sub(r"(?s)\\begin\{(?:equation|axis|tikzpicture|table|figure)\*?\}.*?\\end\{(?:equation|axis|tikzpicture|table|figure)\*?\}", " ", source)
    source = re.sub(r"(?m)^%.*$", " ", source)
    source = re.sub(r"\\(?:section|subsection|subsubsection)\*?\{([^{}]*)\}", r" \1. ", source)
    source = re.sub(r"\\(?:cite|ref|label|url|hypersetup|title|author)\{[^{}]*\}", " ", source)
    source = re.sub(r"\\(?:textbf|emph|textit|texttt|mathrm|mathbf)\{([^{}]*)\}", r"\1", source)
    source = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", " ", source)
    source = source.replace("~", " ").replace("---", "-").replace("--", "-")
    source = re.sub(r"\$[^$]*\$", " ", source)
    source = re.sub(r"[{}&]", " ", source)
    source = re.sub(r"\\+", " ", source)
    source = re.sub(r"\s+", " ", source)
    return source.strip()


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if len(re.findall(r"[A-Za-z]+", p)) >= 5]


def count_phrases(text: str, phrases: tuple[str, ...]) -> dict[str, int]:
    low = text.lower()
    return {p: len(re.findall(r"\b" + re.escape(p) + r"\b", low)) for p in phrases if p in low}


def analyse(path: Path) -> dict:
    raw = path.read_text(errors="replace")
    text = strip_latex(raw)
    sents = sentences(text)
    lengths = [len(re.findall(r"[A-Za-z0-9]+", s)) for s in sents]
    openings = []
    for s in sents:
        words = re.findall(r"[A-Za-z]+", s.lower())
        openings.append(" ".join(words[:3]))
    opening_counts = Counter(openings)
    repeated = sum(c for c in opening_counts.values() if c > 1)
    repeated_share = repeated / max(1, len(sents))
    formulaic = count_phrases(text, FORMULAIC)
    absolutes = count_phrases(text, ABSOLUTES)
    signposts = count_phrases(text, SIGNPOSTS)
    avg = mean(lengths) if lengths else 0.0
    sd = pstdev(lengths) if len(lengths) > 1 else 0.0
    cv = sd / avg if avg else 0.0
    short_share = sum(x <= 10 for x in lengths) / max(1, len(lengths))
    long_share = sum(x >= 35 for x in lengths) / max(1, len(lengths))

    # Conservative 0-10 style-risk scale. A normal edited research paper should
    # land around 1.5-3.5. The score is intentionally interpretable, not trained.
    score = 1.0
    score += min(2.0, sum(formulaic.values()) / max(1, len(sents)) * 20)
    score += min(1.5, max(0.0, repeated_share - 0.08) * 8)
    score += 0.9 if cv < 0.38 else (0.4 if cv < 0.48 else 0.0)
    score += min(1.2, sum(absolutes.values()) * 0.3)
    score += min(1.0, max(0, sum(signposts.values()) - 5) * 0.12)
    score += 0.4 if short_share < 0.04 else 0.0
    score += 0.4 if long_share > 0.22 else 0.0
    score = round(min(10.0, score), 2)

    return {
        "file": str(path),
        "note": "Internal prose-style heuristic; not a vendor AI detector.",
        "sentences": len(sents),
        "mean_words_per_sentence": round(avg, 2),
        "sentence_length_sd": round(sd, 2),
        "sentence_length_cv": round(cv, 3),
        "short_sentence_share": round(short_share, 3),
        "long_sentence_share": round(long_share, 3),
        "repeated_opening_share": round(repeated_share, 3),
        "most_common_repeated_openings": opening_counts.most_common(8),
        "formulaic_phrases": formulaic,
        "absolute_claims": absolutes,
        "signposts": signposts,
        "style_risk_score_out_of_10": score,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    result = analyse(args.path)
    print(json.dumps(result, indent=2))
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
