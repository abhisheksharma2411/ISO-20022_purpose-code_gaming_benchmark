#!/usr/bin/env python3
"""
iso20022_gaming_bench.py -- reference implementation for the F7 benchmark
(paper: "Detecting Purpose-Code Gaming in ISO 20022 Payments").

Provides:
  * a benign message generator with a tunable rate eta of ACCIDENTAL
    data-quality defects, drawn from the failure modes PMPG reports;
  * a cost-bounded evader that applies evasion primitives P1/P2/P3 to
    minimise a published screening-probability model pi (paper eq. 1);
  * pain.001.001.09 / pacs.008.001.08 XML serialisation, optionally
    validated against the ISO 20022 XSDs;
  * detectors D0..D4 over the C1..C5 validation constraints;
  * SEL / SEL_res (paper eqs. 2, 3) with bootstrap intervals.

Run the full paper protocol with run_protocol.py, not this file directly.

EVERYTHING IS SYNTHETIC. No real payment message, customer record, alert
outcome or institution-specific parameter is used anywhere in this code.
The risk weights below are illustrative constants chosen for the study.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
from copy import copy
from dataclasses import dataclass
from xml.etree import ElementTree as ET

import numpy as np

# ===========================================================================
# Domain constants.
# Purpose codes are genuine ISO 20022 ExternalPurpose1Code members.
# The RISK WEIGHTS ARE OUR MODEL -- they are not any institution's weights,
# and we deliberately do not publish corridor-calibrated values (paper VII-A).
# ===========================================================================
PURPOSE_CODES = ["GDDS", "SUPP", "TRAD", "SALA", "CHAR", "INTC", "SERV", "OTHR"]

PURPOSE_RISK = {"GDDS": 0.10, "SUPP": 0.12, "TRAD": 0.45, "SALA": 0.08,
                "CHAR": 0.38, "INTC": 0.30, "SERV": 0.18, "OTHR": 0.35}

CATEGORY_CODES = ["CORT", "SALA", "SUPP", "TRAD", "INTC"]

CORRIDORS = [("GB", "US"), ("DE", "AE"), ("SG", "IN"), ("US", "MX"), ("FR", "TR")]
CORRIDOR_RISK = {("GB", "US"): 0.05, ("DE", "AE"): 0.35, ("SG", "IN"): 0.20,
                 ("US", "MX"): 0.25, ("FR", "TR"): 0.40}

INDUSTRIES = ["manufacturing", "logistics", "retail", "services", "ngo", "finance"]

# Plausible purpose codes per creditor industry -- the basis of constraint C3.
INDUSTRY_PURPOSE = {
    "manufacturing": {"GDDS": .45, "SUPP": .30, "TRAD": .15, "SERV": .05, "OTHR": .05},
    "logistics":     {"SERV": .40, "SUPP": .30, "TRAD": .20, "GDDS": .05, "OTHR": .05},
    "retail":        {"GDDS": .55, "SUPP": .25, "SERV": .10, "SALA": .05, "OTHR": .05},
    "services":      {"SERV": .60, "SUPP": .15, "SALA": .15, "OTHR": .10},
    "ngo":           {"CHAR": .65, "SERV": .15, "SALA": .10, "OTHR": .10},
    "finance":       {"INTC": .50, "SERV": .25, "SUPP": .15, "OTHR": .10},
}

TOWNS = ["SPRINGFIELD", "RIVERTON", "NEWPORT", "ASHFORD", "MILLBROOK", "OAKDALE"]

# Elements the screening abstraction matches names against (F_s in the paper).
SCREENED_ELEMENTS = {"Cdtr/Nm", "Dbtr/Nm", "UltmtDbtr/Nm", "UltmtCdtr/Nm",
                     "PstlAdr/TwnNm", "PstlAdr/Ctry"}
UNSCREENED_ELEMENTS = {"PstlAdr/AdrLine", "RmtInf/Ustrd", "RmtInf/Strd"}

PRIMITIVES = ["P1a", "P1b", "P1c", "P1d",
              "P2a", "P2b", "P2c", "P2d",
              "P3a", "P3b", "P3c"]
FAMILY = {p: p[:2] for p in PRIMITIVES}          # P1a -> P1

# Adversary cost: operational effort + risk that the manipulation is noticed.
PRIM_COST = {"P1a": 0.30, "P1b": 0.25, "P1c": 0.15, "P1d": 0.20,
             "P2a": 0.05, "P2b": 0.08, "P2c": 0.04, "P2d": 0.10,
             "P3a": 0.45, "P3b": 0.35, "P3c": 0.55}

# --- screening-abstraction parameters (paper IV-B) -------------------------
# CALIBRATION WARNING: SEL is a ratio of pass-through probabilities and is
# therefore very sensitive to the baseline pi_0. Never report SEL at a single
# operating point. Use --target-pi0 to solve for P_NAME, and sweep it.
P_NAME = 0.90     # P(name match | party name sits in a screened element)
PI_FLOOR = 0.15   # residual alert prob. from controls the evader cannot reach
TAU = 0.55        # risk-score alert threshold
TEMP = 0.06       # evader rationality temperature; 0.0 => perfect arg-min


# ===========================================================================
@dataclass
class Message:
    msg_id: str
    msg_type: str                 # "pain.001" | "pacs.008"
    dbtr_nm: str
    dbtr_ctry: str
    cdtr_nm: str
    cdtr_ctry: str
    cdtr_industry: str
    amount: float
    ccy: str
    purpose: str | None
    ctgy_purpose: str | None
    ultmt_dbtr_nm: str | None
    twn_nm: str | None
    ctry: str | None
    strt_nm: str | None
    adr_line: list
    rmt_ustrd: str
    name_in_screened: bool        # party of interest sits inside F_s
    name_truncated: bool
    n_splits: int
    pair_id: int
    # ground truth
    illicit: bool = False
    gamed: bool = False
    primitives: tuple = ()
    pi_0: float = 0.0
    pi_m: float = 0.0
    defect: str | None = None     # accidental defect injected, if any


# ===========================================================================
# Screening abstraction pi(x): name match over F_s + additive risk score.
# ===========================================================================
def screening_prob(m: Message) -> float:
    p_name = 0.0
    if m.illicit and m.name_in_screened:
        p_name = (0.35 / 0.90) * P_NAME if m.name_truncated else P_NAME
    s = PURPOSE_RISK.get(m.purpose, 0.32)          # absent code -> weak prior
    s += CORRIDOR_RISK.get((m.dbtr_ctry, m.cdtr_ctry), 0.25)
    s += 0.20 * min(1.0, m.amount / 250_000.0)
    s += 0.10 if m.ultmt_dbtr_nm is None else 0.0
    s += 0.08 if (m.twn_nm is None or m.ctry is None) else 0.0
    s /= m.n_splits ** 0.5                          # splitting dilutes amount
    p_score = 1.0 / (1.0 + math.exp(-8.0 * (s - TAU)))
    floor = PI_FLOOR if m.illicit else 0.0
    return 1.0 - (1.0 - p_name) * (1.0 - p_score) * (1.0 - floor)


# ===========================================================================
# Evasion primitives.
# ===========================================================================
def apply_primitive(m: Message, p: str, rng) -> Message:
    x = copy(m)
    x.adr_line = list(m.adr_line)

    if p == "P1a":                       # ultimate-party name -> RmtInf/Ustrd
        moved = x.ultmt_dbtr_nm or x.dbtr_nm
        x.rmt_ustrd = f"{x.rmt_ustrd} REF {moved}".strip()
        x.ultmt_dbtr_nm = None
        x.name_in_screened = False
    elif p == "P1b":                     # address destructuring
        x.adr_line.insert(0, f"{x.twn_nm} {x.ctry}")
        x.twn_nm = str(rng.choice(TOWNS))
        x.ctry = x.dbtr_ctry
    elif p == "P1c":                     # truncate below fuzzy-match threshold
        x.name_truncated = True
        if x.ultmt_dbtr_nm:
            x.ultmt_dbtr_nm = x.ultmt_dbtr_nm[:4]
        x.cdtr_nm = x.cdtr_nm[:4]
    elif p == "P1d":                     # drop the ultimate debtor
        x.ultmt_dbtr_nm = None
        x.name_in_screened = False
    elif p == "P2a":                     # purpose swap to lowest-risk code
        x.purpose = min(("GDDS", "SUPP", "SALA", "SERV"), key=PURPOSE_RISK.get)
    elif p == "P2b":                     # category-purpose swap
        x.ctgy_purpose = "SALA"
    elif p == "P2c":                     # omit the purpose code
        x.purpose = None
    elif p == "P2d":                     # code says one thing, text another
        x.rmt_ustrd = f"{x.rmt_ustrd} INVOICE GOODS SHIPMENT".strip()
        x.purpose = "SALA"
    elif p == "P3a":                     # message-type substitution
        x.msg_type = "pacs.008" if x.msg_type == "pain.001" else "pain.001"
        x.name_in_screened = False
    elif p == "P3b":                     # in-message structuring
        x.n_splits = int(rng.integers(3, 8))
    elif p == "P3c":                     # party-chain insertion
        x.ultmt_dbtr_nm = f"INTERMEDIARY{int(rng.integers(100, 999))}"
        x.name_in_screened = False
    return x


def best_response(m: Message, k: int, lam: float, knowledge: str, rng):
    """Evader solves paper eq. (1) over primitive subsets of size <= k.

    A perfectly rational evader concentrates on a single cheapest primitive,
    which starves the per-primitive ablation of samples. We sample from a
    softmax over admissible responses instead; TEMP -> 0 recovers the arg-min.
    TEMP is a stated methodological parameter and must be reported.
    """
    pool = (PRIMITIVES if knowledge == "grey"
            else [p for p in PRIMITIVES if not p.startswith("P2")] + ["P2c"])
    base_obj = screening_prob(m)
    cands = [((), base_obj, m)]
    for r in range(1, k + 1):
        for combo in itertools.combinations(pool, r):
            y = m
            for p in combo:
                y = apply_primitive(y, p, rng)
            obj = screening_prob(y) + lam * sum(PRIM_COST[p] for p in combo)
            if obj < base_obj:
                cands.append((combo, obj, y))
    if TEMP <= 0.0:
        combo, _, out = min(cands, key=lambda c: c[1])
    else:
        objs = np.array([c[1] for c in cands])
        w = np.exp(-(objs - objs.min()) / TEMP)
        combo, _, out = cands[int(rng.choice(len(cands), p=w / w.sum()))]
    out = copy(out)
    out.gamed = len(combo) > 0
    out.primitives = combo
    out.pi_0 = base_obj
    out.pi_m = screening_prob(out)
    return out


# ===========================================================================
# Generator.
# ===========================================================================
def generate(n, eta, rho, seed, k=2, lam=0.35, knowledge="grey"):
    rng = np.random.default_rng(seed)
    out = []
    n_pairs = max(2, n // 20)
    for i in range(n):
        dc, cc = CORRIDORS[int(rng.integers(len(CORRIDORS)))]
        ind = INDUSTRIES[int(rng.integers(len(INDUSTRIES)))]
        prof = INDUSTRY_PURPOSE[ind]
        codes = list(prof)
        probs = np.array(list(prof.values()), dtype=float)
        m = Message(
            msg_id=f"MSG{i:09d}",
            msg_type="pain.001" if rng.random() < 0.5 else "pacs.008",
            dbtr_nm=f"DEBTOR{int(rng.integers(1000, 9999))}",
            dbtr_ctry=dc,
            cdtr_nm=f"CREDITOR{int(rng.integers(1000, 9999))}",
            cdtr_ctry=cc,
            cdtr_industry=ind,
            amount=round(float(np.exp(rng.normal(10.2, 1.4))), 2),
            ccy="EUR" if dc in ("DE", "FR") else "USD",
            purpose=str(rng.choice(codes, p=probs / probs.sum())),
            ctgy_purpose=str(rng.choice(CATEGORY_CODES)),
            ultmt_dbtr_nm=(f"ULTIMATE{int(rng.integers(1000, 9999))}"
                           if rng.random() < 0.75 else None),
            twn_nm=str(rng.choice(TOWNS)),
            ctry=dc,
            strt_nm=f"STREET {int(rng.integers(1, 200))}",
            adr_line=[],
            rmt_ustrd=f"INV{int(rng.integers(1e5, 1e6))}",
            name_in_screened=True,
            name_truncated=False,
            n_splits=1,
            pair_id=int(rng.integers(0, n_pairs)),
        )
        # Accidental defects at rate eta. Mix taken from the failure modes
        # market-practice guidance reports (PMPG v1.1, Jul 2024).
        if rng.random() < eta:
            d = rng.random()
            if d < 0.35:
                m.rmt_ustrd += f" PURPOSE {m.purpose}"
                m.purpose = None
                m.defect = "purpose_in_remittance"
            elif d < 0.65:
                m.adr_line.append(str(m.twn_nm))
                m.twn_nm = None
                m.defect = "partial_destructuring"
            elif d < 0.85:
                m.ultmt_dbtr_nm = None
                m.defect = "ultimate_party_absent"
            else:
                m.ctgy_purpose = None
                m.defect = "category_absent"

        m.illicit = bool(rng.random() < rho)
        m.pi_0 = m.pi_m = screening_prob(m)
        if m.illicit:
            m = best_response(m, k, lam, knowledge, rng)
        out.append(m)
    return out


def _mean_pi0(eta, seed, knowledge, n_probe):
    probe = generate(n_probe, eta, 1.0, seed + 991, k=0,
                     lam=1.0, knowledge=knowledge)
    return float(np.mean([m.pi_0 for m in probe]))


def calibrate_p_name(target_pi0, eta, seed, knowledge="grey",
                     n_probe=4000, tol=2e-3, iters=32, verbose=True):
    """Set the screening abstraction so mean pi_0 over an UN-EVADED illicit
    sample equals target_pi0.

    Two stages, because P_NAME alone cannot reach low targets: the risk-score
    leg and PI_FLOOR put a floor on pi_0. Stage 1 bisects P_NAME. If the
    target is still below what P_NAME=0 achieves, stage 2 raises TAU (the
    risk-score threshold), which lowers the score leg. Both solved values are
    recorded in the results config and MUST be reported with any SEL number.
    """
    global P_NAME, TAU
    lo, hi, cur = 0.0, 1.0, float("nan")
    for _ in range(iters):
        P_NAME = (lo + hi) / 2
        cur = _mean_pi0(eta, seed, knowledge, n_probe)
        if abs(cur - target_pi0) < tol:
            break
        if cur < target_pi0:
            lo = P_NAME
        else:
            hi = P_NAME

    if cur - target_pi0 > tol:            # stage 2: unreachable via P_NAME
        P_NAME = 0.0
        t_lo, t_hi = TAU, TAU + 3.0
        for _ in range(iters):
            TAU = (t_lo + t_hi) / 2
            cur = _mean_pi0(eta, seed, knowledge, n_probe)
            if abs(cur - target_pi0) < tol:
                break
            if cur > target_pi0:
                t_lo = TAU
            else:
                t_hi = TAU
        # restore a name-matching leg proportional to what is left of the budget
        lo, hi = 0.0, 1.0
        for _ in range(iters):
            P_NAME = (lo + hi) / 2
            cur = _mean_pi0(eta, seed, knowledge, n_probe)
            if abs(cur - target_pi0) < tol:
                break
            if cur < target_pi0:
                lo = P_NAME
            else:
                hi = P_NAME

    if verbose:
        ok = "OK" if abs(cur - target_pi0) < 0.02 else "NOT REACHED"
        print(f"[calibrate] P_NAME={P_NAME:.4f} TAU={TAU:.4f} PI_FLOOR={PI_FLOOR:.3f}"
              f" -> mean pi_0={cur:.4f} (target {target_pi0}) [{ok}]", flush=True)
        if ok != "OK":
            print("[calibrate] lower --pi-floor to reach this target; "
                  "pi_0 cannot go below the floor.", flush=True)
    return P_NAME, cur


# ===========================================================================
# ISO 20022 XML serialisation.
# ===========================================================================
NS_PAIN = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"
NS_PACS = "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"
STAMP = "2026-11-16T09:00:00"          # fixed: keeps output deterministic


def _sub(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, tag, attrs)
    if text is not None:
        e.text = str(text)
    return e


def _postal(parent, m: Message):
    """PstlAdr children in ISO 20022 sequence order."""
    adr = _sub(parent, "PstlAdr")
    if m.strt_nm:
        _sub(adr, "StrtNm", m.strt_nm)
    if m.twn_nm:
        _sub(adr, "TwnNm", m.twn_nm)
    if m.ctry:
        _sub(adr, "Ctry", m.ctry)
    for line in m.adr_line:
        _sub(adr, "AdrLine", line)


def to_xml(m: Message) -> str:
    """Serialise to pain.001.001.09 or pacs.008.001.08.

    Element order follows the ISO 20022 message sequences. Confirm with
    --xsd-dir; the XSDs are not redistributable and must be downloaded
    from iso20022.org.
    """
    per = round(m.amount / max(1, m.n_splits), 2)

    if m.msg_type == "pain.001":
        doc = ET.Element("Document", {"xmlns": NS_PAIN})
        root = _sub(doc, "CstmrCdtTrfInitn")

        hdr = _sub(root, "GrpHdr")
        _sub(hdr, "MsgId", m.msg_id)
        _sub(hdr, "CreDtTm", STAMP)
        _sub(hdr, "NbOfTxs", max(1, m.n_splits))
        _sub(hdr, "CtrlSum", f"{m.amount:.2f}")
        _sub(_sub(hdr, "InitgPty"), "Nm", m.dbtr_nm)

        pmt = _sub(root, "PmtInf")
        _sub(pmt, "PmtInfId", m.msg_id + "P")
        _sub(pmt, "PmtMtd", "TRF")
        _sub(pmt, "NbOfTxs", max(1, m.n_splits))
        _sub(pmt, "CtrlSum", f"{m.amount:.2f}")
        if m.ctgy_purpose:
            tpinf = _sub(pmt, "PmtTpInf")
            _sub(_sub(tpinf, "CtgyPurp"), "Cd", m.ctgy_purpose)
        _sub(_sub(pmt, "ReqdExctnDt"), "Dt", STAMP[:10])
        dbtr = _sub(pmt, "Dbtr")
        _sub(dbtr, "Nm", m.dbtr_nm)
        _postal(dbtr, m)
        acct = _sub(pmt, "DbtrAcct")
        _sub(_sub(_sub(acct, "Id"), "Othr"), "Id", "ACC" + m.msg_id[-8:])
        _sub(_sub(_sub(pmt, "DbtrAgt"), "FinInstnId"), "BICFI", "BANKGB2LXXX")

        for j in range(max(1, m.n_splits)):
            tx = _sub(pmt, "CdtTrfTxInf")
            pid = _sub(tx, "PmtId")
            _sub(pid, "InstrId", f"{m.msg_id}-{j}")
            _sub(pid, "EndToEndId", f"{m.msg_id}-{j}")
            _sub(_sub(tx, "Amt"), "InstdAmt", f"{per:.2f}", Ccy=m.ccy)
            _sub(_sub(_sub(tx, "CdtrAgt"), "FinInstnId"), "BICFI", "BANKUS33XXX")
            cdtr = _sub(tx, "Cdtr")
            _sub(cdtr, "Nm", m.cdtr_nm)
            _postal(cdtr, m)
            if m.ultmt_dbtr_nm:
                _sub(_sub(tx, "UltmtCdtr"), "Nm", m.ultmt_dbtr_nm)
            if m.purpose:
                _sub(_sub(tx, "Purp"), "Cd", m.purpose)
            if m.rmt_ustrd:
                _sub(_sub(tx, "RmtInf"), "Ustrd", m.rmt_ustrd)

    else:
        doc = ET.Element("Document", {"xmlns": NS_PACS})
        root = _sub(doc, "FIToFICstmrCdtTrf")

        hdr = _sub(root, "GrpHdr")
        _sub(hdr, "MsgId", m.msg_id)
        _sub(hdr, "CreDtTm", STAMP)
        _sub(hdr, "NbOfTxs", max(1, m.n_splits))
        _sub(_sub(hdr, "SttlmInf"), "SttlmMtd", "INDA")

        for j in range(max(1, m.n_splits)):
            tx = _sub(root, "CdtTrfTxInf")
            pid = _sub(tx, "PmtId")
            _sub(pid, "InstrId", f"{m.msg_id}-{j}")
            _sub(pid, "EndToEndId", f"{m.msg_id}-{j}")
            _sub(pid, "TxId", f"{m.msg_id}-{j}")
            if m.ctgy_purpose:
                _sub(_sub(_sub(tx, "PmtTpInf"), "CtgyPurp"), "Cd", m.ctgy_purpose)
            _sub(tx, "IntrBkSttlmAmt", f"{per:.2f}", Ccy=m.ccy)
            _sub(tx, "ChrgBr", "SLEV")
            if m.ultmt_dbtr_nm:
                _sub(_sub(tx, "UltmtDbtr"), "Nm", m.ultmt_dbtr_nm)
            dbtr = _sub(tx, "Dbtr")
            _sub(dbtr, "Nm", m.dbtr_nm)
            _postal(dbtr, m)
            _sub(_sub(_sub(tx, "DbtrAgt"), "FinInstnId"), "BICFI", "BANKGB2LXXX")
            _sub(_sub(_sub(tx, "CdtrAgt"), "FinInstnId"), "BICFI", "BANKUS33XXX")
            cdtr = _sub(tx, "Cdtr")
            _sub(cdtr, "Nm", m.cdtr_nm)
            _postal(cdtr, m)
            if m.purpose:
                _sub(_sub(tx, "Purp"), "Cd", m.purpose)
            if m.rmt_ustrd:
                _sub(_sub(tx, "RmtInf"), "Ustrd", m.rmt_ustrd)

    return ET.tostring(doc, encoding="unicode")


def write_corpus(msgs, path, limit=None):
    """Write one XML document per line (JSONL of XML), plus a labels file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    sel = msgs if limit is None else msgs[:limit]
    with open(path, "w") as f:
        for m in sel:
            f.write(json.dumps({"msg_id": m.msg_id, "xml": to_xml(m)}) + "\n")
    with open(path.replace(".jsonl", "_labels.jsonl"), "w") as f:
        for m in sel:
            f.write(json.dumps({
                "msg_id": m.msg_id, "msg_type": m.msg_type,
                "illicit": m.illicit, "gamed": m.gamed,
                "primitives": list(m.primitives), "defect": m.defect,
                "pi_0": m.pi_0, "pi_m": m.pi_m}) + "\n")
    return len(sel)


