"""Raw facts -> ranked experts with evidence records (v0 algorithm).

    raw = w_first * first_authored
        + w_del   * log(1 + deliveries)        # commits + 0.5 * coauthored
        + w_size  * log(1 + lines_changed)
        - w_decay * log(1 + others_commits_since_authors_last)
    score = raw * 0.5 ** (months_since_last_touch / HALF_LIFE_MONTHS)

Variant of the degree-of-knowledge shape (Fritz et al., ICSE 2010); not their calibration.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from memoir.mining import AuthorFacts, FileHistory, Identity

DAYS_PER_MONTH = 365.25 / 12
COAUTHOR_DELIVERY = 0.5


@dataclass(frozen=True)
class Weights:
    w_first: float = 3.0
    w_del: float = 1.0
    w_size: float = 0.5
    w_decay: float = 0.7
    half_life_months: float = 18.0


@dataclass(frozen=True)
class Evidence:
    author: Identity
    score: float
    raw_score: float
    first_authored: bool
    commits: int
    coauthored_count: int
    lines_changed: int
    active_span: float  # months between first and last touch
    last_touch: str  # ISO date (UTC)
    months_since_last_touch: float
    others_commits_since: int

    def to_dict(self) -> dict:
        d = asdict(self)
        d["author"] = {"name": self.author.name, "email": self.author.email}
        return d


def months_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 86400 / DAYS_PER_MONTH


def score_author(f: AuthorFacts, now: datetime, w: Weights = Weights()) -> Evidence:
    deliveries = f.commits + COAUTHOR_DELIVERY * f.coauthored_count
    raw = (
        w.w_first * (1.0 if f.first_authored else 0.0)
        + w.w_del * math.log1p(deliveries)
        + w.w_size * math.log1p(f.lines_changed)
        - w.w_decay * math.log1p(f.others_commits_since)
    )
    months = max(0.0, months_between(f.last_touch, now))
    score = raw * 0.5 ** (months / w.half_life_months)
    return Evidence(
        author=f.author,
        score=score,
        raw_score=raw,
        first_authored=f.first_authored,
        commits=f.commits,
        coauthored_count=f.coauthored_count,
        lines_changed=f.lines_changed,
        active_span=round(months_between(f.first_touch, f.last_touch), 2),
        last_touch=f.last_touch.date().isoformat(),
        months_since_last_touch=round(months, 2),
        others_commits_since=f.others_commits_since,
    )


def rank(history: FileHistory, now: datetime | None = None, w: Weights = Weights()) -> list[Evidence]:
    """Score every non-bot author of the file; highest score first, ties broken by name."""
    now = now or datetime.now(tz=timezone.utc)
    scored = [score_author(f, now, w) for f in history.authors]
    return sorted(scored, key=lambda e: (-e.score, e.author.name, e.author.email))
