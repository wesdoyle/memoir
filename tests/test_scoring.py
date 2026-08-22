"""Scoring: facts -> ranked experts. Formula checks use hand-built facts; ranking checks use the fixture."""

import math
from datetime import datetime, timezone

import pytest

from memoir.mining import AuthorFacts, Identity, mine_file
from memoir.scoring import Weights, rank, score_author

NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)
W = Weights()


def facts(**kw):
    base = dict(
        author=Identity("X", "x@example.com"), first_authored=False, commits=0,
        coauthored_count=0, lines_changed=0, first_touch=NOW, last_touch=NOW,
        others_commits_since=0,
    )
    base.update(kw)
    return AuthorFacts(**base)


def test_formula_matches_spec_without_decay():
    f = facts(first_authored=True, commits=4, lines_changed=100, others_commits_since=2)
    expected = 3.0 + 1.0 * math.log(5) + 0.5 * math.log(101) - 0.7 * math.log(3)
    assert score_author(f, now=NOW, w=W).score == pytest.approx(expected)


def test_half_life_decay():
    f = facts(commits=1, last_touch=datetime(2025, 2, 21, tzinfo=timezone.utc))  # 18 months ago
    raw = math.log(2)
    assert score_author(f, now=NOW, w=W).score == pytest.approx(raw * 0.5, rel=1e-2)


def test_coauthored_commit_counts_as_half_delivery():
    f = facts(coauthored_count=1)
    assert score_author(f, now=NOW, w=W).score == pytest.approx(math.log(1.5))


def test_evidence_record_shape():
    ev = score_author(facts(commits=1), now=NOW, w=W)
    assert set(ev.to_dict()) >= {
        "score", "first_authored", "commits", "lines_changed", "active_span",
        "last_touch", "coauthored_count",
    }


def test_lint_sweeper_does_not_outrank_long_term_author(fixture_repo):
    ranked = rank(mine_file(fixture_repo, "src/core.py"), now=NOW)
    names = [e.author.name for e in ranked]
    assert names[0] == "Alice Adams"
    assert names.index("Carol Chen") > 0


def test_renamed_file_retains_creator_as_top_expert(fixture_repo):
    ranked = rank(mine_file(fixture_repo, "src/helpers.py"), now=NOW)
    assert ranked[0].author.name == "Bob Smith"
    assert ranked[0].first_authored is True


def test_ranking_is_deterministic(fixture_repo):
    h = mine_file(fixture_repo, "src/core.py")
    assert [e.to_dict() for e in rank(h, now=NOW)] == [e.to_dict() for e in rank(h, now=NOW)]


def test_score_is_clamped_at_zero():
    f = facts(coauthored_count=1, others_commits_since=3)  # decay term exceeds half delivery
    assert score_author(f, now=NOW, w=W).score == 0.0
