"""Raw facts -> ranked experts with evidence records (v0 algorithm).

    raw = w_first * first_authored
        + w_del   * log(1 + deliveries)        # commits + 0.5 * coauthored
        + w_size  * log(1 + lines_changed)
        - w_decay * log(1 + others_commits_since_authors_last)
    score = max(0, raw) * 0.5 ** (months_since_last_touch / HALF_LIFE_MONTHS)

Variant of the degree-of-knowledge shape (Fritz et al., ICSE 2010); not their calibration.
"""

from __future__ import annotations

import math
from bisect import bisect_right
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
    # --- shapes; V0 below has them all off. Defaults adopted at the P6 gate: breadth_k=10, line_cap=300, first_rule=not_root ---
    breadth_k: int = 10         # >0: a commit touching B files is worth min(1, breadth_k/B) of a commit (credit, lines, erosion)
    line_scale: float = 0.0     # >0: delivery credit per commit = 1 - exp(-lines/line_scale) (small commits earn less)
    line_cap: int = 300         # >0: lines per commit are capped here before the size term (size saturates)
    decay_floor: float = 0.0    # in [0,1): decay multiplier = floor + (1-floor) * 0.5^(t/HL); knowledge fades to a floor
    decay_depth: float = 0.0    # >0: HL_eff = HL * (1 + decay_depth * log1p(deliveries)); deep history fades slower
    first_rule: str = "not_root"  # any | not_root | not_mass | needs_followup: when first_authored earns w_first
    first_mass_n: int = 200     # for not_mass: creating commit touching > this many files earns no w_first


V0 = Weights(breadth_k=0, line_scale=0.0, line_cap=0, decay_floor=0.0, decay_depth=0.0, first_rule="any")
"""The v0 formula exactly as specified (initial_prompt.md); the regression baseline."""


@dataclass(frozen=True)
class Evidence:
    author: Identity
    score: float
    raw_score: float
    first_authored: bool  # fact: author of the file's first knowledge-bearing commit
    first_credited: bool  # whether that earned w_first under the active first_rule
    commits: int
    coauthored_count: int
    lines_changed: int
    active_span: float  # months between first and last touch
    last_touch: str  # ISO date (UTC)
    months_since_last_touch: float
    others_commits_since: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["author"] = {"name": self.author.name, "email": self.author.email}
        return d


def months_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 86400 / DAYS_PER_MONTH


def breadth_weight(breadth: int | None, w: Weights) -> float:
    if not w.breadth_k or breadth is None or breadth <= w.breadth_k:
        return 1.0
    return w.breadth_k / breadth


def _credit(t, w: Weights) -> float:
    """Delivery credit for one touch: breadth-discounted, optionally size-shaped, co-authors at 0.5."""
    c = breadth_weight(t.breadth, w)
    if w.line_scale > 0:
        lines = t.lines if not (t.binary and t.lines == 0) else w.line_scale
        c *= 1.0 - math.exp(-lines / w.line_scale)
    return c if t.primary else COAUTHOR_DELIVERY * c


def _first_earns(f: AuthorFacts, w: Weights) -> bool:
    if not f.first_authored:
        return False
    prim = [t for t in f.touches if t.primary]
    creating = min(prim, key=lambda t: t.date) if prim else None
    if w.first_rule == "any" or creating is None:
        return True
    if w.first_rule == "not_root":
        return not creating.is_root
    if w.first_rule == "not_mass":
        return creating.breadth is None or creating.breadth <= w.first_mass_n
    if w.first_rule == "needs_followup":
        return len(prim) >= 2
    raise ValueError(f"unknown first_rule {w.first_rule!r}")


def score_author(f: AuthorFacts, now: datetime, w: Weights = Weights(), others_since: float | None = None) -> Evidence:
    shaped = w.breadth_k or w.line_scale > 0 or w.line_cap
    if shaped and f.touches:
        deliveries = sum(_credit(t, w) for t in f.touches)
        lines = sum(breadth_weight(t.breadth, w) * (min(t.lines, w.line_cap) if w.line_cap else t.lines)
                    for t in f.touches if t.primary)
    else:
        deliveries = f.commits + COAUTHOR_DELIVERY * f.coauthored_count
        lines = f.lines_changed
    erosion = f.others_commits_since if others_since is None else others_since
    first_credited = _first_earns(f, w)
    raw = (
        w.w_first * (1.0 if first_credited else 0.0)
        + w.w_del * math.log1p(deliveries)
        + w.w_size * math.log1p(lines)
        - w.w_decay * math.log1p(erosion)
    )
    months = max(0.0, months_between(f.last_touch, now))
    hl = w.half_life_months * (1.0 + w.decay_depth * math.log1p(deliveries)) if w.decay_depth > 0 else w.half_life_months
    mult = w.decay_floor + (1.0 - w.decay_floor) * 0.5 ** (months / hl)
    score = max(0.0, raw) * mult
    return Evidence(
        author=f.author,
        score=score,
        raw_score=raw,
        first_authored=f.first_authored,
        first_credited=first_credited,
        commits=f.commits,
        coauthored_count=f.coauthored_count,
        lines_changed=f.lines_changed,
        active_span=round(months_between(f.first_touch, f.last_touch), 2),
        last_touch=f.last_touch.date().isoformat(),
        months_since_last_touch=round(months, 2),
        others_commits_since=erosion,
    )


def _erosion_by_author(history: FileHistory, w: Weights) -> dict[str, float]:
    """Breadth-weighted count of others' primary touches after each author's last touch.

    One sorted pass with prefix sums (O(T log T)) instead of authors × touches. An author's own
    primary touches are never after their own last touch, so the total after it is exactly others'.
    """
    touches = sorted(
        ((t.date, breadth_weight(t.breadth, w)) for a in history.authors for t in a.touches if t.primary),
        key=lambda x: x[0],
    )
    dates = [d for d, _ in touches]
    suffix = [0.0] * (len(touches) + 1)
    for i in range(len(touches) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + touches[i][1]
    return {a.author.key: suffix[bisect_right(dates, a.last_touch)] for a in history.authors}


def rank(history: FileHistory, now: datetime | None = None, w: Weights = Weights()) -> list[Evidence]:
    """Score every non-bot author of the file; highest score first, ties broken by name."""
    now = now or datetime.now(tz=timezone.utc)
    if w.breadth_k:
        # erosion by others is breadth-discounted too: a sweep displaces little knowledge
        erosion = _erosion_by_author(history, w)
        scored = [score_author(f, now, w, others_since=erosion[f.author.key]) for f in history.authors]
    else:
        scored = [score_author(f, now, w) for f in history.authors]
    return sorted(scored, key=lambda e: (-e.score, e.author.name, e.author.email))


def divergence(history: FileHistory, ranked: list[Evidence], n: int = 3) -> dict:
    """Compare the file's last committer (what blame shows) with memoir's top-n."""
    last = history.last_commit
    top = ranked[:n]
    if last is None:
        return {"last_commit": None, "last_is_bot": False, "rank_of_last": None, "diverges": False, "top": []}
    rank_of_last = next((i + 1 for i, e in enumerate(ranked) if e.author.key == last.author.key), None)
    return {
        "last_commit": {
            "author": {"name": last.author.name, "email": last.author.email},
            "date": last.date.date().isoformat(),
            "sha": last.sha[:10],
            "is_noop": last.is_noop,
        },
        "last_is_bot": last.is_bot,
        "rank_of_last": rank_of_last,  # None if the last committer has no expertise record
        "diverges": not last.is_bot and (rank_of_last is None or rank_of_last > n),
        "top": [e.to_dict() for e in top],
    }