def validate_corpus(msgs, xsd_dir, limit=500):
    """Validate a sample against the ISO 20022 XSDs.

    Requires lxml and the schema files. The XSDs are not redistributable --
    download pain.001.001.09 and pacs.008.001.08 from iso20022.org and place
    them in xsd_dir. Returns (n_checked, n_valid, [first errors]).
    """
    try:
        from lxml import etree
    except ImportError:
        return (0, 0, ["lxml not installed: pip install lxml"])
    schemas = {}
    for key, fn in (("pain.001", "pain.001.001.09.xsd"),
                    ("pacs.008", "pacs.008.001.08.xsd")):
        p = os.path.join(xsd_dir, fn)
        if not os.path.exists(p):
            return (0, 0, [f"missing schema: {p}"])
        schemas[key] = etree.XMLSchema(etree.parse(p))
    ok, errs = 0, []
    sample = msgs[:limit]
    for m in sample:
        try:
            schemas[m.msg_type].assertValid(etree.fromstring(to_xml(m).encode()))
            ok += 1
        except Exception as e:                       # noqa: BLE001
            if len(errs) < 10:
                errs.append(f"{m.msg_id} ({m.msg_type}): {e}")
    return (len(sample), ok, errs)


# ===========================================================================
# Validation constraints C1..C5 -> detector features.
# ===========================================================================
COUNTRY_TOKENS = {c for pair in CORRIDORS for c in pair}

