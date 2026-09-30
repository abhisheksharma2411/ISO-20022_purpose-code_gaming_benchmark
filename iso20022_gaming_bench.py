#!/usr/bin/env python3
"""
iso20022_gaming_bench.py -- v3: message gaming in ISO 20022 payments.

Third harness revision (30 Sep 2026). Changes from v2, each answering a
reviewer objection:

  * Pairs have latent behaviour. Every debtor-creditor pair carries a stable
    purpose profile, a preferred message path, a batching habit, a party-chain
    pattern (which ultimate names it uses), an amount scale, and a volume
    weight. Messages are generated in time order and carry a timestamp t.
  * Every history feature is computed from the pair's STRICTLY EARLIER
    messages only, in a single streaming pass, with no label.
  * Temporal protocol: earliest 60% of each run trains, next 20% validates
    (alert thresholds are frozen there), latest 20% tests. Nothing is
    cross-fitted any more.
  * Paired counterfactual SEL: every gamed record keeps its unmanipulated
    original x, which is scored by the same detector with the same prior
    history, so residual SEL no longer depends on a small no-edit control
    group.
  * Splitting (P3b) dilutes only the amount term of the score leg, one child
    at a time; attempt-level alerting (any child alerted) is evaluated too.
  * Screening coverage depends on the message path: the interbank leg does
    not read ultimate parties in this abstraction, so P3a's effect flows
    through coverage rather than through a hard-coded flag. Route choice is
    a per-record capability. Admissibility is checked per record.
  * A history-only positive-control detector D7 uses prior pair behaviour.
  * Uncertainty is a pair-clustered bootstrap over the test window.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import xml.etree.ElementTree as ET
from copy import copy
from dataclasses import dataclass, field, asdict

import numpy as np

# ===========================================================================
# Constants. Risk weights are the benchmark's own illustrative constants.
# ===========================================================================
PURPOSE_CODES = ["GDDS", "SUPP", "TRAD", "SALA", "CHAR", "INTC", "SERV", "OTHR"]
PURPOSE_RISK = {"GDDS": 0.10, "SUPP": 0.12, "TRAD": 0.45, "SALA": 0.08,
                "CHAR": 0.38, "INTC": 0.30, "SERV": 0.18, "OTHR": 0.35}
CATEGORY_CODES = ["CORT", "SALA", "SUPP", "TRAD", "INTC"]
CORRIDORS = [("GB", "US"), ("DE", "AE"), ("SG", "IN"), ("US", "MX"), ("FR", "TR")]
CORRIDOR_RISK = {("GB", "US"): 0.05, ("DE", "AE"): 0.35, ("SG", "IN"): 0.20,
                 ("US", "MX"): 0.25, ("FR", "TR"): 0.40}
INDUSTRIES = ["manufacturing", "logistics", "retail", "services", "ngo", "finance"]
INDUSTRY_PURPOSE = {
    "manufacturing": {"GDDS": .45, "SUPP": .30, "TRAD": .15, "SERV": .05, "OTHR": .05},
    "logistics":     {"SERV": .40, "SUPP": .30, "TRAD": .20, "GDDS": .05, "OTHR": .05},
    "retail":        {"GDDS": .55, "SUPP": .25, "SERV": .10, "SALA": .05, "OTHR": .05},
    "services":      {"SERV": .60, "SUPP": .15, "SALA": .15, "OTHR": .10},
    "ngo":           {"CHAR": .65, "SERV": .15, "SALA": .10, "OTHR": .10},
    "finance":       {"INTC": .50, "SERV": .25, "SUPP": .15, "OTHR": .10},
}
TOWNS = ["SPRINGFIELD", "RIVERTON", "NEWPORT", "ASHFORD", "MILLBROOK", "OAKDALE"]
RMT_WORDS = ["REF", "PAYMENT", "ORDER", "CONTRACT", "SERVICE", "FEE", "PO",
             "ACCOUNT", "MONTHLY", "SETTLEMENT", "BALANCE", "PERIOD", "NO"]
_LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# Elements the screening abstraction matches listed names against, by path.
# Assumption (stated in the paper): the interbank leg screens the debtor and
# creditor names but not ultimate parties.
SCREENED = {"pain.001": {"Dbtr/Nm", "Cdtr/Nm", "UltmtDbtr/Nm"},
            "pacs.008": {"Dbtr/Nm", "Cdtr/Nm"}}

PRIMITIVES = ["P1a", "P1b", "P1c", "P1d", "P2a", "P2b", "P2c", "P2d",
              "P3a", "P3b", "P3c"]
FAMILY = {p: p[:2] for p in PRIMITIVES}
PRIM_COST = {"P1a": 0.30, "P1b": 0.25, "P1c": 0.15, "P1d": 0.20,
             "P2a": 0.05, "P2b": 0.08, "P2c": 0.04, "P2d": 0.10,
             "P3a": 0.45, "P3b": 0.35, "P3c": 0.55}
# Pre-registered from the primitive definitions BEFORE any v3 result was
# seen (analysis/primitive_labels.json carries the rationale): does the edit
# make two elements of the same message, or an element and the creditor's
# static profile, inconsistent with each other?
CONTRADICTION = {"P1a": 0, "P1b": 1, "P1c": 0, "P1d": 0, "P2a": 1, "P2b": 1,
                 "P2c": 0, "P2d": 1, "P3a": 0, "P3b": 0, "P3c": 0}
CAPABILITY = {p: ("route choice" if p == "P3a" else "originator or PSP")
              for p in PRIMITIVES}

# --- screening-abstraction parameters; calibrated by calibrate() -----------
P_NAME = 0.90
PI_FLOOR = 0.10
TAU = 0.55
TEMP = 0.10


@dataclass
class GenConfig:
    """Generator configuration. A is the main setting; B is an independently
    parameterised shift used only as a test distribution."""
    name: str = "A"
    pairs_per: int = 20                 # n / number of pairs
    pair_concentration: float = 1.0     # Dirichlet alpha for pair volumes
    profile_alpha: float = 20.0         # concentration around industry profile
    profile_perturb: float = 0.0        # mix profile with uniform
    industry_weights: tuple = (1, 1, 1, 1, 1, 1)
    corridor_weights: tuple = (1, 1, 1, 1, 1)
    path_pref_beta: tuple = (2.0, 2.0)  # per-pair P(pain.001)
    batch_rate: float = 0.30            # P(a pain.001 file is batched), scaled per pair
    batch_size_range: tuple = (2, 49)   # typical size drawn per pair (log-uniform)
    batch_tail: float = 0.10            # share of batched files drawn from 50-200
    ultimate_beta: tuple = (3.0, 1.0)   # per-pair P(ultimate debtor present)
    ult_names: tuple = (1, 3)           # ultimate names a pair uses
    amount_logmean: float = 10.2
    amount_pair_sd: float = 0.5
    amount_msg_sd: float = 1.2
    defect_mix: tuple = (0.35, 0.30, 0.20, 0.15)
    rmt_words_max: int = 6
    rmt_second_ref: float = 0.3
    name_len: tuple = (4, 17)
    route_choice_rate: float = 0.30     # illicit records whose actor can pick the path
    listed_ultimate_share: float = 0.5  # listed party is the ultimate debtor


CONFIG_A = GenConfig()
CONFIG_B = GenConfig(name="B", pairs_per=30, pair_concentration=0.5,
                     profile_alpha=8.0, profile_perturb=0.2,
                     industry_weights=(2, 1, 1, 2, 1, 1),
                     corridor_weights=(1, 2, 2, 1, 1), path_pref_beta=(1.5, 3.0),
                     batch_rate=0.45, batch_size_range=(2, 80), batch_tail=0.2,
                     ultimate_beta=(2.0, 1.5), ult_names=(1, 5),
                     amount_logmean=10.6, amount_pair_sd=0.7, amount_msg_sd=1.5,
                     defect_mix=(0.25, 0.35, 0.25, 0.15), rmt_words_max=10,
                     rmt_second_ref=0.5, name_len=(3, 24),
                     route_choice_rate=0.5, listed_ultimate_share=0.6)
CONFIGS = {"A": CONFIG_A, "B": CONFIG_B}


def _party_name(rng, cfg):
    return "".join(rng.choice(_LETTERS, int(rng.integers(*cfg.name_len))))


def _remittance(rng, cfg):
    rmt = f"INV{int(rng.integers(1e5, 1e6))}"
    nw = int(rng.integers(0, cfg.rmt_words_max + 1))
    if nw:
        rmt += " " + " ".join(rng.choice(RMT_WORDS, nw))
    if rng.random() < cfg.rmt_second_ref:
        rmt += f" {int(rng.integers(1e3, 1e8))}"
    return rmt


# ===========================================================================
# Records.
# ===========================================================================
@dataclass
class Pair:
    pair_id: int
    dbtr_nm: str
    dbtr_ctry: str
    cdtr_nm: str
    cdtr_ctry: str
    industry: str
    purpose_codes: list
    purpose_probs: np.ndarray
    p_pain: float
    batch_p: float
    batch_mu: float
    p_ult: float
    ult_names: list
    amount_mu: float
    twn_nm: str
    strt_nm: str


@dataclass
class Message:
    msg_id: str
    t: int
    pair_id: int
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
    n_splits: int
    listed_party: str | None = None   # "debtor" | "ultimate" | None
    listed_nm: str | None = None
    name_truncated: bool = False
    route_choice: bool = False
    illicit: bool = False
    gamed: bool = False
    primitives: tuple = ()
    pi_0: float = 0.0
    pi_m: float = 0.0
    defect: str | None = None
    orig: "Message | None" = None


def listed_in_screened(m: Message) -> bool:
    """Does the listed party's name sit in an element the current path
    screens? P1a moves it out, P1d omits it, P3c replaces it, P3a changes the
    path's screened set."""
    if not m.illicit or m.listed_party is None:
        return False
    if m.listed_party == "debtor":
        return "Dbtr/Nm" in SCREENED[m.msg_type]
    return (m.ultmt_dbtr_nm is not None and "UltmtDbtr/Nm" in SCREENED[m.msg_type]
            and (m.ultmt_dbtr_nm == m.listed_nm or m.name_truncated
                 and m.listed_nm.startswith(m.ultmt_dbtr_nm)))


