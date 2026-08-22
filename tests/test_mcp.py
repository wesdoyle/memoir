"""MCP surface: exactly three tools, mirroring the resolution ladder; in-memory client."""

import asyncio
import json

from fastmcp import Client

from memoir.mcp_server import make_server


def call(server, tool, **args):
    async def go():
        async with Client(server) as c:
            r = await c.call_tool(tool, args)
            return r.data if r.data is not None else json.loads(r.content[0].text)
    return asyncio.run(go())


def tools(server):
    async def go():
        async with Client(server) as c:
            return sorted(t.name for t in await c.list_tools())
    return asyncio.run(go())


def test_exactly_three_tools(fixture_repo):
    assert tools(make_server(fixture_repo, now="2026-08-21")) == ["blame_divergence", "expertise_evidence", "who_knows"]


def test_who_knows_is_compact_and_ranked(fixture_repo):
    srv = make_server(fixture_repo, now="2026-08-21")
    out = call(srv, "who_knows", path="src/core.py", n=3)
    assert out["path"] == "src/core.py"
    assert [e["name"] for e in out["current"]][:2] == ["Alice Adams", "Carol Chen"]
    assert {"score", "raw"} <= set(out["current"][0])
    assert out["recent"][0] == "Carol Chen"
    assert set(out["flags"]) >= {"dormant", "last_touch_is_sweep", "top1_stable"}
    assert len(json.dumps(out)) < 700  # ~100-150 tokens


def test_expertise_evidence_full_record(fixture_repo):
    srv = make_server(fixture_repo, now="2026-08-21")
    out = call(srv, "expertise_evidence", path="src/core.py", author="alice")
    assert out["author"]["email"] == "alice@example.com"
    assert out["rank"] == 1
    assert {"score", "raw_score", "first_authored", "first_credited", "commits", "lines_changed", "active_span",
            "last_touch", "coauthored_count", "others_commits_since"} <= set(out["evidence"])
    miss = call(srv, "expertise_evidence", path="src/core.py", author="nobody")
    assert miss["rank"] is None and "candidates" in miss


def test_blame_divergence_explains(fixture_repo):
    srv = make_server(fixture_repo, now="2026-08-21")
    out = call(srv, "blame_divergence", path="src/core.py")
    assert out["last_commit"]["author"]["name"] == "Carol Chen"
    assert out["diverges"] is False  # 3 authors only: Carol is in the top-3
    assert "explanation" in out and "Carol Chen" in out["explanation"]
    out1 = call(srv, "blame_divergence", path="src/core.py", n=1)
    assert out1["diverges"] is True and "Alice Adams" in out1["explanation"]
