"""Suggest .mailmap lines for split identities. Deterministic; read-only; for human review.

Tiers:
  high     same normalized multi-token name (>= 2 tokens), different emails
  noreply  GitHub `ID+login@users.noreply.github.com` whose login equals another identity's email
           local part or squashed name
  names    one email, several display names (already one identity; picks the canonical spelling)
  handle   a single-token name (a handle) whose digit-stripped form equals the first name or the
           squashed full name of exactly one multi-token person (filipi87 -> Filipi Fuchter); skipped
           when the handle's email already belongs to a multi-token identity or the name is ambiguous
Canonical identity = the one with the most commits. Single-token names are never merged by name;
bots and placeholder emails are skipped.
"""

from __future__ import annotations

import re
from collections import defaultdict

from memoir.index import Index
from memoir.mining import PLACEHOLDER_EMAIL_RE, Identity

_NOREPLY = re.compile(r"^\d+\+([^@]+)@users\.noreply\.github\.com$", re.I)


def _norm(n: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]", "", n.lower()).split()


def suggest_mailmap(ix: Index) -> dict[str, list[tuple[str, int]]]:
    rows = ix.con.execute("SELECT name, email, COUNT(*) FROM commits GROUP BY name, email").fetchall()
    idents = [(Identity(n, e), c) for n, e, c in rows
              if not Identity(n, e).is_bot and not PLACEHOLDER_EMAIL_RE.search(e)]
    out: dict[str, list[tuple[str, int]]] = {"high": [], "noreply": [], "names": [], "handle": []}
    line = lambda canon, other: f"{canon.name} <{canon.email}> {other.name} <{other.email}>"

    by_name = defaultdict(list)
    for i, c in idents:
        toks = _norm(i.name)
        if len(toks) >= 2:
            by_name[" ".join(toks)].append((i, c))
    for lst in by_name.values():
        if len({i.email.lower() for i, _ in lst}) > 1:
            canon = max(lst, key=lambda x: x[1])[0]
            for i, c in lst:
                if i.email.lower() != canon.email.lower():
                    out["high"].append((line(canon, i), c))
    seen = {l for l, _ in out["high"]}

    by_local, by_squash = defaultdict(list), defaultdict(list)
    for i, c in idents:
        by_local[i.email.split("@")[0].lower()].append((i, c))
        by_squash["".join(_norm(i.name))].append((i, c))
    for i, c in idents:
        m = _NOREPLY.match(i.email)
        if not m:
            continue
        login = m.group(1).lower()
        others = [(j, d) for j, d in by_local.get(login, []) + by_squash.get(login, []) if j.email.lower() != i.email.lower()]
        if others:
            canon = max(others, key=lambda x: x[1])[0]
            l = line(canon, i)
            if l not in seen:
                out["noreply"].append((l, c)); seen.add(l)

    # handle: single-token name vs multi-token identities sharing the first name (digits stripped).
    # Only when (a) the handle's email is not already a multi-token identity's email (same key ->
    # the names tier owns it) and (b) the stem matches exactly one person.
    multi = defaultdict(list)  # first-name / squashed-name -> multi-token identities
    multi_keys = set()
    for i, c in idents:
        toks = _norm(i.name)
        if len(toks) >= 2:
            multi[toks[0]].append((i, c))
            multi["".join(toks)].append((i, c))
            multi_keys.add(i.key)
    for i, c in idents:
        toks = _norm(i.name)
        if len(toks) != 1 or i.key in multi_keys:
            continue
        stem = re.sub(r"\d+$", "", toks[0])
        if len(stem) < 4 or stem not in multi:
            continue
        cands = [(j, d) for j, d in multi[stem] if j.key != i.key]
        persons = {" ".join(_norm(j.name)) for j, _ in cands}
        if cands and len(persons) == 1:
            canon = max(cands, key=lambda x: x[1])[0]
            l = line(canon, i)
            if l not in seen:
                out["handle"].append((l, c)); seen.add(l)

    by_email = defaultdict(list)
    for i, c in idents:
        by_email[i.email.lower()].append((i, c))
    for lst in by_email.values():
        if len({i.name for i, _ in lst}) > 1:
            canon = max(lst, key=lambda x: x[1])[0]
            for i, c in lst:
                if i.name != canon.name:
                    out["names"].append((line(canon, i), c))
    for k in out:
        out[k].sort(key=lambda x: (-x[1], x[0]))
    return out


def format_mailmap(out: dict[str, list[tuple[str, int]]]) -> str:
    L = ["# Suggested .mailmap lines (nothing is written; review, then paste into .mailmap and rebuild the index)",
         "# form: Canonical Name <canonical@email> Other Name <other@email>   # commits under the other identity"]
    for tier, title in (("high", "same full name, different emails"), ("noreply", "GitHub noreply address whose login matches another identity"),
                        ("names", "one email, several spellings (already one identity; canonical spelling)"),
                        ("handle", "a handle matching a full name's first name (low confidence; check before pasting)")):
        L.append(f"\n# {tier}: {title} ({len(out[tier])})")
        L += [f"{l}   # {c}" for l, c in out[tier]]
    return "\n".join(L) + "\n"