# ===========================================================================
# Screening abstraction pi(x).
# ===========================================================================
def _score(m: Message) -> float:
    a_child = m.amount / max(1, m.n_splits)          # splitting dilutes the amount term only
    s = PURPOSE_RISK.get(m.purpose, 0.32)
    s += CORRIDOR_RISK.get((m.dbtr_ctry, m.cdtr_ctry), 0.25)
    s += 0.20 * min(1.0, a_child / 250_000.0)
    s += 0.10 if m.ultmt_dbtr_nm is None else 0.0
    s += 0.08 if (m.twn_nm is None or m.ctry is None) else 0.0
    return s


def _legs(m: Message):
    p_name = 0.0
    if listed_in_screened(m):
        p_name = (0.35 / 0.90) * P_NAME if m.name_truncated else P_NAME
    p_score = 1.0 / (1.0 + math.exp(-8.0 * (_score(m) - TAU)))
    floor = PI_FLOOR if m.illicit else 0.0
    return p_name, p_score, floor


def screening_prob(m: Message) -> float:
    """Per-message alert probability (the evader's objective)."""
    p_name, p_score, floor = _legs(m)
    return 1.0 - (1.0 - p_name) * (1.0 - p_score) * (1.0 - floor)


def screening_prob_attempt(m: Message) -> float:
    """Attempt-level alert probability: the name leg and the residual floor
    act once per payment attempt, the score leg once per child transaction,
    and the attempt is alerted if any child is."""
    p_name, p_score, floor = _legs(m)
    return 1.0 - (1.0 - p_name) * (1.0 - floor) * (1.0 - p_score) ** max(1, m.n_splits)


# ===========================================================================
# Evasion primitives, admissibility, best response.
# ===========================================================================
def apply_primitive(m: Message, p: str, rng, cfg: GenConfig) -> Message:
    """Apply one primitive. Invariants: amount total, currency, debtor and
    creditor countries, and the economic originator and beneficiary are
    unchanged by every primitive. P3a changes the message path (single
    transactions only), P3b the decomposition, P3c the represented party
    chain (an intermediary replaces the ultimate party element)."""
    x = copy(m)
    x.adr_line = list(m.adr_line)
    if p == "P1a":                       # ultimate-party name -> RmtInf/Ustrd
        x.rmt_ustrd = f"{x.rmt_ustrd} REF {x.ultmt_dbtr_nm}".strip()
        x.ultmt_dbtr_nm = None
    elif p == "P1b":                     # true town+country into a free-text line;
        x.adr_line.insert(0, f"{x.twn_nm} {x.ctry}")   # structured town now disagrees
        x.twn_nm = str(rng.choice([t for t in TOWNS if t != x.twn_nm]))
    elif p == "P1c":                     # truncate the LISTED party's name
        if x.listed_party == "ultimate":
            if x.ultmt_dbtr_nm:              # no-op if an earlier edit removed it
                x.ultmt_dbtr_nm = x.ultmt_dbtr_nm[:4]; x.name_truncated = True
        else:
            x.dbtr_nm = x.dbtr_nm[:4]; x.name_truncated = True
    elif p == "P1d":                     # omit the ultimate debtor
        x.ultmt_dbtr_nm = None
    elif p == "P2a":                     # purpose swap to the lowest-weight plausible code
        x.purpose = min(("GDDS", "SUPP", "SALA", "SERV"), key=PURPOSE_RISK.get)
    elif p == "P2b":                     # category-purpose swap
        x.ctgy_purpose = "SALA"
    elif p == "P2c":                     # omit the purpose code
        x.purpose = None
    elif p == "P2d":                     # code says one thing, narrative another
        x.rmt_ustrd = f"{x.rmt_ustrd} INVOICE GOODS SHIPMENT".strip()
        x.purpose = "SALA"
    elif p == "P3a":                     # same payment intent, other path
        x.msg_type = "pacs.008" if x.msg_type == "pain.001" else "pain.001"
    elif p == "P3b":                     # decompose into 3-7x more children, capped at 200
        x.n_splits = min(200, max(x.n_splits, 1) * int(rng.integers(3, 8)))
    elif p == "P3c":                     # an intermediary replaces the ultimate party
        x.ultmt_dbtr_nm = _party_name(rng, cfg)
    return x


