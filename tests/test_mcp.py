"""MCP surface: the file ladder (who_knows / expertise_evidence / blame_divergence) plus person_profile; in-memory client."""

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


def test_five_tools(fixture_repo):
    assert tools(make_server(fixture_repo, now="2026-08-21")) == ["blame_divergence", "expertise_evidence", "experts_for_files", "person_profile", "who_knows"]


def test_person_profile_tool(fixture_repo):
    srv = make_server(fixture_repo, now="2026-08-21")
    out = call(srv, "person_profile", query="alice", n=3)
    assert out["person"]["name"] == "Alice Adams"
    assert out["summary"]["top3_built_it"] >= 1
    assert out["top_files"]["current"][0]["path"] == "src/core.py"
    assert "themes" in out and "directories" in out
    amb = call(srv, "person_profile", query="example.com")
    assert amb["ambiguous"] is True and len(amb["candidates"]) >= 3
    none = call(srv, "person_profile", query="nobody")
    assert none["ambiguous"] is False and none["person"] is None


def test_experts_for_files_tool(fixture_repo):
    srv = make_server(fixture_repo, now="2026-08-21")
    assert "experts_for_files" in tools(srv)
    out = call(srv, "experts_for_files", paths=["src/core.py", "src/helpers.py"], n=3)
    assert out["selection"]["files"] == 2
    assert {e["name"] for e in out["current"][:2]} == {"Alice Adams", "Bob Smith"}
    out = call(srv, "experts_for_files", match="core")
    assert out["selection"]["files"] == 1 and out["current"][0]["name"] == "Alice Adams"
    out = call(srv, "experts_for_files", dir="src", match="zzz")
    assert out["selection"]["files"] == 0 and out["current"] == []
