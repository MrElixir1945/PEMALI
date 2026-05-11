"""
Integration tests untuk Narrative Prompt Contracts + SSE Telemetry (Sprint 3).
"""

import json
import sys
import os
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.models import TelemetryEvent, NodeState
from backend.core.telemetry import telemetry


# ============================================================
# TESTS — TelemetryEvent Metadata
# ============================================================

class TestTelemetryMetadata:
    def test_event_with_metadata(self):
        evt = TelemetryEvent(
            trace_id="tr-123",
            node_id="geo_worker",
            node_type="Module",
            state=NodeState.EXECUTING,
            narrative="Test",
            metadata={"tool_name": "satellite", "duration_ms": 245.5}
        )
        data = evt.model_dump()
        assert data["metadata"]["tool_name"] == "satellite"
        assert data["metadata"]["duration_ms"] == 245.5

    def test_event_without_metadata(self):
        evt = TelemetryEvent(
            trace_id="tr-123",
            node_id="geo_worker",
            node_type="Module",
            state=NodeState.DONE,
            narrative="Done"
        )
        data = evt.model_dump()
        assert data["metadata"] is None


# ============================================================
# TESTS — Narrative Contract in System Prompts
# ============================================================

class TestNarrativeContract:
    def test_manager_prompt_has_contract(self):
        orchestrator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "core", "orchestrator.py"
        )
        with open(orchestrator_path) as f:
            source = f.read()
        assert "MANAGER AGENT" in source, "Manager prompt harus mengandung MANAGER AGENT"
        assert "target_agent" in source, "Manager prompt harus mengandung target_agent"
        assert "depends_on" in source, "Manager prompt harus mengandung depends_on"

    def test_subagent_prompt_has_contract(self):
        orchestrator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "core", "orchestrator.py"
        )
        with open(orchestrator_path) as f:
            source = f.read()
        assert "NARRATIVE CONTRACT" in source
        assert "ATURAN STATE MACHINE" in source
        assert "ATURAN NARASI" in source
        assert "ATURAN KOREKSI DIRI" in source

    def test_rag_context_in_prompt(self):
        orchestrator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "core", "orchestrator.py"
        )
        with open(orchestrator_path) as f:
            source = f.read()
        assert "rag_context" not in source or "KONTEKS HISTORIS" in source


# ============================================================
# TESTS — Duration Tracking
# ============================================================

class TestDurationTracking:
    @classmethod
    def _import_subagent(cls):
        import sys
        # Mock heavy dependencies before importing orchestrator
        mock_memory = MagicMock()
        sys.modules["core.memory"] = mock_memory
        mock_processor = MagicMock()
        sys.modules["core.memory_processor"] = mock_processor
        from backend.core.orchestrator import SubAgent
        return SubAgent

    @patch("backend.core.orchestrator.registry")
    @patch("backend.core.orchestrator.telemetry")
    @patch("backend.core.orchestrator.time")
    def test_tool_execution_records_duration(self, mock_time, mock_telemetry, mock_registry):
        SubAgent = self._import_subagent()
        from backend.core.models import TaskIntent

        mock_registry.execute_tool = AsyncMock()
        mock_registry.execute_tool.return_value = MagicMock(
            model_dump=lambda: {"status": "success", "data": {}}
        )

        mock_time.monotonic.side_effect = [1000.0, 1002.5]

        mock_emit = AsyncMock()
        mock_telemetry.emit = mock_emit

        task = TaskIntent(
            task_id="t1", target_agent="geo_agent",
            intent="test", parameters={}
        )
        agent = SubAgent(task, "session_1", [], "tr-test")
        agent.headers = {}

        result = asyncio.run(agent._execute_tool("geo_sensor", {}, "tc_1"))

        emit_calls = mock_emit.call_args_list
        done_calls = [c for c in emit_calls if c[0][0].state == NodeState.DONE]
        assert len(done_calls) >= 1
        done_evt = done_calls[0][0][0]
        assert done_evt.metadata is not None
        assert done_evt.metadata["duration_ms"] == 2500.0
        assert done_evt.metadata["tool_name"] == "geo_sensor"

    @patch("backend.core.orchestrator.registry")
    @patch("backend.core.orchestrator.telemetry")
    @patch("backend.core.orchestrator.time")
    def test_error_tool_records_duration(self, mock_time, mock_telemetry, mock_registry):
        SubAgent = self._import_subagent()
        from backend.core.models import TaskIntent

        mock_registry.execute_tool = AsyncMock()
        mock_registry.execute_tool.side_effect = Exception("Connection refused")

        mock_time.monotonic.side_effect = [2000.0, 2001.8]

        mock_emit = AsyncMock()
        mock_telemetry.emit = mock_emit

        task = TaskIntent(
            task_id="t2", target_agent="water_agent",
            intent="test", parameters={}
        )
        agent = SubAgent(task, "session_1", [], "tr-test")
        agent.headers = {}

        result = asyncio.run(agent._execute_tool("water_sensor", {}, "tc_2"))

        emit_calls = mock_emit.call_args_list
        error_calls = [c for c in emit_calls if c[0][0].state == NodeState.ERROR]
        assert len(error_calls) >= 1
        error_evt = error_calls[0][0][0]
        assert error_evt.metadata is not None
        assert error_evt.metadata["duration_ms"] == 1800.0
        assert "error" in error_evt.metadata


# ============================================================
# TESTS — SSE Serialization
# ============================================================

class TestSSESerialization:
    def test_telemetry_stream_includes_metadata(self):
        evt = TelemetryEvent(
            trace_id="tr-456",
            node_id="manager",
            node_type="Manager",
            state=NodeState.THINKING,
            narrative="Analisis data...",
            metadata={"rag_sources": ["audit_123", "audit_456"]}
        )
        serialized = evt.model_dump()
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        assert parsed["metadata"]["rag_sources"] == ["audit_123", "audit_456"]
        assert parsed["trace_id"] == "tr-456"


# ============================================================
# RUNNER
# ============================================================

if __name__ == "__main__":
    import inspect

    all_tests = []
    test_classes = [
        TestTelemetryMetadata,
        TestNarrativeContract,
        TestDurationTracking,
        TestSSESerialization,
    ]

    for cls in test_classes:
        inst = cls()
        for name, method in inspect.getmembers(inst, predicate=inspect.ismethod):
            if name.startswith("test_"):
                all_tests.append((cls.__name__, name, method))

    passed = 0
    failed = 0

    for cls_name, m_name, method in all_tests:
        try:
            method()
            print(f"  ✅ {cls_name}.{m_name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {cls_name}.{m_name}: {type(e).__name__}: {e}")
            failed += 1

    total = passed + failed
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*50}")