def admissible(m: Message, knowledge: str) -> list:
    """Per-record admissible set. Black-box adversaries lack the targeted code
    substitutions. P1a/P1d/P3c need an ultimate-party element to act on. P3a
    needs route choice and a single-transaction payment. P3b is file
    decomposition, so it needs a pain.001 file."""
    pool = []
    for p in PRIMITIVES:
        if knowledge == "black" and p in ("P2a", "P2b", "P2d"):
            continue
        if p in ("P1a", "P1d", "P3c") and m.ultmt_dbtr_nm is None:
            continue
        if p == "P1c" and m.listed_party == "ultimate" and m.ultmt_dbtr_nm is None:
            continue
        if p == "P3a" and not (m.route_choice and m.n_splits == 1):
            continue
        if p == "P3b" and m.msg_type != "pain.001":
            continue
        pool.append(p)
    return pool


def best_response(m: Message, k: int, lam: float, knowledge: str, rng, cfg: GenConfig):
    """Evader solves eq. (1) over admissible primitive subsets of size <= k,
    sampling among improving subsets and the no-edit option with a softmax of
    temperature TEMP. Keeps the unmanipulated original on the result."""
    pool = admissible(m, knowledge)
    base_obj = screening_prob(m)
    cands = [((), base_obj, m)]
    for r in range(1, k + 1):
        for combo in itertools.combinations(pool, r):
            y = m
            for p in combo:
                y = apply_primitive(y, p, rng, cfg)
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
    out.adr_line = list(out.adr_line)
    out.gamed = len(combo) > 0
    out.primitives = combo
    out.pi_0 = base_obj
    out.pi_m = screening_prob(out)
    if out.gamed:
        o = copy(m)
        o.adr_line = list(m.adr_line)
        o.orig = None
        out.orig = o
    return out


# ===========================================================================
# Generator: pairs with latent behaviour, messages in time order.
# ===========================================================================
def make_pairs(n_pairs: int, rng, cfg: GenConfig) -> list:
    ind_w = np.array(cfg.industry_weights, float); ind_w /= ind_w.sum()
    cor_w = np.array(cfg.corridor_weights, float); cor_w /= cor_w.sum()
    pairs = []
    for i in range(n_pairs):
        dc, cc = CORRIDORS[int(rng.choice(len(CORRIDORS), p=cor_w))]
        ind = INDUSTRIES[int(rng.choice(len(INDUSTRIES), p=ind_w))]
        prof = INDUSTRY_PURPOSE[ind]
        codes = list(prof)
        base = np.array([prof[c] for c in codes], float)
        if cfg.profile_perturb > 0:
            base = (1 - cfg.profile_perturb) * base + cfg.profile_perturb / len(codes)
        probs = rng.dirichlet(cfg.profile_alpha * base)
        n_ult = int(rng.integers(cfg.ult_names[0], cfg.ult_names[1] + 1))
        pairs.append(Pair(
            pair_id=i, dbtr_nm=_party_name(rng, cfg), dbtr_ctry=dc,
            cdtr_nm=_party_name(rng, cfg), cdtr_ctry=cc, industry=ind,
            purpose_codes=codes, purpose_probs=probs,
            p_pain=float(rng.beta(*cfg.path_pref_beta)),
            batch_p=float(min(1.0, cfg.batch_rate * 2.0 * rng.beta(2.0, 2.0))),
            batch_mu=float(rng.uniform(math.log(cfg.batch_size_range[0]),
                                       math.log(cfg.batch_size_range[1]))),
            p_ult=float(rng.beta(*cfg.ultimate_beta)),
            ult_names=[_party_name(rng, cfg) for _ in range(n_ult)],
            amount_mu=float(rng.normal(cfg.amount_logmean, cfg.amount_pair_sd)),
            twn_nm=str(rng.choice(TOWNS)), strt_nm=f"STREET {int(rng.integers(1, 200))}"))
    return pairs