FEATURE_NAMES = ["c1_codelist", "c2_completeness", "c3_crossfield",
                 "c4_code_narrative", "c5_longitudinal", "purpose_absent",
                 "len_rmt", "n_adrline", "n_splits", "ultmt_absent",
                 "name_short"]


def build_history(msgs):
    h = {}
    for m in msgs:
        if not m.gamed:
            h.setdefault(m.pair_id, {})
            h[m.pair_id][m.purpose] = h[m.pair_id].get(m.purpose, 0) + 1
    return h


def features(m: Message, history: dict):
    c1 = 0.0 if (m.purpose is None or m.purpose in PURPOSE_RISK) else 1.0
    adr_tokens = set(" ".join(m.adr_line).split())
    adr_has_geo = float(bool(adr_tokens & (COUNTRY_TOKENS | set(TOWNS))))
    c2 = float(m.twn_nm is None) + float(m.ctry is None) + adr_has_geo
    prof = INDUSTRY_PURPOSE[m.cdtr_industry]
    c3 = (1.0 - (prof.get(m.purpose, 0.0) if m.purpose else 0.0)) \
        + float(m.ultmt_dbtr_nm is None)
    c4 = float(m.purpose == "SALA"
               and any(w in m.rmt_ustrd for w in ("GOODS", "INVOICE", "SHIPMENT")))
    hist = history.get(m.pair_id, {})
    tot = sum(hist.values()) or 1
    c5 = 1.0 - (hist.get(m.purpose, 0) / tot)
    return [c1, c2, c3, c4, c5,
            float(m.purpose is None), float(len(m.rmt_ustrd)),
            float(len(m.adr_line)), float(m.n_splits),
            float(m.ultmt_dbtr_nm is None), float(len(m.cdtr_nm) <= 5)]


