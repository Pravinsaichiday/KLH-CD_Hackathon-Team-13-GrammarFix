"""Context-free grammar model, text parser, and the dangling-else transformation."""
from __future__ import annotations

import re


class GrammarError(ValueError):
    """Raised when grammar text cannot be understood."""


ARROWS = ("->", "→", "::=")

DEFAULT_GRAMMAR_TEXT = """stmt -> if E then stmt
      | if E then stmt else stmt
      | S"""


class Grammar:
    """A CFG: ``rules`` maps a non-terminal to a list of productions (lists of symbols).

    Any symbol that is not a key of ``rules`` is a terminal.
    """

    def __init__(self, rules: dict[str, list[list[str]]], start: str):
        self.rules = rules
        self.start = start

    def is_nt(self, sym: str) -> bool:
        return sym in self.rules

    @property
    def terminals(self) -> list[str]:
        return sorted({s for ps in self.rules.values() for p in ps for s in p if s not in self.rules})

    def to_text(self) -> str:
        width = max(len(n) for n in self.rules)
        lines = []
        for nt, prods in self.rules.items():
            for i, p in enumerate(prods):
                lead = nt.ljust(width) + " -> " if i == 0 else " " * width + "  | "
                lines.append(lead + " ".join(p))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "text": self.to_text(),
            "productions": [
                {"lhs": nt, "alternatives": [" ".join(p) for p in prods]}
                for nt, prods in self.rules.items()
            ],
        }


def parse_grammar_text(text: str) -> Grammar:
    """Parse ``A -> x y | z`` style text (continuation lines may start with ``|``)."""
    rules: dict[str, list[list[str]]] = {}
    current = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("|"):
            if current is None:
                raise GrammarError("A line cannot start with '|' before the first rule.")
            body = line[1:]
        else:
            for arrow in ARROWS:
                if arrow in line:
                    lhs, body = line.split(arrow, 1)
                    break
            else:
                raise GrammarError(f"Cannot read '{raw.strip()}'. Write rules as  A -> x y | z")
            lhs = lhs.strip()
            if not re.fullmatch(r"[A-Za-z_][\w']*", lhs):
                raise GrammarError(f"'{lhs}' is not a valid non-terminal name.")
            current = lhs
            rules.setdefault(lhs, [])
        for alt in body.split("|"):
            syms = alt.split()
            if not syms or syms in (["ε"], ["epsilon"], ["eps"]):
                raise GrammarError("Empty (ε) productions are not supported. Give every alternative at least one symbol.")
            if syms not in rules[current]:
                rules[current].append(syms)
    if not rules:
        raise GrammarError("The grammar is empty. Add at least one rule.")
    if sum(len(p) for p in rules.values()) > 60:
        raise GrammarError("Grammar is too large (limit: 60 productions).")
    return Grammar(rules, next(iter(rules)))


def find_dangling_else(g: Grammar) -> dict | None:
    """Detect the pattern  N -> X N  and  N -> X N else N  (X = condition prefix)."""
    for nt, prods in g.rules.items():
        for short in prods:
            if len(short) < 2 or short[-1] != nt:
                continue
            for long_ in prods:
                if (
                    len(long_) == len(short) + 2
                    and long_[: len(short)] == short
                    and long_[-1] == nt
                    and not g.is_nt(long_[-2])
                ):
                    return {"nt": nt, "prefix": short[:-1], "else": long_[-2]}
    return None


def transform_dangling_else(g: Grammar) -> tuple[Grammar, dict]:
    """Rewrite into matched/unmatched statements (textbook unambiguous grammar).

        N         -> matched | unmatched
        matched   -> X matched else matched | <other productions, N->matched>
        unmatched -> X N | X matched else unmatched | <other productions ending in N>
    """
    pat = find_dangling_else(g)
    if pat is None:
        raise GrammarError(
            "No dangling-else pattern found. The grammar needs rules of the form  "
            "S -> if E then S  and  S -> if E then S else S."
        )
    nt, prefix, els = pat["nt"], pat["prefix"], pat["else"]
    m, u = "matched", "unmatched"
    while m in g.rules or u in g.rules:
        m, u = m + "_", u + "_"

    short, long_ = prefix + [nt], prefix + [nt, els, nt]
    others = [p for p in g.rules[nt] if p not in (short, long_)]

    matched = [prefix + [m, els, m]] + [[m if s == nt else s for s in p] for p in others]
    unmatched = [prefix + [nt], prefix + [m, els, u]]
    for p in others:
        if len(p) > 1 and p[-1] == nt:
            unmatched.append([m if s == nt else s for s in p[:-1]] + [u])

    rules: dict[str, list[list[str]]] = {}
    for name, prods in g.rules.items():
        if name == nt:
            rules[nt] = [[m], [u]]
            rules[m] = matched
            rules[u] = unmatched
        else:
            rules[name] = [list(p) for p in prods]
    info = dict(pat, matched=m, unmatched=u)
    return Grammar(rules, g.start), info