def generate(n, eta, rho, seed, k=2, lam=0.18, knowledge="grey", cfg: GenConfig = CONFIG_A):
    rng = np.random.default_rng(seed)
    n_pairs = max(2, n // cfg.pairs_per)
    pairs = make_pairs(n_pairs, rng, cfg)
    w = rng.dirichlet(np.full(n_pairs, cfg.pair_concentration))
    seq = rng.choice(n_pairs, size=n, p=w)
    dm = np.cumsum(cfg.defect_mix)
    out = []
    for i in range(n):
        P = pairs[int(seq[i])]
        msg_type = "pain.001" if rng.random() < P.p_pain else "pacs.008"
        m = Message(
            msg_id=f"MSG{i:09d}", t=i, pair_id=P.pair_id, msg_type=msg_type,
            dbtr_nm=P.dbtr_nm, dbtr_ctry=P.dbtr_ctry, cdtr_nm=P.cdtr_nm,
            cdtr_ctry=P.cdtr_ctry, cdtr_industry=P.industry,
            amount=round(float(math.exp(rng.normal(P.amount_mu, cfg.amount_msg_sd))), 2),
            ccy="EUR" if P.dbtr_ctry in ("DE", "FR") else "USD",
            purpose=str(rng.choice(P.purpose_codes, p=P.purpose_probs)),
            ctgy_purpose=str(rng.choice(CATEGORY_CODES)),
            ultmt_dbtr_nm=(str(rng.choice(P.ult_names)) if rng.random() < P.p_ult else None),
            twn_nm=P.twn_nm, ctry=P.dbtr_ctry, strt_nm=P.strt_nm, adr_line=[],
            rmt_ustrd=_remittance(rng, cfg), n_splits=1)
        if msg_type == "pain.001" and rng.random() < P.batch_p:
            if rng.random() < cfg.batch_tail:
                m.n_splits = int(rng.integers(50, 201))
            else:
                m.n_splits = int(min(200, max(2, round(math.exp(rng.normal(P.batch_mu, 0.35))))))
        if rng.random() < eta:                      # one ordinary data-quality defect
            d = rng.random()
            if d < dm[0]:
                m.rmt_ustrd += f" PURPOSE {m.purpose}"; m.purpose = None
                m.defect = "purpose_in_remittance"
            elif d < dm[1]:
                m.adr_line.append(str(m.twn_nm)); m.twn_nm = None
                m.defect = "partial_destructuring"
            elif d < dm[2]:
                m.ultmt_dbtr_nm = None; m.defect = "ultimate_party_absent"
            else:
                m.ctgy_purpose = None; m.defect = "category_absent"
        m.illicit = bool(rng.random() < rho)
        if m.illicit:
            m.listed_party = "ultimate" if rng.random() < cfg.listed_ultimate_share else "debtor"
            if m.listed_party == "ultimate" and m.ultmt_dbtr_nm is None:
                m.ultmt_dbtr_nm = str(rng.choice(P.ult_names))   # the listed party is on the message
                if m.defect == "ultimate_party_absent":
                    m.defect = None
            m.listed_nm = m.ultmt_dbtr_nm if m.listed_party == "ultimate" else m.dbtr_nm
            m.route_choice = bool(rng.random() < cfg.route_choice_rate)
        m.pi_0 = m.pi_m = screening_prob(m)
        if m.illicit and k > 0:
            m = best_response(m, k, lam, knowledge, rng, cfg)
        out.append(m)
    return out


# ===========================================================================
# Calibration of the screening abstraction.
# ===========================================================================
def _probe(eta, seed, knowledge, n_probe, cfg):
    probe = generate(n_probe, eta, 1.0, seed + 991, k=0, lam=1.0, knowledge=knowledge, cfg=cfg)
    pn = np.array([_legs(m)[0] for m in probe]); ps = np.array([_legs(m)[1] for m in probe])
    pi = np.array([screening_prob(m) for m in probe])
    scr = np.array([listed_in_screened(m) for m in probe], float)
    return float(pi.mean()), float(pn.mean()), float(ps.mean()), float(scr.mean())


def calibrate(target_pi0, eta, seed, knowledge="grey", name_share=0.6, n_probe=4000,
              cfg: GenConfig = CONFIG_A, iters=40, tol=1e-3, verbose=True):
    """Split baseline survival multiplicatively between the two legs with the
    stated name share. P_NAME is set so that the MEAN name-leg probability over
    an unevaded illicit probe hits its target (the listed name is in a screened
    element for only a share of records, since the interbank leg does not read
    ultimate parties); TAU is bisected on the score leg."""
    global P_NAME, TAU
    f = PI_FLOOR
    surv = (1.0 - target_pi0) / (1.0 - f)
    if not 0 < surv < 1:
        raise ValueError("target pi_0 unreachable with this floor")
    p_name_t = 1.0 - surv ** name_share
    p_score_t = 1.0 - surv ** (1.0 - name_share)
    P_NAME = 1.0
    _, _, _, share = _probe(eta, seed, knowledge, n_probe, cfg)
    P_NAME = float(min(1.0, p_name_t / max(share, 1e-6)))
    lo, hi = 0.0, 6.0
    for _ in range(iters):
        TAU = (lo + hi) / 2
        _, _, ps, _ = _probe(eta, seed, knowledge, n_probe, cfg)
        if abs(ps - p_score_t) < tol:
            break
        lo, hi = (TAU, hi) if ps > p_score_t else (lo, TAU)
    pi0, pn, ps, share = _probe(eta, seed, knowledge, n_probe, cfg)
    if verbose:
        print(f"[calibrate] P_NAME={P_NAME:.4f} TAU={TAU:.4f} floor={f:.3f} share={name_share} "
              f"listed-in-screened={share:.3f} -> pi_0={pi0:.4f} (name {pn:.3f} / score {ps:.3f}) "
              f"target {target_pi0} [{'OK' if abs(pi0 - target_pi0) < 0.02 else 'NOT REACHED'}]", flush=True)
    return P_NAME, TAU, pi0


# ===========================================================================
# XML serialisation (carried over from v2; fully XSD-valid, see scripts/validate_release.py).
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
            # In pain.001 the ultimate debtor precedes creditor-agent data.
            # This field describes the initiating customer's underlying party;
            # it must not be serialized as UltmtCdtr.
            if m.ultmt_dbtr_nm:
                _sub(_sub(tx, "UltmtDbtr"), "Nm", m.ultmt_dbtr_nm)
            _sub(_sub(_sub(tx, "CdtrAgt"), "FinInstnId"), "BICFI", "BANKUS33XXX")
            cdtr = _sub(tx, "Cdtr")
            _sub(cdtr, "Nm", m.cdtr_nm)
            _postal(cdtr, m)
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
# Features. Message-level features read the current message only; history
# features read the pair's STRICTLY EARLIER messages, gamed or not, never a
# label. Both are computed in one streaming pass in time order.
# ===========================================================================
COUNTRY_TOKENS = {c for pair in CORRIDORS for c in pair}
FEATURE_NAMES = ["c1_codelist", "c2_completeness", "c3_crossfield", "c4_code_narrative",
                 "c5_purpose_history", "purpose_absent", "len_rmt", "n_adrline",
                 "n_splits", "ultmt_absent", "short_name"]
HIST_NAMES = ["c5_purpose_history", "path_novelty", "split_dev", "ult_novelty",
              "ult_presence_dev", "amount_dev", "purpose_new"]


class PairState:
    __slots__ = ("n", "purpose", "path", "ns", "s1", "s2", "ult_names", "n_ult", "an", "a1", "a2")

    def __init__(self):
        self.n = 0; self.purpose = {}; self.path = {}
        self.ns = 0; self.s1 = 0.0; self.s2 = 0.0
        self.ult_names = set(); self.n_ult = 0
        self.an = 0; self.a1 = 0.0; self.a2 = 0.0

    def update(self, m: Message):
        self.n += 1
        self.purpose[m.purpose] = self.purpose.get(m.purpose, 0) + 1
        self.path[m.msg_type] = self.path.get(m.msg_type, 0) + 1
        ls = math.log(max(1, m.n_splits)); self.ns += 1; self.s1 += ls; self.s2 += ls * ls
        if m.ultmt_dbtr_nm is not None:
            self.ult_names.add(m.ultmt_dbtr_nm); self.n_ult += 1
        la = math.log1p(m.amount); self.an += 1; self.a1 += la; self.a2 += la * la


def _dev(x, n, s1, s2):
    if n < 3:
        return 0.0
    mu = s1 / n
    var = max(0.0, s2 / n - mu * mu)
    return abs(x - mu) / (math.sqrt(var) + 0.5)


def hist_features(m: Message, st: PairState):
    n = st.n
    if n == 0:
        return [0.0] * len(HIST_NAMES)
    c5 = 1.0 - st.purpose.get(m.purpose, 0) / n
    path_nov = 1.0 - st.path.get(m.msg_type, 0) / n
    split_dev = _dev(math.log(max(1, m.n_splits)), st.ns, st.s1, st.s2)
    ult_nov = float(m.ultmt_dbtr_nm is not None and m.ultmt_dbtr_nm not in st.ult_names)
    ult_pres_dev = abs(float(m.ultmt_dbtr_nm is not None) - st.n_ult / n)
    amount_dev = _dev(math.log1p(m.amount), st.an, st.a1, st.a2)
    purpose_new = float(n >= 3 and m.purpose is not None and st.purpose.get(m.purpose, 0) == 0)
    return [c5, path_nov, split_dev, ult_nov, ult_pres_dev, amount_dev, purpose_new]


def msg_features(m: Message, c5: float):
    c1 = 0.0 if (m.purpose is None or m.purpose in PURPOSE_RISK) else 1.0
    adr_tokens = set(" ".join(m.adr_line).split())
    adr_has_geo = float(bool(adr_tokens & (COUNTRY_TOKENS | set(TOWNS))))
    c2 = float(m.twn_nm is None) + float(m.ctry is None) + adr_has_geo
    prof = INDUSTRY_PURPOSE[m.cdtr_industry]
    c3 = (1.0 - (prof.get(m.purpose, 0.0) if m.purpose else 0.0)) + float(m.ultmt_dbtr_nm is None)
    c4 = float(m.purpose == "SALA" and any(w in m.rmt_ustrd for w in ("GOODS", "INVOICE", "SHIPMENT")))
    short = float(min(len(m.dbtr_nm), len(m.cdtr_nm), len(m.ultmt_dbtr_nm or "X" * 99)) <= 5)
    return [c1, c2, c3, c4, c5, float(m.purpose is None), float(len(m.rmt_ustrd)),
            float(len(m.adr_line)), float(m.n_splits), float(m.ultmt_dbtr_nm is None), short]


def raw_features(m: Message):
    """D2/D6 inputs (26 dims): one-hot codes, corridor, amount, splits, completeness.
    Never the evader's own objective terms."""
    def onehot(v, vocab):
        z = [0.0] * (len(vocab) + 1)
        z[vocab.index(v) if v in vocab else len(vocab)] = 1.0
        return z
    corr_vocab = [f"{a}{b}" for a, b in CORRIDORS]
    return (onehot(m.purpose, PURPOSE_CODES) + onehot(m.ctgy_purpose, CATEGORY_CODES)
            + onehot(f"{m.dbtr_ctry}{m.cdtr_ctry}", corr_vocab)
            + [math.log1p(m.amount), float(m.n_splits), float(m.ultmt_dbtr_nm is None),
               float(m.twn_nm is None), float(len(m.rmt_ustrd))])


def build_features(msgs):
    """One streaming pass. Returns X (11), H (7), R (25) for every message,
    the same three matrices for the unmanipulated originals of gamed messages
    (rows are zero where there is no original), y, pair ids and t."""
    n = len(msgs)
    X = np.zeros((n, len(FEATURE_NAMES))); H = np.zeros((n, len(HIST_NAMES)))
    R = np.zeros((n, len(raw_features(msgs[0]))))
    Xo = np.zeros_like(X); Ho = np.zeros_like(H); Ro = np.zeros_like(R)
    has_orig = np.zeros(n, bool)
    states = {}
    for i, m in enumerate(msgs):
        st = states.get(m.pair_id)
        if st is None:
            st = states[m.pair_id] = PairState()
        h = hist_features(m, st); H[i] = h; X[i] = msg_features(m, h[0]); R[i] = raw_features(m)
        if m.orig is not None:
            ho = hist_features(m.orig, st); Ho[i] = ho; Xo[i] = msg_features(m.orig, ho[0]); Ro[i] = raw_features(m.orig)
            has_orig[i] = True
        st.update(m)
    y = np.array([int(m.gamed) for m in msgs])
    pid = np.array([m.pair_id for m in msgs])
    return dict(X=X, H=H, R=R, Xo=Xo, Ho=Ho, Ro=Ro, has_orig=has_orig, y=y, pid=pid)


# ===========================================================================
# Detectors under the temporal protocol.
# ===========================================================================
DETECTORS = ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"]
LABELLED = {"D2", "D6"}


def temporal_split(n, train=0.6, val=0.2):
    idx = np.arange(n)
    return idx < int(train * n), (idx >= int(train * n)) & (idx < int((train + val) * n)), idx >= int((train + val) * n)


def fit_detectors(F, train, seed, allow_labels=True, reuse=None):
    """Fit every learned detector on the training window only. Returns a
    scorer callable that maps (X, H, R) to a dict of score arrays. With
    `reuse` (a previous scorer), the label-free components (isolation forest,
    LOF, standardisation statistics) are shared and only the two labelled
    models are refitted, which is what leave-one-family-out needs."""
    from sklearn.ensemble import IsolationForest, HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.preprocessing import StandardScaler
    X, H, R, y = F["X"], F["H"], F["R"], F["y"]
    benign_tr = train & (y == 0)
    labelled = allow_labels and y[train].sum() >= 10 and (y[train] == 0).sum() >= 10
    gb = HistGradientBoostingClassifier(random_state=seed, max_iter=150).fit(R[train], y[train]) if labelled else None
    scr = StandardScaler().fit(R[train])
    lr = LogisticRegression(max_iter=1000).fit(scr.transform(R[train]), y[train]) if labelled else None
    if reuse is not None:
        iso, scx, lof, z1, z3, hmu, hsd = reuse.parts
    else:
        iso = IsolationForest(random_state=seed, n_estimators=200, contamination=0.05).fit(X[benign_tr])
        scx = StandardScaler().fit(X[benign_tr])
        lof = LocalOutlierFactor(n_neighbors=20, novelty=True).fit(scx.transform(X[benign_tr]))
        d1_tr = X[train, 0] + 0.5 * X[train, 1] + X[train, 2] + 1.5 * X[train, 3]
        d3_tr = -iso.score_samples(X[train])
        z1 = (d1_tr.mean(), d1_tr.std() + 1e-9); z3 = (d3_tr.mean(), d3_tr.std() + 1e-9)
        hmu, hsd = H[train].mean(0), H[train].std(0) + 1e-9

    def scorer(X_, H_, R_):
        d0 = X_[:, 0] + (X_[:, 1] > 1).astype(float)
        d1 = X_[:, 0] + 0.5 * X_[:, 1] + X_[:, 2] + 1.5 * X_[:, 3]
        d3 = -iso.score_samples(X_)
        out = {"D0": d0, "D1": d1, "D3": d3,
               "D4": (d1 - z1[0]) / z1[1] + (d3 - z3[0]) / z3[1],
               "D5": -lof.score_samples(scx.transform(X_)),
               "D7": ((H_ - hmu) / hsd).sum(1)}
        out["D2"] = gb.predict_proba(R_)[:, 1] if gb is not None else np.zeros(len(X_))
        out["D6"] = lr.predict_proba(scr.transform(R_))[:, 1] if lr is not None else np.zeros(len(X_))
        return out
    scorer.parts = (iso, scx, lof, z1, z3, hmu, hsd)
    return scorer


# ===========================================================================
# Frozen thresholds and metrics.
# ===========================================================================
def frozen_threshold(val_scores, q):
    """Largest score value v with share(val >= v) >= q, and the label-blind
    fraction of the tied block needed to alert exactly q of the validation
    window. Applied unchanged to the test window."""
    vals, counts = np.unique(val_scores, return_counts=True)
    vals, counts = vals[::-1], counts[::-1]
    cum = np.cumsum(counts) / len(val_scores)
    j = int(np.searchsorted(cum, q, side="left"))
    j = min(j, len(vals) - 1)
    above = cum[j - 1] if j > 0 else 0.0
    frac = float(np.clip((q - above) / (counts[j] / len(val_scores)), 0.0, 1.0))
    return float(vals[j]), frac


def alert_weights_frozen(scores, thr, frac):
    return (scores > thr).astype(float) + frac * (scores == thr)


def metrics_frozen(w, y):
    tp = float((w * y).sum()); alerts = float(w.sum()); npos = float(y.sum())
    return {"recovery": tp / max(npos, 1), "precision": tp / alerts if alerts > 0 else 0.0,
            "alert_rate": alerts / len(y), "alerts_per_detection": alerts / tp if tp > 0 else float("inf"),
            "tp": tp, "alerts": alerts}


def alert_weights(score, budget):
    """Exact expected top-`budget` alert assignment with label-blind
    tie-breaking (analysis metric; the deployable one is frozen_threshold)."""
    n = len(score)
    target = min(float(n), max(0.0, float(budget) * n))
    order = np.argsort(-score, kind="mergesort")
    s_sorted = score[order]
    w = np.zeros(n)
    if target <= 0:
        return w
    kth = s_sorted[min(n - 1, int(math.ceil(target)) - 1)]
    strictly = score > kth
    n_strict = int(strictly.sum())
    w[strictly] = 1.0
    tied = score == kth
    remaining = target - n_strict
    if tied.sum() > 0 and remaining > 0:
        w[tied] = remaining / tied.sum()
    return w


def tpr_at_budget(score, y, budget):
    w = alert_weights(score, budget)
    return float((w * y).sum() / max(1, y.sum()))


def _midrank(x):
    u, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    start = np.cumsum(cnt) - cnt
    return (start + (cnt - 1) / 2.0 + 1.0)[inv]


def auc_delong_ci(y, score, z=1.96):
    pos, neg = score[y == 1], score[y == 0]
    m, n = len(pos), len(neg)
    tz = _midrank(np.concatenate([pos, neg]))
    v01 = (tz[:m] - _midrank(pos)) / n
    v10 = 1.0 - (tz[m:] - _midrank(neg)) / m
    auc = float(v01.mean())
    se = float(np.sqrt(v01.var(ddof=1) / m + v10.var(ddof=1) / n))
    return auc, max(0.0, auc - z * se), min(1.0, auc + z * se), se


def pair_bootstrap_indices(pid, n_boot, seed):
    """Yield index arrays that resample debtor-creditor pairs with replacement."""
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(pid, return_inverse=True)
    groups = [np.where(inv == g)[0] for g in range(len(uniq))]
    for _ in range(n_boot):
        chosen = rng.integers(0, len(uniq), len(uniq))
        yield np.concatenate([groups[g] for g in chosen])


def ci(vals):
    a = np.asarray(vals, float)
    a = a[np.isfinite(a)]
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))] if len(a) else [float("nan")] * 2


