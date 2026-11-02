"""High-level dangling-else analysis used by the Flask API and the tests."""
from __future__ import annotations

import copy
import sys

from cfg_parser import Parser, ParseInputError, matches, tokenize, unknown_tokens
from grammar import (
    DEFAULT_GRAMMAR_TEXT,
    Grammar,
    GrammarError,
    find_dangling_else,
    parse_grammar_text,
    transform_dangling_else,
)

sys.setrecursionlimit(8000)

PALETTE = ["#d1495b", "#00798c", "#edae49", "#7d4e9f", "#2e7d32", "#f4743b"]
MAX_TREES = 12

EXAMPLES = [
    {"name": "Classic dangling else", "input": "if e1 then if e2 then s1 else s2"},
    {"name": "No else", "input": "if e1 then s1"},
    {"name": "Else for each if", "input": "if e1 then if e2 then s1 else s2 else s3"},
    {"name": "Three nested ifs", "input": "if e1 then if e2 then if e3 then s1 else s2"},
    {"name": "Else-if chain", "input": "if e1 then s1 else if e2 then s2 else s3"},
]


# --------------------------------------------------------------------------
# Tree helpers
# --------------------------------------------------------------------------
def _assign_ids(tree: dict) -> None:
    counter = [0]

    def walk(n):
        n["id"] = counter[0]
        counter[0] += 1
        for c in n.get("children", []):
            walk(c)

    walk(tree)


def _annotate(node: dict, pat: dict | None) -> None:
    """Mark nodes that own an ``if ... else`` pair with their token positions."""
    if node["terminal"]:
        return
    kids = node["children"]
    if pat and kids and kids[0]["terminal"] and kids[0]["sym"] == pat["prefix"][0]:
        else_leaf = next((c for c in kids if c["terminal"] and c["sym"] == pat["else"]), None)
        if else_leaf is not None:
            node["if_pos"], node["else_pos"] = kids[0]["pos"], else_leaf["pos"]
    for c in kids:
        _annotate(c, pat)


def _collect_pairs(node: dict, out: list) -> list:
    if "else_pos" in node:
        out.append((node["if_pos"], node["else_pos"]))
    for c in node.get("children", []):
        _collect_pairs(c, out)
    return out


def leftmost_derivation(tree: dict) -> list[dict]:
    form = [tree]
    steps = [{"rule": "start", "form": tree["label"]}]
    while True:
        idx = next((k for k, n in enumerate(form) if not n["terminal"]), None)
        if idx is None:
            break
        node = form[idx]
        rhs = " ".join(c["sym"] if c["terminal"] else c["label"] for c in node["children"])
        form = form[:idx] + node["children"] + form[idx + 1:]
        steps.append({
            "rule": f"{node['label']} → {rhs}",
            "form": " ".join(n["label"] for n in form),
        })
    return steps


