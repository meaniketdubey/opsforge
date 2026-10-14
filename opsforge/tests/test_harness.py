import pytest

from opsforge.config import Config
from opsforge.harness import Guardrails, Tracer, retry_async
from opsforge.orchestrator import parse_kv


def make_guard(tmp_path, **kw):
    cfg = Config(**kw)
    return Guardrails(cfg, Tracer(tmp_path / "tr", "run1"), tmp_path), cfg


def test_blocks_dangerous_commands(tmp_path):
    g, _ = make_guard(tmp_path)
    assert g.check_command("rm -rf /") is not None
    assert g.check_command("ls -la") is None


def test_blocks_writes_outside_workdir(tmp_path):
    g, _ = make_guard(tmp_path)
    assert g.check_path("/etc/passwd") is not None
    assert g.check_path("notes/out.md") is None


async def test_pre_hook_denies_and_traces(tmp_path):
    g, _ = make_guard(tmp_path)
    out = await g.pre_tool_use({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}, "1", None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    kinds = [e["kind"] for e in g.tracer.read()]
    assert "guardrail_denied" in kinds


async def test_tool_call_budget(tmp_path):
    g, _ = make_guard(tmp_path, max_tool_calls=2)
    ok = {"tool_name": "Read", "tool_input": {}}
    assert await g.pre_tool_use(ok, "1", None) == {}
    assert await g.pre_tool_use(ok, "2", None) == {}
    third = await g.pre_tool_use(ok, "3", None)
    assert third["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    assert await retry_async(flaky, attempts=3, base_delay=0.001) == "ok"


async def test_retry_gives_up():
    async def bad():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        await retry_async(bad, attempts=2, base_delay=0.001)


def test_parse_kv():
    t = "severity: SEV2\nservice: checkout-api\nneeds_investigation: true"
    assert parse_kv(t, "service") == "checkout-api"
    assert parse_kv(t, "missing", "x") == "x"