# ===========================================================================
# One full evaluation of one corpus under the temporal protocol.
# ===========================================================================
def evaluate_run(msgs, seed=0, budgets=(0.01, 0.001), n_boot=200, want_prims=True):
    from sklearn.metrics import roc_auc_score, average_precision_score
    F = build_features(msgs)
    n = len(msgs)
    train, val, test = temporal_split(n)
    scorer = fit_detectors(F, train, seed)
    S = scorer(F["X"], F["H"], F["R"])
    So = scorer(F["Xo"], F["Ho"], F["Ro"])            # originals scored by the same models
    y, pid = F["y"], F["pid"]
    yt, pidt = y[test], pid[test]
    ti = np.where(test)[0]
    res = {"n": n, "n_train": int(train.sum()), "n_val": int(val.sum()), "n_test": int(test.sum()),
           "n_gamed_test": int(yt.sum()), "n_gamed": int(y.sum()),
           "n_illicit_test": int(sum(m.illicit for m in msgs if test[m.t])),
           "n_pairs_test": int(len(np.unique(pidt))),
           "prevalence_test": float(yt.mean()),
           "tpr_ceiling@0.01": float(min(1.0, 0.01 * len(yt) / max(1, yt.sum()))),
           "tpr_ceiling@0.001": float(min(1.0, 0.001 * len(yt) / max(1, yt.sum()))),
           "detectors": {}, "thresholds": {}}
    W = {}; Wo = {}
    for d in DETECTORS:
        s = S[d]; st = s[test]
        row = {"auc": float(roc_auc_score(yt, st)), "ap": float(average_precision_score(yt, st))}
        a, lo, hi, se = auc_delong_ci(yt, st); row["auc_delong_ci95"] = [lo, hi]
        for b in budgets:
            thr, frac = frozen_threshold(s[val], b)
            res["thresholds"].setdefault(d, {})[str(b)] = [thr, frac]
            w = alert_weights_frozen(st, thr, frac)
            W[(d, b)] = w
            Wo[(d, b)] = alert_weights_frozen(So[d][test], thr, frac)
            mt = metrics_frozen(w, yt)
            for kk, v in mt.items():
                row[f"{kk}@{b}"] = v
            row[f"topq_recovery@{b}"] = tpr_at_budget(st, yt, b)   # analysis metric
        res["detectors"][d] = row
    # ---- pair-clustered bootstrap of test metrics ------------------------
    boot = {d: {"auc": [], "ap": [], "recovery@0.01": [], "precision@0.01": []} for d in DETECTORS}
    for idx in pair_bootstrap_indices(pidt, n_boot, seed):
        yb = yt[idx]
        if yb.sum() == 0 or yb.sum() == len(yb):
            continue
        for d in DETECTORS:
            sb = S[d][test][idx]
            boot[d]["auc"].append(roc_auc_score(yb, sb)); boot[d]["ap"].append(average_precision_score(yb, sb))
            mt = metrics_frozen(W[(d, 0.01)][idx], yb)
            boot[d]["recovery@0.01"].append(mt["recovery"]); boot[d]["precision@0.01"].append(mt["precision"])
    for d in DETECTORS:
        for kk, v in boot[d].items():
            res["detectors"][d][kk + "_ci95"] = ci(v)
    # ---- paired counterfactual SEL on the test window ----------------------
    if want_prims:
        res["sel"] = paired_sel(msgs, ti, S, So, W, Wo, pidt, seed, n_boot)
    return res