def raw_features(m: Message):
    """Features for D2, the naive supervised baseline.

    NEVER put PURPOSE_RISK or CORRIDOR_RISK in here. Those are the evader's
    own objective terms and leak the label -- they drove D2 to AUC ~0.998 in
    an early version. One-hot codes only.
    """
    def onehot(v, vocab):
        z = [0.0] * (len(vocab) + 1)
        z[vocab.index(v) if v in vocab else len(vocab)] = 1.0
        return z
    corr_vocab = [f"{a}{b}" for a, b in CORRIDORS]
    return (onehot(m.purpose, PURPOSE_CODES)
            + onehot(m.ctgy_purpose, CATEGORY_CODES)
            + onehot(f"{m.dbtr_ctry}{m.cdtr_ctry}", corr_vocab)
            + [math.log1p(m.amount), float(m.n_splits),
               float(m.ultmt_dbtr_nm is None), float(m.twn_nm is None),
               float(len(m.rmt_ustrd))])


# ===========================================================================
# Detectors and metrics.
# ===========================================================================
def _z(v):
    return (v - v.mean()) / (v.std() + 1e-9)


def _rank(v):
    """Normalised ranks in [0,1]. Ties get distinct ranks, which is harmless
    here because both combined scores are near-continuous."""
    return np.argsort(np.argsort(v)) / max(1, len(v) - 1)


