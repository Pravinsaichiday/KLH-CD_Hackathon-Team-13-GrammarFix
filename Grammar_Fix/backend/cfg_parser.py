"""Tokeniser and a span-based parser that counts and enumerates *all* parse trees."""
from __future__ import annotations

import re

from grammar import Grammar

MAX_TOKENS = 60
E_RE = re.compile(r"^(e|c|cond|expr|b)\d*$", re.I)
S_RE = re.compile(r"^(s|a|other)\d*$", re.I)


class ParseInputError(ValueError):
    """Raised for unusable input strings."""


def matches(terminal: str, text: str) -> bool:
    """Does token ``text`` instantiate grammar terminal ``terminal``?

    ``E`` stands for any condition (e, e1, c2, cond...), ``S`` for any simple
    statement (s, s1, a, other...). Every other terminal matches itself.
    """
    if terminal.lower() == text.lower():
        return True
    if terminal == "E":
        return bool(E_RE.match(text))
    if terminal == "S":
        return bool(S_RE.match(text))
    return False


def tokenize(text: str) -> list[str]:
    toks = text.split()
    if not toks:
        raise ParseInputError("Enter a statement to analyse, e.g.  if e1 then if e2 then s1 else s2")
    if len(toks) > MAX_TOKENS:
        raise ParseInputError(f"Input has {len(toks)} tokens; the limit is {MAX_TOKENS}.")
    return toks


def unknown_tokens(g: Grammar, toks: list[str]) -> list[tuple[int, str]]:
    terms = g.terminals
    return [(i, t) for i, t in enumerate(toks) if not any(matches(x, t) for x in terms)]


class Parser:
    """Memoised top-down span parser (no ε-productions, so every symbol eats ≥ 1 token).

    ``count`` returns the exact number of parse trees; ``trees`` returns up to
    ``max_trees`` of them as nested dicts.
    """

    def __init__(self, grammar: Grammar, tokens: list[str], max_trees: int = 12):
        self.g, self.toks, self.cap = grammar, tokens, max_trees
        self._count: dict = {}
        self._seq_count_memo: dict = {}
        self._trees: dict = {}
        self._seq_trees_memo: dict = {}
        self._active: set = set()

    # ---- counting -------------------------------------------------------
    def count(self, nt: str, i: int, j: int) -> int:
        key = (nt, i, j)
        if key in self._count:
            return self._count[key]
        if key in self._active:  # unit-production cycle guard
            return 0
        self._active.add(key)
        total = sum(self._seq_count(nt, pi, p, 0, i, j) for pi, p in enumerate(self.g.rules[nt]))
        self._active.discard(key)
        self._count[key] = total
        return total

    def _seq_count(self, nt, pi, prod, k, i, j) -> int:
        key = (nt, pi, k, i, j)
        if key in self._seq_count_memo:
            return self._seq_count_memo[key]
        if k == len(prod):
            res = 1 if i == j else 0
        else:
            rem = len(prod) - k - 1
            sym = prod[k]
            res = 0
            if j - i >= rem + 1:
                if not self.g.is_nt(sym):
                    if matches(sym, self.toks[i]):
                        res = self._seq_count(nt, pi, prod, k + 1, i + 1, j)
                else:
                    for m in range(i + 1, j - rem + 1):
                        c = self.count(sym, i, m)
                        if c:
                            res += c * self._seq_count(nt, pi, prod, k + 1, m, j)
        self._seq_count_memo[key] = res
        return res

    # ---- enumeration ----------------------------------------------------
    def trees(self, nt: str, i: int, j: int) -> list[dict]:
        key = (nt, i, j)
        if key in self._trees:
            return self._trees[key]
        out: list[dict] = []
        if self.count(nt, i, j):
            for pi, p in enumerate(self.g.rules[nt]):
                if len(out) >= self.cap:
                    break
                for kids in self._seq_trees(nt, pi, p, 0, i, j):
                    out.append({"label": nt, "terminal": False, "children": kids})
                    if len(out) >= self.cap:
                        break
        self._trees[key] = out
        return out

    def _seq_trees(self, nt, pi, prod, k, i, j) -> list[list[dict]]:
        key = (nt, pi, k, i, j)
        if key in self._seq_trees_memo:
            return self._seq_trees_memo[key]
        out: list[list[dict]] = []
        if k == len(prod):
            out = [[]] if i == j else []
        elif self._seq_count(nt, pi, prod, k, i, j):
            rem = len(prod) - k - 1
            sym = prod[k]
            if not self.g.is_nt(sym):
                leaf = {"label": self.toks[i], "sym": sym, "terminal": True, "pos": i}
                out = [[leaf] + r for r in self._seq_trees(nt, pi, prod, k + 1, i + 1, j)][: self.cap]
            else:
                for m in range(i + 1, j - rem + 1):
                    if not self.count(sym, i, m) or not self._seq_count(nt, pi, prod, k + 1, m, j):
                        continue
                    rights = self._seq_trees(nt, pi, prod, k + 1, m, j)
                    for left in self.trees(sym, i, m):
                        for r in rights:
                            out.append([left] + r)
                            if len(out) >= self.cap:
                                break
                        if len(out) >= self.cap:
                            break
                    if len(out) >= self.cap:
                        break
        self._seq_trees_memo[key] = out
        return out

    # ---- convenience ----------------------------------------------------
    def total(self) -> int:
        return self.count(self.g.start, 0, len(self.toks))

    def all_trees(self) -> list[dict]:
        return self.trees(self.g.start, 0, len(self.toks))