def paired_sel(msgs, ti, S, So, W, Wo, pidt, seed, n_boot, budget=0.01, dets=("D1", "D2", "D4", "D5", "D7")):
    """Paired SEL: every gamed test record contributes its own manipulated
    and original alert probabilities (and detector decisions at the frozen
    threshold). SEL = sum(1-pi_m) / sum(1-pi_0); residual multiplies each side
    by (1 - decision). Attempt-level SEL uses screening_prob_attempt."""
    gam = np.array([msgs[i].gamed for i in ti])
    pi0 = np.array([msgs[i].pi_0 for i in ti]); pim = np.array([msgs[i].pi_m for i in ti])
    pa0 = np.array([screening_prob_attempt(msgs[i].orig) if msgs[i].orig else 0.0 for i in ti])
    pam = np.array([screening_prob_attempt(msgs[i]) for i in ti])
    prim_mask = {p: np.array([p in msgs[i].primitives for i in ti]) for p in PRIMITIVES}
    prim_mask["all"] = gam.copy()

    def stats(rows):
        out = {"n": int(rows.sum())}
        if rows.sum() == 0:
            return out
        a, b = (1 - pim[rows]).sum(), (1 - pi0[rows]).sum()
        out["SEL"] = float(a / max(b, 1e-9))
        out["SEL_attempt"] = float((1 - pam[rows]).sum() / max((1 - pa0[rows]).sum(), 1e-9))
        for d in dets:
            wm, wx = W[(d, budget)][rows], Wo[(d, budget)][rows]
            out[f"SEL_res_{d}"] = float(((1 - pim[rows]) * (1 - wm)).sum() / max(((1 - pi0[rows]) * (1 - wx)).sum(), 1e-9))
            out[f"detect_rate_{d}"] = float(wm.mean())
            out[f"orig_detect_rate_{d}"] = float(wx.mean())
        return out

    out = {}
    for p, mask in prim_mask.items():
        out[p] = stats(mask)
    # pair-clustered bootstrap for SEL and residual SEL (all primitives at once)
    acc = {p: {"SEL": [], **{f"SEL_res_{d}": [] for d in dets}} for p in prim_mask}
    for idx in pair_bootstrap_indices(pidt, n_boot, seed + 1):
        sel_rows = np.zeros(len(ti), bool); sel_rows[idx] = True   # membership (weights ignored for clusters drawn >1x)
        cnt = np.bincount(idx, minlength=len(ti)).astype(float)   # multiplicity weights
        for p, mask in prim_mask.items():
            rows = mask & (cnt > 0)
            if rows.sum() < 10:
                continue
            wgt = cnt[rows]
            a = ((1 - pim[rows]) * wgt).sum(); b = ((1 - pi0[rows]) * wgt).sum()
            acc[p]["SEL"].append(a / max(b, 1e-9))
            for d in dets:
                wm, wx = W[(d, budget)][rows], Wo[(d, budget)][rows]
                acc[p][f"SEL_res_{d}"].append((((1 - pim[rows]) * (1 - wm)) * wgt).sum()
                                              / max((((1 - pi0[rows]) * (1 - wx)) * wgt).sum(), 1e-9))
    for p in prim_mask:
        for kk, v in acc[p].items():
            if v:
                out[p][kk + "_ci95"] = ci(v)
    return out