def detector_scores(msgs, seed=0, train_mask=None):
    """Return ({name: score array}, y). train_mask selects rows the LEARNED
    detectors (D2, D3) may train on; scores are produced for every row."""
    from sklearn.ensemble import IsolationForest, HistGradientBoostingClassifier

    hist = build_history(msgs)
    X = np.array([features(m, hist) for m in msgs])
    R = np.array([raw_features(m) for m in msgs])
    y = np.array([int(m.gamed) for m in msgs])
    if train_mask is None:
        train_mask = np.ones(len(msgs), dtype=bool)

    d0 = X[:, 0] + (X[:, 1] > 1).astype(float)                 # C1 + hard C2
    d1 = X[:, 0] + 0.5 * X[:, 1] + X[:, 2] + 1.5 * X[:, 3]     # rules C1-C4

    tr = train_mask & (np.arange(len(msgs)) % 2 == 0)
    if y[tr].sum() >= 10 and (y[tr] == 0).sum() >= 10:
        gb = HistGradientBoostingClassifier(random_state=seed,
                                            max_iter=150).fit(R[tr], y[tr])
        d2 = gb.predict_proba(R)[:, 1]
    else:
        d2 = np.zeros(len(msgs))

    benign_tr = train_mask & (y == 0)
    iso = IsolationForest(random_state=seed, n_estimators=200,
                          contamination=0.05).fit(X[benign_tr])
    d3 = -iso.score_samples(X)

    # D4 combines D1 and D3 by RANK AVERAGING, not by summing z-scores.
    # d1 is a small-support sum of rule violations and d3 is a continuous
    # isolation-forest score; their scales and skews differ enough that
    # z-scoring lets d3's tail dominate. Equal-weight rank averaging is
    # scale-free and has no tuned parameter, so it cannot be fitted to the
    # evaluation set. Measured at n=40k, eta=0.15, pi_0=0.45, seed 7:
    # z-sum 0.7675, rank-average 0.7753, rank-max 0.7711 (D1 0.7600,
    # D3 0.7562). A weighted rank blend scored marginally higher at w=0.3,
    # but the weight would have been chosen on the test set, so we do not
    # use it. This choice is reported in the paper.
    d4 = _rank(d1) + _rank(d3)
    return {"D0": d0, "D1": d1, "D2": d2, "D3": d3, "D4": d4}, y


