"""
Tests for freebuff/core_02/interfaces.py
"""

import pytest
from freebuff.core_02.interfaces import IAgent, AgentResult, TaskStatus


class _TestAgent(IAgent):
    @property
    def name(self) -> str:
        return "test-agent"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def run(self, **kwargs) -> AgentResult:
        return self.ok("test", data=kwargs)


class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.OK.value == "ok"
        assert TaskStatus.WARN.value == "warn"
        assert TaskStatus.ERROR.value == "error"


class TestAgentResult:
    def test_ok_result(self):
        r = AgentResult(status=TaskStatus.OK, agent="a", task="t", data={"x": 1***REMOVED***)
        assert r.ok is True
        assert r.status == TaskStatus.OK
        d = r.to_dict()
        assert d["status"***REMOVED*** == "ok"
        assert d["data"***REMOVED*** == {"x": 1***REMOVED***

    def test_error_result(self):
        r = AgentResult(status=TaskStatus.ERROR, agent="a", task="t", errors=["e1"***REMOVED***)
        assert r.ok is False
        assert r.errors == ["e1"***REMOVED***

    def test_warn_result(self):
        r = AgentResult(status=TaskStatus.WARN, agent="a", task="t", warnings=["w1"***REMOVED***)
        assert r.status == TaskStatus.WARN
        assert r.warnings == ["w1"***REMOVED***

    def test_empty_defaults(self):
        r = AgentResult(status=TaskStatus.OK, agent="a", task="t")
        assert r.warnings == [***REMOVED***
        assert r.errors == [***REMOVED***
        assert r.meta == {***REMOVED***
        assert r.data is None

    def test_to_dict_full(self):
        r = AgentResult(
            status=TaskStatus.OK,
            agent="test",
            task="run",
            data="result",
            warnings=["w"***REMOVED***,
            errors=[***REMOVED***,
            meta={"key": "val"***REMOVED***,
        )
        d = r.to_dict()
        assert d == {
            "status": "ok",
            "agent": "test",
            "task": "run", "data": "result",
            "warnings": ["w"***REMOVED***,
            "errors": [***REMOVED***,
            "meta": {"key": "val"***REMOVED***,
        ***REMOVED***


class TestIAgent:
    @pytest.mark.asyncio
    async def test_run_returns_agent_result(self):
        agent = _TestAgent()
        result = await agent.run(x=1)
        assert isinstance(result, AgentResult)
        assert result.ok is True
        assert result.data == {"x": 1***REMOVED***

    def test_name_property(self):
        agent = _TestAgent()
        assert agent.name == "test-agent"

    def test_version_property(self):
        agent = _TestAgent()
        assert agent.version == "1.0.0"

    def test_convenience_ok(self):
        agent = _TestAgent()
        r = agent.ok("task1", data="done", meta_key="v")
        assert r.ok is True
        assert r.task == "task1"
        assert r.data == "done"
        assert r.meta == {"meta_key": "v"***REMOVED***

    def test_convenience_err(self):
        agent = _TestAgent()
        r = agent.err("task2", errors=["fail"***REMOVED***)
        assert r.ok is False
        assert r.errors == ["fail"***REMOVED***

    def test_convenience_warn(self):
        agent = _TestAgent()
        r = agent.warn("task3", warnings=["caution"***REMOVED***)
        assert r.status == TaskStatus.WARN
        assert r.warnings == ["caution"***REMOVED***