# ===========================================================================
# Leave-one-family-out under the temporal protocol (k = 1 corpus).
# ===========================================================================
def evaluate_loo(msgs, seed=0):
    from sklearn.metrics import roc_auc_score
    F = build_features(msgs)
    n = len(msgs)
    train, val, test = temporal_split(n)
    y = F["y"]
    gamed = y == 1
    full_scorer = fit_detectors(F, train, seed)
    full = full_scorer(F["X"], F["H"], F["R"])
    ult_absent = np.array([m.ultmt_dbtr_nm is None for m in msgs])
    out = {}
    for fam in ("P1", "P2", "P3"):
        pure = np.array([m.gamed and all(FAMILY[p] == fam for p in m.primitives) for m in msgs])
        any_fam = np.array([any(FAMILY[p] == fam for p in m.primitives) for m in msgs])
        keep = test & ((~gamed) | pure)
        n_pure = int((pure & test).sum())
        if n_pure < 30:
            out[fam] = {"skipped": f"only {n_pure} pure-family test rows", "n_pure": n_pure}
            continue
        tr_red = train & ~any_fam
        held = fit_detectors(F, tr_red, seed, reuse=full_scorer)(F["X"], F["H"], F["R"])
        yk = y[keep]
        row = {"n_pure": n_pure,
               "train_P_gamed_given_ultimate_absent": float(y[tr_red & ult_absent].mean()),
               "train_P_gamed_given_ultimate_present": float(y[tr_red & ~ult_absent].mean()),
               "benign_share_ultimate_absent": float(ult_absent[(~gamed) & train].mean())}
        if fam == "P1":
            for prim in ("P1a", "P1b", "P1c", "P1d"):
                mk = np.array([m.gamed and m.primitives == (prim,) for m in msgs]) & test
                if mk.sum() >= 30:
                    sel = test & ((~gamed) | mk)
                    row[f"{prim}_heldout_auc_D2"] = float(roc_auc_score(y[sel], held["D2"][sel]))
                    row[f"{prim}_n"] = int(mk.sum())
                    row[f"{prim}_ultimate_absent_share"] = float(ult_absent[mk].mean())
        for d in DETECTORS:
            row[d] = float(roc_auc_score(yk, held[d][keep]))
            row[d + "_matched_in"] = float(roc_auc_score(yk, full[d][keep]))
            row[d + "_drop"] = row[d + "_matched_in"] - row[d]
        out[fam] = row
    return out


