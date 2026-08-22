"""MCP agent surface: four tools — a resolution ladder for a file, plus the reverse question.

  who_knows(path, n=3)              compact ranked answer (~100 tokens)
  expertise_evidence(path, author)  full evidence record for one author
  blame_divergence(path, n=3)       last committer vs memoir top-n, explained
  person_profile(query, n=5)        what a person knows: themes, top files, directories (current / built_it)

Run: `memoir mcp [--repo PATH]` (stdio). The repository is fixed at server start; paths are
relative to its root. The on-disk index is built or refreshed on demand, like the CLI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

from memoir.api import Source, answer, by_raw, lists_and_flags
from memoir.person import person_report, resolve_person
from memoir.scoring import Evidence


def _parse_now(now: str | None) -> datetime | None:
    return datetime.fromisoformat(now).replace(tzinfo=timezone.utc) if now else None


def _compact(e: Evidence) -> dict:
    return {"name": e.author.name, "email": e.author.email, "score": round(e.score, 2), "raw": round(e.raw_score, 2),
            "commits": e.commits, "last": e.last_touch}


def make_server(repo: str | Path, now: str | None = None) -> FastMCP:
    root = Path(repo).resolve()
    when = _parse_now(now)
    mcp = FastMCP("memoir", instructions=(
        "memoir ranks the people most likely to hold the mental model of a file, from git history. "
        "Start with who_knows; call expertise_evidence to justify or compare a name; call blame_divergence "
        "when the last committer (git blame/log) may be misleading; call person_profile before pulling "
        "someone in, to see what they know (themes, files, directories). Scores: `score` is time-decayed "
        "(who is current), `raw` is undecayed (who built it)."))

    def _answer(path: str, n: int):
        src = Source(root, need=path)
        try:
            h, ranked, div = answer(src, path, n, when)
        finally:
            src.close()
        return h, ranked, div

    @mcp.tool
    def who_knows(path: str, n: int = 3) -> dict:
        """Who most likely understands this file. Returns `current` (time-decayed top-n), `built_it`
        (undecayed top-n, only when it differs), `recent` (last distinct committers: the naive baseline),
        and trust flags: dormant (nothing substantive for >36 months; list is then ordered by raw),
        last_touch_is_sweep (the last commit was a wide sweep), top1_stable (same #1 across half-lives)."""
        h, ranked, div = _answer(path, n)
        lists, flags = lists_and_flags(h, ranked, n, when)
        out = {
            "path": path,
            "current": [_compact(e) for e in ranked[:n]],
            "recent": [r["name"] for r in lists["recent"]],
            "flags": {"dormant": flags["dormant"], "last_touch_is_sweep": flags["last_touch_is_sweep"],
                      "top1_stable": flags["stability"]["top1_stable"]},
        }
        built = [e.author.name for e in by_raw(ranked)[:n]]
        if built != [e.author.name for e in ranked[:n]]:
            out["built_it"] = built
        if not ranked:
            out["note"] = "no knowledge-bearing human history for this path"
        return out

    @mcp.tool
    def expertise_evidence(path: str, author: str) -> dict:
        """Full evidence record for one author on a file (match by name or email, case-insensitive
        substring). Returns rank, score, raw_score, first_authored/first_credited, commits, co-authored
        count, lines changed, active span (months), last touch, months idle, commits by others since."""
        h, ranked, div = _answer(path, 500)
        q = author.lower()
        for i, e in enumerate(ranked, 1):
            if q in e.author.name.lower() or q in e.author.email.lower():
                d = e.to_dict()
                return {"path": path, "author": d.pop("author"), "rank": i, "of": len(ranked), "evidence": d}
        return {"path": path, "author": author, "rank": None, "of": len(ranked),
                "candidates": [e.author.name for e in ranked[:10]]}

    @mcp.tool
    def blame_divergence(path: str, n: int = 3) -> dict:
        """Does the last committer (what git blame/log shows) hold the knowledge? Compares the last
        commit's author with memoir's top-n and explains the gap (rank of the last committer, whether
        that commit was a sweep or a content-free rename, who memoir would name instead)."""
        h, ranked, div = _answer(path, n)
        last = div["last_commit"]
        if last is None:
            return {"path": path, "diverges": False, "explanation": "no history for this path"}
        lc = h.last_commit
        why = []
        if div["last_is_bot"]:
            why.append("the last commit is by a bot")
        if lc is not None and lc.is_noop:
            why.append("the last commit changed no content (rename or mode change)")
        if lc is not None and lc.breadth is not None and lc.breadth > 50:
            why.append(f"the last commit touched {lc.breadth} files (a sweep)")
        r = div["rank_of_last"]
        where = "no expertise record" if r is None else f"rank {r} of {len(ranked)}"
        top = ", ".join(f"{e.author.name} ({e.score:.2f})" for e in ranked[:n])
        explanation = (f"last commit by {last['author']['name']} on {last['date']}: {where}. "
                       + ("; ".join(why) + ". " if why else "")
                       + (f"memoir top-{n}: {top}." if top else "memoir has no ranking."))
        return {"path": path, "last_commit": last, "last_is_bot": div["last_is_bot"], "rank_of_last": r,
                "diverges": div["diverges"], "top": [_compact(e) for e in ranked[:n]], "explanation": explanation}

    @mcp.tool
    def person_profile(query: str, n: int = 5) -> dict:
        """What does this person know? `query` is a name or email (exact email wins; otherwise substring;
        split identities sharing an email or a full name are merged and reported in `person.note`).
        Returns summary counts, `themes` (path-token TF-IDF), `top_files` and `directories` for both
        `current` (decayed: can answer today) and `built_it` (undecayed: deepest knowledge), each trimmed
        to n. If the query matches several different people, returns ambiguous=true with candidates."""
        src = Source(root)
        try:
            keys, note = resolve_person(src.index, query)
            if not keys:
                cands = []
                if note and note.startswith("ambiguous"):
                    cands = [c.strip() for c in note[len("ambiguous: "):].split(";") if c.strip()]
                return {"query": query, "ambiguous": bool(cands), "candidates": cands, "person": None,
                        "note": None if cands else note}
            rep = person_report(src.index, keys, now=when, n_top=n)
        finally:
            src.close()
        rep["person"]["note"] = note
        rep["directories"] = rep["directories"][:n]
        for d in rep["directories"]:
            d["representative"] = d["representative"][:3]
        rep["query"] = query
        rep["ambiguous"] = False
        return rep

    return mcp


if __name__ == "__main__":
    import sys
    make_server(sys.argv[1] if len(sys.argv) > 1 else ".").run()
