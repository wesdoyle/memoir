"""Scoring shapes behind Weights flags. Defaults must reproduce the v0 formula exactly."""

import math
from datetime import datetime, timedelta, timezone

import pytest

from memoir.mining import AuthorFacts, Identity, Touch, mine_file, walk
from memoir.scoring import V0, Weights, rank, score_author

NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)
T0 = datetime(2026, 8, 1, tzinfo=timezone.utc)


def touches(*specs):
    """specs: (days_before_T0, lines, breadth, primary) -> list[Touch]"""
    return [Touch(date=T0 - timedelta(days=d), lines=l, breadth=b, primary=p, binary=False, is_root=False)
            for d, l, b, p in specs]


def facts(ts, first=False, name="X"):
    prim = [t for t in ts if t.primary]
    return AuthorFacts(
        author=Identity(name, f"{name}@x"), first_authored=first,
        commits=len(prim), coauthored_count=len(ts) - len(prim),
        lines_changed=sum(t.lines for t in prim),
        first_touch=min(t.date for t in ts), last_touch=max(t.date for t in ts),
        others_commits_since=0, touches=ts,
    )


def test_v0_weights_reproduce_the_spec_formula():
    f = facts(touches((10, 100, 300, True), (5, 1, 1, True), (1, 20, 2, False)), first=True)
    expected = 3.0 + math.log1p(2.5) + 0.5 * math.log1p(101)
    assert score_author(f, now=T0, w=V0).raw_score == pytest.approx(expected)


def test_defaults_are_breadth10_and_not_root():
    w = Weights()
    assert w.breadth_k == 10 and w.first_rule == "not_root" and w.line_cap == 300
    assert V0.breadth_k == 0 and V0.first_rule == "any"


def test_evidence_reports_whether_first_authorship_was_credited():
    root = [Touch(date=T0, lines=10, breadth=5000, primary=True, binary=False, is_root=True)]
    ev = score_author(facts(root, first=True), now=T0, w=Weights())
    assert ev.first_authored is True and ev.first_credited is False
    assert "first_credited" in ev.to_dict()


def test_breadth_discount_scales_wide_commits():
    # one commit touching 300 files with breadth_k=10 -> 10/300 of a delivery and of its lines
    f = facts(touches((1, 90, 300, True)))
    w = Weights(breadth_k=10)
    ev = score_author(f, now=T0, w=w)
    assert ev.raw_score == pytest.approx(math.log1p(10 / 300) + 0.5 * math.log1p(90 * 10 / 300))
    # a narrow commit is untouched
    g = facts(touches((1, 90, 3, True)))
    assert score_author(g, now=T0, w=w).raw_score == pytest.approx(math.log1p(1) + 0.5 * math.log1p(90))


def test_breadth_unknown_means_no_discount():
    f = facts(touches((1, 90, None, True)))
    assert score_author(f, now=T0, w=Weights(breadth_k=10)).raw_score == score_author(f, now=T0, w=Weights()).raw_score


def test_line_scale_gives_small_commits_less_delivery_credit():
    one = facts(touches((1, 1, 1, True)))
    big = facts(touches((1, 200, 1, True)))
    w = Weights(line_scale=20)
    d1 = 1 - math.exp(-1 / 20)
    assert score_author(one, now=T0, w=w).raw_score == pytest.approx(math.log1p(d1) + 0.5 * math.log1p(1))
    assert score_author(big, now=T0, w=w).raw_score == pytest.approx(math.log1p(1 - math.exp(-10)) + 0.5 * math.log1p(200))


def test_line_cap_saturates_size_term():
    f = facts(touches((1, 1293, 1, True)))
    assert score_author(f, now=T0, w=Weights(line_cap=300)).raw_score == pytest.approx(math.log1p(1) + 0.5 * math.log1p(300))


def test_decay_floor_keeps_a_fraction():
    f = facts(touches((18 * 30, 10, 1, True)))  # ~18 months idle -> 0.5 decay
    raw = math.log1p(1) + 0.5 * math.log1p(10)
    ev = score_author(f, now=T0 + timedelta(days=18 * 30.4375 - 18 * 30), w=Weights(decay_floor=0.3))
    assert ev.score == pytest.approx(raw * (0.3 + 0.7 * 0.5), rel=1e-2)


def test_decay_depth_slows_decay_for_deep_history():
    shallow = facts(touches((600, 10, 1, True)))
    deep = facts(touches(*[(600 + i, 10, 1, True) for i in range(200)]))
    w = Weights(decay_depth=0.5)
    s, d = score_author(shallow, now=T0, w=w), score_author(deep, now=T0, w=w)
    assert d.score / d.raw_score > s.score / s.raw_score  # deep history decays slower


def test_first_rule_not_root_and_not_mass_and_needs_followup():
    root = [Touch(date=T0, lines=10, breadth=5000, primary=True, binary=False, is_root=True)]
    f_root = facts(root, first=True)
    assert score_author(f_root, now=T0, w=Weights(first_rule="not_root")).raw_score < 3.0
    assert score_author(f_root, now=T0, w=Weights(first_rule="any")).raw_score > 3.0
    mass = facts(touches((1, 10, 5000, True)), first=True)
    assert score_author(mass, now=T0, w=Weights(first_rule="not_mass", first_mass_n=200)).raw_score < 3.0
    narrow = facts(touches((1, 10, 3, True)), first=True)
    assert score_author(narrow, now=T0, w=Weights(first_rule="not_mass", first_mass_n=200)).raw_score > 3.0
    lone = facts(touches((1, 10, 1, True)), first=True)
    assert score_author(lone, now=T0, w=Weights(first_rule="needs_followup")).raw_score < 3.0
    two = facts(touches((1, 10, 1, True), (0, 5, 1, True)), first=True)
    assert score_author(two, now=T0, w=Weights(first_rule="needs_followup")).raw_score > 3.0


def test_breadth_discount_applies_to_erosion_of_others(fixture_repo):
    # Carol's sweep (breadth 3) should erode Alice by 2/3 of a commit with breadth_k=2, not 1.
    h = walk(fixture_repo).history("src/core.py")
    r = {e.author.name: e for e in rank(h, now=NOW, w=Weights(breadth_k=2))}
    assert r["Alice Adams"].others_commits_since == pytest.approx(2 / 3)
    assert r["Carol Chen"].commits == 1  # raw facts unchanged


def test_is_root_is_known_from_walk_and_follow(fixture_repo):
    w = walk(fixture_repo).history("README.md")
    f = mine_file(fixture_repo, "README.md")
    assert w.commits[-1].is_root is True and f.commits[-1].is_root is True
    assert w.commits[0].is_root is False