def tpr_at_budget(score, y, budget):
    thr = np.quantile(score, 1.0 - budget)
    return float(((score >= thr) & (y == 1)).sum() / max(1, int(y.sum())))


def alerts_per_million_benign(score, y, budget):
    thr = np.quantile(score, 1.0 - budget)
    benign = y == 0
    return float(1e6 * ((score >= thr) & benign).sum() / max(1, benign.sum()))


def sel_table(msgs, score, y, budget=0.01, n_boot=1000, seed=0, min_n=30):
    """SEL and SEL_res per primitive, with bootstrap intervals (eqs. 2, 3)."""
    rng = np.random.default_rng(seed)
    thr = np.quantile(score, 1.0 - budget)
    flagged = score >= thr
    base = np.array([i for i, m in enumerate(msgs) if m.illicit and not m.gamed],
                    dtype=int)
    delta0 = float(flagged[base].mean()) if len(base) else 0.0

    out = {"_baseline": {"delta0": delta0, "n_unevaded_illicit": int(len(base))}}
    for p in PRIMITIVES:
        idx = np.array([i for i, m in enumerate(msgs) if p in m.primitives],
                       dtype=int)
        if len(idx) < min_n:
            continue
        pi0 = np.array([msgs[i].pi_0 for i in idx])
        pim = np.array([msgs[i].pi_m for i in idx])
        fl = flagged[idx].astype(float)

        def _stats(sel):
            a, b, d = pi0[sel].mean(), pim[sel].mean(), fl[sel].mean()
            s = (1 - b) / max(1e-9, 1 - a)
            sr = ((1 - b) * (1 - d)) / max(1e-9, (1 - a) * (1 - delta0))
            return s, sr

        s, sr = _stats(np.arange(len(idx)))
        boots = np.array([_stats(rng.integers(0, len(idx), len(idx)))
                          for _ in range(n_boot)])
        out[p] = {"n": int(len(idx)),
                  "SEL": float(s),
                  "SEL_lo": float(np.percentile(boots[:, 0], 2.5)),
                  "SEL_hi": float(np.percentile(boots[:, 0], 97.5)),
                  "SEL_res": float(sr),
                  "SEL_res_lo": float(np.percentile(boots[:, 1], 2.5)),
                  "SEL_res_hi": float(np.percentile(boots[:, 1], 97.5)),
                  "detect_rate": float(fl.mean())}
    return out


