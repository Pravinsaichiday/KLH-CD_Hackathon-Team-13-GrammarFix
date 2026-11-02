"""Test suite for GrammarFix. Run with:  pytest -q"""
import pytest

from analysis import (
    TEST_CASES, analyze, find_witnesses, generate_case, rule_bindings,
    run_test_suite, strings_of_length,
)
from cfg_parser import Parser, ParseInputError, tokenize
from grammar import (
    DEFAULT_GRAMMAR_TEXT, GrammarError, find_dangling_else,
    parse_grammar_text, transform_dangling_else,
)

G = parse_grammar_text(DEFAULT_GRAMMAR_TEXT)
G2, INFO = transform_dangling_else(G)


# ---- grammar handling ------------------------------------------------------
def test_grammar_text_round_trip():
    assert parse_grammar_text(G.to_text()).rules == G.rules


def test_pattern_detected():
    assert find_dangling_else(G) == {"nt": "stmt", "prefix": ["if", "E", "then"], "else": "else"}


def test_transformed_grammar_shape():
    assert set(G2.rules) == {"stmt", "matched", "unmatched"}
    assert ["if", "E", "then", "matched", "else", "matched"] in G2.rules["matched"]
    assert ["if", "E", "then", "matched", "else", "unmatched"] in G2.rules["unmatched"]


def test_bad_grammar_rejected():
    with pytest.raises(GrammarError):
        parse_grammar_text("nonsense without arrow")
    with pytest.raises(GrammarError):
        parse_grammar_text("a -> ")
    with pytest.raises(GrammarError):
        transform_dangling_else(parse_grammar_text("a -> x y"))


# ---- ambiguity detection ---------------------------------------------------
@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c["name"])
def test_parse_counts(case):
    toks = tokenize(case["input"])
    assert Parser(G, toks).total() == case["before"]
    assert Parser(G2, toks).total() == case["after"]


def test_shortest_witness():
    w = find_witnesses()
    assert w["ambiguous"]
    assert w["witnesses"][0]["string"] == "if E then if E then S else S"
    assert w["witnesses"][0]["parses"] == 2


def test_unambiguous_grammar_has_no_witness():
    assert not find_witnesses("stmt -> if E then stmt else stmt | S", 9)["ambiguous"]


# ---- transformation --------------------------------------------------------
@pytest.mark.parametrize("n", range(1, 12))
def test_transformation_preserves_language(n):
    assert strings_of_length(G, n) == strings_of_length(G2, n)


@pytest.mark.parametrize("n", range(1, 12))
def test_transformed_grammar_is_unambiguous(n):
    for s in strings_of_length(G2, n):
        assert Parser(G2, list(s), max_trees=1).total() == 1


@pytest.mark.parametrize("n", range(1, 12))
def test_unique_tree_matches_nearest_unmatched_if(n):
    for s in strings_of_length(G, n):
        r = analyze(" ".join(s))
        assert r["after"]["count"] == 1
        assert r["after"]["tree"]["matches_rule"] is True


def test_exactly_one_original_tree_follows_the_rule():
    r = analyze("if e1 then if e2 then s1 else s2")
    assert r["ambiguous"] and r["before"]["count"] == 2
    assert sum(t["matches_rule"] for t in r["before"]["trees"]) == 1


# ---- rule & explanation ----------------------------------------------------
def test_rule_binds_to_nearest_if():
    pairs, trace = rule_bindings(tokenize("if e1 then if e2 then s1 else s2"), INFO)
    assert pairs == [(3, 7)]
    assert any("nearest unmatched if is #2" in t for t in trace)


def test_explanation_steps_present():
    r = analyze("if e1 then if e2 then s1 else s2")
    titles = [s["title"] for s in r["steps"]]
    assert "Apply the nearest-unmatched-if rule" in titles
    assert "Rewrite with matched and unmatched statements" in titles
    assert "Graphviz" not in r["before"]["trees"][0]["dot"] and r["before"]["trees"][0]["dot"].startswith("digraph")


def test_derivation_ends_in_tokens():
    r = analyze("if e1 then s1 else s2")
    assert r["after"]["tree"]["derivation"][-1]["form"] == "if e1 then s1 else s2"


# ---- errors ----------------------------------------------------------------
def test_empty_input():
    with pytest.raises(ParseInputError):
        analyze("   ")


def test_unknown_token_reported():
    r = analyze("if e1 then while")
    assert not r["valid"] and "while" in r["error"]


def test_string_not_in_language():
    assert not analyze("s1 else s2")["valid"]


def test_custom_grammar_with_while():
    g = "stmt -> if E then stmt | if E then stmt else stmt | while E do stmt | S"
    r = analyze("if e1 then while e2 do if e3 then s1 else s2", g)
    assert r["after"]["count"] == 1 and r["after"]["tree"]["matches_rule"]


# ---- test-case builder (bonus) ---------------------------------------------
def test_generator_shapes():
    c = generate_case(2, [1])
    assert c["input"] == "if e1 then if e2 then s else s1"
    assert analyze(c["input"])["parse_count"] == 2
    assert analyze(generate_case(3, [1, 2, 3])["input"])["parse_count"] == 1


def test_generator_validates():
    with pytest.raises(ParseInputError):
        generate_case(0, [])
    with pytest.raises(ParseInputError):
        generate_case(9, [])


def test_builtin_suite_passes():
    assert all(r["passed"] for r in run_test_suite())