def to_dot(tree: dict, bindings: list[dict]) -> str:
    """Graphviz DOT source for a parse tree (render with ``dot -Tsvg``)."""
    colour = {}
    for k, b in enumerate(bindings):
        colour[b["if"]] = colour[b["else"]] = PALETTE[k % len(PALETTE)]

    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    lines = ["digraph ParseTree {", '  node [fontname="Helvetica"];']

    def walk(n):
        nid = f"n{n['id']}"
        if n["terminal"]:
            c = colour.get(n["pos"])
            style = f', style=filled, fillcolor="{c}", fontcolor=white' if c else ""
            lines.append(f'  {nid} [label="{esc(n["label"])}", shape=box{style}];')
        else:
            lines.append(f'  {nid} [label="{esc(n["label"])}", shape=ellipse];')
            for ch in n["children"]:
                lines.append(f"  {nid} -> n{ch['id']};")
                walk(ch)

    walk(tree)
    lines.append("}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Nearest-unmatched-if rule
# --------------------------------------------------------------------------
def rule_bindings(tokens: list[str], pat: dict) -> tuple[list[tuple[int, int]], list[str]]:
    """Apply "else binds to the nearest preceding unmatched if" with a stack scan."""
    if_sym, else_sym = pat["prefix"][0], pat["else"]
    if_numbers = [i for i, t in enumerate(tokens) if matches(if_sym, t)]
    number = {p: k + 1 for k, p in enumerate(if_numbers)}
    open_ifs: list[int] = []
    pairs: list[tuple[int, int]] = []
    trace: list[str] = []
    for pos, tok in enumerate(tokens):
        if matches(if_sym, tok):
            open_ifs.append(pos)
            now = ", ".join(f"#{number[p]}" for p in open_ifs)
            trace.append(f"Token {pos + 1} “{tok}”: this is if #{number[pos]}. It has no else yet, so push it. Unmatched ifs: {now}.")
        elif matches(else_sym, tok):
            if open_ifs:
                top = open_ifs.pop()
                pairs.append((top, pos))
                left = ", ".join(f"#{number[p]}" for p in open_ifs) or "none"
                trace.append(f"Token {pos + 1} “{tok}”: the nearest unmatched if is #{number[top]}. Bind to it and close it. Still unmatched: {left}.")
            else:
                trace.append(f"Token {pos + 1} “{tok}”: no unmatched if is left, so this else cannot be attached.")
    return pairs, trace


def _if_label(pos: int, tokens: list[str], number: dict) -> str:
    cond = tokens[pos + 1] if pos + 1 < len(tokens) else ""
    return f"if #{number[pos]} (token {pos + 1}, “if {cond}”)"


def _tree_entry(tree, tokens, pat, rule_pairs, label) -> dict:
    t = copy.deepcopy(tree)
    _assign_ids(t)
    _annotate(t, pat)
    pairs = sorted(_collect_pairs(t, []), key=lambda p: p[1])
    if_numbers = {p: k + 1 for k, p in enumerate(
        i for i, tk in enumerate(tokens) if pat and matches(pat["prefix"][0], tk))}
    bindings = [{"if": a, "else": b, "if_no": if_numbers.get(a, 0)} for a, b in pairs]
    return {
        "label": label,
        "tree": t,
        "bindings": bindings,
        "matches_rule": (set(pairs) == set(rule_pairs)) if pat else None,
        "dot": to_dot(t, bindings),
        "derivation": leftmost_derivation(t),
    }


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def analyze(text: str, grammar_text: str | None = None) -> dict:
    g = parse_grammar_text(grammar_text or DEFAULT_GRAMMAR_TEXT)
    tokens = tokenize(text)
    pat = find_dangling_else(g)
    toklist = [{"pos": i, "text": t} for i, t in enumerate(tokens)]
    result: dict = {
        "tokens": toklist,
        "grammar_before": g.to_dict(),
        "pattern": pat,
        "steps": [],
    }
    steps = result["steps"]
    steps.append({
        "title": "Split the input into tokens",
        "text": f"{len(tokens)} tokens: " + "  ".join(f"{i + 1}:{t}" for i, t in enumerate(tokens)),
    })

    bad = unknown_tokens(g, tokens)
    if bad:
        names = ", ".join(f"“{t}” (token {i + 1})" for i, t in bad[:5])
        result.update(valid=False, ambiguous=False, parse_count=0,
                      error=f"These tokens are not in the grammar's alphabet: {names}. "
                            f"Terminals are: {', '.join(g.terminals)}.")
        return result

    parser = Parser(g, tokens, max_trees=MAX_TREES)
    total = parser.total()
    result["parse_count"] = total
    result["valid"] = total > 0
    result["ambiguous"] = total > 1
    if total == 0:
        result["error"] = "The string is not generated by this grammar, so there is nothing to parse."
        steps.append({"title": "Parse with the original grammar",
                      "text": "No derivation exists. Check that every then/else belongs to an if and that each branch has a statement."})
        return result

    rule_pairs, trace = rule_bindings(tokens, pat) if pat else ([], [])
    if_numbers = {p: k + 1 for k, p in enumerate(i for i, t in enumerate(tokens) if pat and matches(pat["prefix"][0], t))}

    before_trees = [
        _tree_entry(t, tokens, pat, rule_pairs, f"Parse tree {k + 1}")
        for k, t in enumerate(parser.all_trees())
    ]
    result["before"] = {"count": total, "shown": len(before_trees), "trees": before_trees}
    result["rule_bindings"] = [
        {"if": a, "else": b, "if_no": if_numbers[a]} for a, b in sorted(rule_pairs, key=lambda p: p[1])
    ]
    result["rule_trace"] = trace

    # ---- Step-by-step explanation ----------------------------------------
    if total == 1:
        steps.append({"title": "Parse with the original grammar",
                      "text": "Exactly one parse tree exists, so this particular string is not ambiguous."})
    else:
        steps.append({"title": "Parse with the original grammar",
                      "text": f"{total} different parse trees exist for the same string. A grammar that gives one string more than one tree is ambiguous, and this string is the witness."})
    if pat and before_trees:
        lines = []
        for e in before_trees:
            parts = [f"else at token {b['else'] + 1} → {_if_label(b['if'], tokens, if_numbers)}" for b in e["bindings"]]
            tag = "follows the nearest-unmatched-if rule" if e["matches_rule"] else "breaks the rule"
            lines.append(f"{e['label']}: " + "; ".join(parts) + f"  ({tag})")
        if total > len(before_trees):
            lines.append(f"…and {total - len(before_trees)} more (showing the first {len(before_trees)}).")
        steps.append({"title": "Where does each else attach?", "text": "\n".join(lines)})
        steps.append({"title": "Apply the nearest-unmatched-if rule",
                      "text": "Scan left to right. Push every if. Each else binds to the most recent if that has no else yet.\n" + "\n".join(trace)})

    # ---- Transformation ---------------------------------------------------
    if not pat:
        steps.append({"title": "Transform the grammar",
                      "text": "No dangling-else pattern (S → if E then S  and  S → if E then S else S) was found, so there is nothing to transform."})
        result["after"] = None
        result["grammar_after"] = None
        return result

    g2, info = transform_dangling_else(g)
    m, u, nt = info["matched"], info["unmatched"], info["nt"]
    result["grammar_after"] = g2.to_dict()
    result["transform_info"] = info
    steps.append({
        "title": "Rewrite with matched and unmatched statements",
        "text": (f"Split {nt} into two kinds.\n"
                 f"• {m}: every if has its else. It can safely sit inside another if's then-branch.\n"
                 f"• {u}: contains at least one if without an else.\n"
                 f"The only production that reads “else” is  {m} → … {m} else {m}  or  {u} → … {m} else {u}. "
                 f"The statement before an else must therefore be {m}, so an unmatched if can never hide before an else. "
                 f"That forces each else to pair with the nearest if that is still open.")
    })

    p2 = Parser(g2, tokens, max_trees=2)
    total2 = p2.total()
    after_entry = None
    if total2:
        after_entry = _tree_entry(p2.all_trees()[0], tokens, pat, rule_pairs, "Parse tree")
    result["after"] = {"count": total2, "tree": after_entry}
    if total2 == 1 and after_entry:
        parts = [f"else at token {b['else'] + 1} → {_if_label(b['if'], tokens, if_numbers)}" for b in after_entry["bindings"]] or ["no else clauses"]
        steps.append({"title": "Re-parse with the new grammar",
                      "text": f"Exactly 1 parse tree. " + "; ".join(parts) + ". "
                              + ("This is the same attachment the nearest-unmatched-if rule gives." if after_entry["matches_rule"] else "This differs from the rule, so check the grammar.")})
    else:
        steps.append({"title": "Re-parse with the new grammar", "text": f"{total2} parse trees were found."})
    return result


# --------------------------------------------------------------------------
# Ambiguity witness search (shortest ambiguous strings of a grammar)
# --------------------------------------------------------------------------
def _lang(g: Grammar, nt: str, n: int, memo: dict, active: set) -> set:
    key = (nt, n)
    if key in memo:
        return memo[key]
    if key in active:
        return set()
    active.add(key)
    out: set = set()
    for prod in g.rules[nt]:
        out |= _seq_lang(g, prod, 0, n, memo, active)
        if len(out) > 20000:
            break
    active.discard(key)
    memo[key] = out
    return out


def _seq_lang(g, prod, k, n, memo, active) -> set:
    if k == len(prod):
        return {()} if n == 0 else set()
    rem = len(prod) - k - 1
    if n < rem + 1:
        return set()
    sym = prod[k]
    if not g.is_nt(sym):
        return {(sym,) + r for r in _seq_lang(g, prod, k + 1, n - 1, memo, active)}
    out: set = set()
    for m in range(1, n - rem + 1):
        left = _lang(g, sym, m, memo, active)
        if left:
            right = _seq_lang(g, prod, k + 1, n - m, memo, active)
            out |= {a + b for a in left for b in right}
    return out


def strings_of_length(g: Grammar, n: int, memo: dict | None = None) -> set:
    return _lang(g, g.start, n, {} if memo is None else memo, set())


def find_witnesses(grammar_text: str | None = None, max_len: int = 11, limit: int = 5) -> dict:
    g = parse_grammar_text(grammar_text or DEFAULT_GRAMMAR_TEXT)
    max_len = max(1, min(max_len, 12))
    memo: dict = {}
    found = []
    for n in range(1, max_len + 1):
        for s in sorted(strings_of_length(g, n, memo)):
            c = Parser(g, list(s), max_trees=1).total()
            if c > 1:
                found.append({"string": " ".join(s), "parses": c, "length": n})
                if len(found) >= limit:
                    return {"ambiguous": True, "witnesses": found, "searched_up_to": n}
    return {"ambiguous": bool(found), "witnesses": found, "searched_up_to": max_len}


# --------------------------------------------------------------------------
# Test-case builder (bonus)
# --------------------------------------------------------------------------
def generate_case(depth: int, else_levels: list[int]) -> dict:
    """Nest ``depth`` ifs in each other's then-branch; give an else to the chosen levels.

    The else belonging to level k is written ``s<k>`` so you can see which if the
    author *meant*; the grammar only sees tokens, so the parse may differ.
    """
    if not isinstance(depth, int) or not 1 <= depth <= 8:
        raise ParseInputError("Depth must be a whole number from 1 to 8.")
    levels = sorted({int(k) for k in else_levels if 1 <= int(k) <= depth})
    toks: list[str] = []
    if_pos, else_pos = {}, {}

    def gen(k):
        if k > depth:
            toks.append("s")
            return
        if_pos[k] = len(toks)
        toks.extend(["if", f"e{k}", "then"])
        gen(k + 1)
        if k in levels:
            else_pos[k] = len(toks)
            toks.extend(["else", f"s{k}"])

    gen(1)
    intended = [{"if": if_pos[k], "else": else_pos[k], "level": k} for k in levels]
    return {"input": " ".join(toks), "depth": depth, "else_levels": levels, "intended": intended}


# --------------------------------------------------------------------------
# Built-in regression suite (also used by tests/)
# --------------------------------------------------------------------------
TEST_CASES = [
    {"name": "Single if, no else", "input": "if e1 then s", "before": 1, "after": 1},
    {"name": "Single if-else", "input": "if e1 then s1 else s2", "before": 1, "after": 1},
    {"name": "Classic dangling else", "input": "if e1 then if e2 then s1 else s2", "before": 2, "after": 1},
    {"name": "Else for both ifs", "input": "if e1 then if e2 then s1 else s2 else s3", "before": 1, "after": 1},
    {"name": "Else-if chain", "input": "if e1 then s1 else if e2 then s2 else s3", "before": 1, "after": 1},
    {"name": "Depth 3, one else", "input": "if e1 then if e2 then if e3 then s1 else s2", "before": 3, "after": 1},
    {"name": "Depth 3, two elses", "input": "if e1 then if e2 then if e3 then s1 else s2 else s3", "before": 3, "after": 1},
    {"name": "Nested in else branch", "input": "if e1 then s1 else if e2 then if e3 then s2 else s3", "before": 2, "after": 1},
    {"name": "Invalid: else without if", "input": "s1 else s2", "before": 0, "after": 0},
]


def run_test_suite() -> list[dict]:
    results = []
    for case in TEST_CASES:
        r = analyze(case["input"])
        before = r.get("parse_count", 0)
        after = (r.get("after") or {}).get("count", 0)
        rule_ok = True
        if after == 1:
            rule_ok = bool(r["after"]["tree"]["matches_rule"])
        results.append({
            "name": case["name"],
            "input": case["input"],
            "expected_before": case["before"],
            "actual_before": before,
            "expected_after": case["after"],
            "actual_after": after,
            "rule_ok": rule_ok,
            "passed": before == case["before"] and after == case["after"] and rule_ok,
        })
    return results


def default_payload() -> dict:
    return {"grammar": DEFAULT_GRAMMAR_TEXT, "examples": EXAMPLES}