def roc_points(score, y, n=40):
    """FPR/TPR pairs on a log-spaced FPR grid, ready for pgfplots."""
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y, score)
    grid = np.concatenate([np.logspace(-4, 0, n), [1.0]])
    return [(float(g), float(np.interp(g, fpr, tpr))) for g in grid]


def evaluate(msgs, seed=0, budgets=(0.01, 0.001), boot=1000, want_roc=True):
    from sklearn.metrics import roc_auc_score
    scores, y = detector_scores(msgs, seed=seed)
    if y.sum() == 0:
        raise SystemExit("no gamed messages: raise --rho or lower --lam")
    res, roc = {}, {}
    for name, s in scores.items():
        row = {"auc": float(roc_auc_score(y, s))}
        for b in budgets:
            row[f"tpr@{b}"] = tpr_at_budget(s, y, b)
            row[f"benign_alerts_per_M@{b}"] = alerts_per_million_benign(s, y, b)
        res[name] = row
        if want_roc:
            roc[name] = roc_points(s, y)
    return {"detectors": res, "roc": roc,
            "sel": sel_table(msgs, scores["D4"], y, seed=seed, n_boot=boot),
            "n": len(msgs), "n_gamed": int(y.sum()),
            "n_illicit": int(sum(m.illicit for m in msgs))}