# ===========================================================================
# Generator shift: fit on A's training window, freeze on A's validation
# window, test on B's test window (and B on B as reference).
# ===========================================================================
def evaluate_shift(msgs_a, msgs_b, seed=0, budget=0.01):
    from sklearn.metrics import roc_auc_score, average_precision_score
    Fa, Fb = build_features(msgs_a), build_features(msgs_b)
    tra, vala, _ = temporal_split(len(msgs_a)); trb, valb, teb = temporal_split(len(msgs_b))
    sa = fit_detectors(Fa, tra, seed); sb = fit_detectors(Fb, trb, seed)
    Sa_on_a = sa(Fa["X"], Fa["H"], Fa["R"]); Sa_on_b = sa(Fb["X"], Fb["H"], Fb["R"]); Sb_on_b = sb(Fb["X"], Fb["H"], Fb["R"])
    yb = Fb["y"][teb]
    out = {"n_gamed_test_B": int(yb.sum()), "prevalence_test_B": float(yb.mean()), "detectors": {}}
    for d in DETECTORS:
        thr_a, fr_a = frozen_threshold(Sa_on_a[d][vala], budget)
        thr_b, fr_b = frozen_threshold(Sb_on_b[d][valb], budget)
        ma = metrics_frozen(alert_weights_frozen(Sa_on_b[d][teb], thr_a, fr_a), yb)
        mb = metrics_frozen(alert_weights_frozen(Sb_on_b[d][teb], thr_b, fr_b), yb)
        out["detectors"][d] = {
            "A_to_B": {"auc": float(roc_auc_score(yb, Sa_on_b[d][teb])), "ap": float(average_precision_score(yb, Sa_on_b[d][teb])),
                       "recovery@0.01": ma["recovery"], "precision@0.01": ma["precision"], "alert_rate@0.01": ma["alert_rate"]},
            "B_to_B": {"auc": float(roc_auc_score(yb, Sb_on_b[d][teb])), "ap": float(average_precision_score(yb, Sb_on_b[d][teb])),
                       "recovery@0.01": mb["recovery"], "precision@0.01": mb["precision"], "alert_rate@0.01": mb["alert_rate"]}}
    return out


# ===========================================================================
# Artefact audit: do any alerts rest on values benign traffic never produces?
# ===========================================================================
def artefact_audit(msgs, budget=0.01, seed=0):
    F = build_features(msgs)
    n = len(msgs)
    train, val, test = temporal_split(n)
    S = fit_detectors(F, train, seed)(F["X"], F["H"], F["R"])
    y = F["y"]; benign = y == 0
    len_rmt = np.array([len(m.rmt_ustrd) for m in msgs]); splits = np.array([m.n_splits for m in msgs])
    names = np.array([min(len(m.dbtr_nm), len(m.cdtr_nm), len(m.ultmt_dbtr_nm or "X" * 99)) for m in msgs])
    ben = benign & train
    out_len = ~np.isin(len_rmt, np.unique(len_rmt[ben]))
    out_split = splits > splits[ben].max()
    out_name = names < names[ben].min()
    art = out_len | out_split | out_name
    out = {"benign_train_remittance_lengths": int(len(np.unique(len_rmt[ben]))),
           "benign_train_max_splits": int(splits[ben].max()), "benign_train_min_name_len": int(names[ben].min()),
           "share_gamed_test_out_of_range": float(art[test & (y == 1)].mean()),
           "share_benign_test_out_of_range": float(art[test & benign].mean()),
           "alert_mass_on_out_of_range": {}, "detectors_precision": {}}
    yt = y[test]
    for d in DETECTORS:
        thr, frac = frozen_threshold(S[d][val], budget)
        w = alert_weights_frozen(S[d][test], thr, frac)
        out["alert_mass_on_out_of_range"][d] = float((w * art[test]).sum() / max(w.sum(), 1e-9))
        out["detectors_precision"][d] = float((w * yt).sum() / max(w.sum(), 1e-9))
    return out


# ===========================================================================
# Invariants of the primitives (checked on every gamed record).
# ===========================================================================
def check_invariants(m: Message) -> list:
    """Return the list of violated invariants for a gamed record."""
    o = m.orig
    v = []
    if o is None:
        return ["no original retained"]
    if abs(m.amount - o.amount) > 1e-6: v.append("amount")
    if m.ccy != o.ccy: v.append("currency")
    if (m.dbtr_ctry, m.cdtr_ctry) != (o.dbtr_ctry, o.cdtr_ctry): v.append("countries")
    if m.cdtr_nm != o.cdtr_nm: v.append("creditor name")
    if m.dbtr_nm != o.dbtr_nm and not ("P1c" in m.primitives and o.listed_party == "debtor"): v.append("debtor name")
    if m.msg_type != o.msg_type and "P3a" not in m.primitives: v.append("message type")
    if m.n_splits != o.n_splits and "P3b" not in m.primitives: v.append("split count")
    if m.purpose != o.purpose and not ({"P2a", "P2c", "P2d"} & set(m.primitives)): v.append("purpose")
    if m.ctgy_purpose != o.ctgy_purpose and "P2b" not in m.primitives: v.append("category purpose")
    if m.ultmt_dbtr_nm != o.ultmt_dbtr_nm and not ({"P1a", "P1c", "P1d", "P3c"} & set(m.primitives)): v.append("ultimate party")
    if "P3b" in m.primitives and abs(m.n_splits * round(m.amount / m.n_splits, 2) - m.amount) > 0.01 * m.n_splits: v.append("children do not sum to amount")
    return v


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="ISO 20022 message-gaming benchmark v3")
    ap.add_argument("--n", type=int, default=50_000)
    ap.add_argument("--eta", type=float, default=0.15)
    ap.add_argument("--rho", type=float, default=0.05)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--lam", type=float, default=0.18)
    ap.add_argument("--temp", type=float, default=0.10)
    ap.add_argument("--knowledge", choices=["black", "grey"], default="grey")
    ap.add_argument("--pi-floor", type=float, default=0.10)
    ap.add_argument("--target-pi0", type=float, default=0.45)
    ap.add_argument("--name-share", type=float, default=0.6)
    ap.add_argument("--config", choices=list(CONFIGS), default="A")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--out", default="results/run.json")
    a = ap.parse_args()
    globals()["PI_FLOOR"] = a.pi_floor; globals()["TEMP"] = a.temp
    cfg = CONFIGS[a.config]
    calibrate(a.target_pi0, a.eta, a.seed, a.knowledge, a.name_share, cfg=cfg)
    msgs = generate(a.n, a.eta, a.rho, a.seed, a.k, a.lam, a.knowledge, cfg=cfg)
    res = evaluate_run(msgs, seed=a.seed, n_boot=a.boot)
    res["config"] = {**vars(a), "solved_P_NAME": P_NAME, "solved_TAU": TAU}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=2)
    print(json.dumps({d: {k: round(v, 4) for k, v in r.items() if isinstance(v, float)} for d, r in res["detectors"].items()}, indent=1))


if __name__ == "__main__":
    main()