def evaluate_loo(msgs, seed=0):
    """Leave-one-primitive-family-out. Learned detectors never see the family
    they are scored on. This is the paper's headline number."""
    from sklearn.metrics import roc_auc_score
    out = {}
    gamed = np.array([m.gamed for m in msgs])
    for fam in ("P1", "P2", "P3"):
        in_fam = np.array([any(FAMILY[p] == fam for p in m.primitives)
                           for m in msgs])
        if in_fam.sum() < 30:
            out[fam] = {"skipped": f"only {int(in_fam.sum())} samples"}
            continue
        train_mask = ~in_fam                    # withhold this family entirely
        keep = (~gamed) | in_fam                # score benign + this family
        scores, y = detector_scores(msgs, seed=seed, train_mask=train_mask)
        yk = y[keep]
        out[fam] = {"n_family": int(in_fam.sum()),
                    **{name: float(roc_auc_score(yk, s[keep]))
                       for name, s in scores.items()}}
    return out


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="F7 ISO 20022 gaming benchmark")
    ap.add_argument("--n", type=int, default=50_000)
    ap.add_argument("--eta", type=float, default=0.15, help="accidental defect rate")
    ap.add_argument("--rho", type=float, default=0.02, help="illicit fraction")
    ap.add_argument("--k", type=int, default=2, help="evader budget")
    ap.add_argument("--lam", type=float, default=0.35, help="evader cost weight")
    ap.add_argument("--temp", type=float, default=0.06, help="evader temperature")
    ap.add_argument("--knowledge", choices=["black", "grey"], default="grey")
    ap.add_argument("--pi-floor", type=float, default=0.15)
    ap.add_argument("--target-pi0", type=float, default=None,
                    help="calibrate P_NAME to this baseline alert probability")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--emit-xml", type=int, default=0,
                    help="write this many messages as ISO 20022 XML")
    ap.add_argument("--xsd-dir", default=None,
                    help="dir with pain.001.001.09.xsd / pacs.008.001.08.xsd")
    ap.add_argument("--loo", action="store_true", help="also run leave-one-out")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    globals()["PI_FLOOR"] = a.pi_floor
    globals()["TEMP"] = a.temp
    if a.target_pi0 is not None:
        calibrate_p_name(a.target_pi0, a.eta, a.seed, a.knowledge)

    msgs = generate(a.n, a.eta, a.rho, a.seed, a.k, a.lam, a.knowledge)
    res = evaluate(msgs, seed=a.seed, boot=a.boot)
    if a.loo:
        res["loo"] = evaluate_loo(msgs, seed=a.seed)
    if a.emit_xml:
        p = os.path.join(a.out, f"corpus_seed{a.seed}.jsonl")
        res["xml_written"] = write_corpus(msgs, p, limit=a.emit_xml)
        res["xml_path"] = p
    if a.xsd_dir:
        n, ok, errs = validate_corpus(msgs, a.xsd_dir)
        res["xsd"] = {"checked": n, "valid": ok, "errors": errs}

    res["config"] = vars(a)
    res["config"]["solved_P_NAME"] = P_NAME
    res["config"]["solved_TAU"] = TAU
    if res["sel"]["_baseline"]["n_unevaded_illicit"] < 200:
        res["warning"] = ("few un-evaded illicit messages: the SEL_res "
                          "baseline delta0 is noisy. Raise --n or --rho.")
        print("[warn]", res["warning"])
    res["config_hash"] = hashlib.sha256(
        json.dumps(res["config"], sort_keys=True).encode()).hexdigest()[:12]
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"run_{res['config_hash']}.json")
    with open(path, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res["detectors"], indent=2))
    print(f"gamed {res['n_gamed']} / illicit {res['n_illicit']} / n {res['n']}")
    print("->", path)


if __name__ == "__main__":
    main()
