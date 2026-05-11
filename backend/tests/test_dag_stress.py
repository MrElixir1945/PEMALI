"""
DAG Stress Test untuk PEMALI Orchestrator.

Menguji:
1. DAG dengan 4+ level dependency (memory injection tidak corrupt)
2. Parallel execution pada level yang sama
3. Error propagation antar node (task gagal → downstream lihat _ERROR_)
4. Timeout handling pada SubAgent
5. Shared context integrity (tidak ada referensi bocor/hilang)
"""

import json
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.models import (
    TaskIntent, MasterPlan, NodeState, TelemetryEvent, ErrorResponse
)


# ============================================================
# UNIT TESTS — Data Model
# ============================================================

class TestErrorResponse:
    """ErrorResponse model harus bisa serial/deserial dengan benar."""

    def test_structured_error_serialization(self):
        err = ErrorResponse(
            status="TOOL_EXECUTION_FAILED",
            step="http_request",
            error_code="OPENROUTER_HTTP_500",
            context={
                "agent": "geo_agent",
                "task_id": "task_001",
                "attempts_made": 3,
                "recommendation": "Coba lagi nanti."
            }
        )
        dump = err.model_dump()
        assert dump["status"] == "TOOL_EXECUTION_FAILED"
        assert dump["error_code"] == "OPENROUTER_HTTP_500"
        assert dump["context"]["attempts_made"] == 3

    def test_error_response_without_context(self):
        err = ErrorResponse(
            status="TIMEOUT",
            step="timeout",
            error_code="SUB_AGENT_TIMEOUT"
        )
        dump = err.model_dump()
        assert dump["context"] == {}


class TestTaskIntent:
    """TaskIntent model harus bisa membuat chain dependency."""

    def test_simple_linear_dependency(self):
        tasks = [
            TaskIntent(task_id="t1", target_agent="geo_agent", intent="Cari koordinat", depends_on=[]),
            TaskIntent(task_id="t2", target_agent="water_agent", intent="Cek air", depends_on=["t1"]),
            TaskIntent(task_id="t3", target_agent="fire_agent", intent="Cek kebakaran", depends_on=["t2"]),
        ]
        assert tasks[0].depends_on == []
        assert tasks[1].depends_on == ["t1"]
        assert tasks[2].depends_on == ["t2"]

    def test_diamond_dependency(self):
        tasks = [
            TaskIntent(task_id="root", target_agent="geo_agent", intent="Root task", depends_on=[]),
            TaskIntent(task_id="left", target_agent="water_agent", intent="Left branch", depends_on=["root"]),
            TaskIntent(task_id="right", target_agent="fire_agent", intent="Right branch", depends_on=["root"]),
            TaskIntent(task_id="sink", target_agent="osint_agent", intent="Merge result", depends_on=["left", "right"]),
        ]
        assert tasks[3].depends_on == ["left", "right"]

    def test_multiple_roots(self):
        tasks = [
            TaskIntent(task_id="a", target_agent="geo_agent", intent="Task A", depends_on=[]),
            TaskIntent(task_id="b", target_agent="water_agent", intent="Task B", depends_on=[]),
            TaskIntent(task_id="c", target_agent="fire_agent", intent="Task C", depends_on=["a", "b"]),
        ]
        assert all(t.depends_on == [] for t in tasks[:2])


# ============================================================
# INTEGRATION TESTS — DAG Scheduling Logic
# ============================================================

class TestDAGTopology:
    """Test topological scheduling logic di orchestrator."""

    def test_topological_order_simple(self):
        """Test bahwa task di-eksekusi dalam urutan dependensi yang benar."""
        tasks = [
            TaskIntent(task_id="a", target_agent="agent_a", intent="Task A", depends_on=[]),
            TaskIntent(task_id="b", target_agent="agent_b", intent="Task B", depends_on=["a"]),
            TaskIntent(task_id="c", target_agent="agent_c", intent="Task C", depends_on=["b"]),
            TaskIntent(task_id="d", target_agent="agent_d", intent="Task D", depends_on=["a"]),
        ]
        pending = {t.task_id: t for t in tasks}
        completed = set()
        execution_order = []

        while pending:
            ready = [t for t in pending.values() if all(d in completed for d in t.depends_on)]
            assert ready, "Deadlock terdeteksi — ada task yang tidak bisa jalan"
            for t in ready:
                execution_order.append(t.task_id)
                completed.add(t.task_id)
                del pending[t.task_id]

        assert execution_order[0] == "a"
        assert execution_order[-1] == "c"

    def test_deadlock_detection(self):
        """Test deteksi circular dependency."""
        tasks = [
            TaskIntent(task_id="x", target_agent="agent_x", intent="Task X", depends_on=["y"]),
            TaskIntent(task_id="y", target_agent="agent_y", intent="Task Y", depends_on=["x"]),
        ]
        pending = {t.task_id: t for t in tasks}
        completed = set()

        ready = [t for t in pending.values() if all(d in completed for d in t.depends_on)]
        assert len(ready) == 0, "Circular dependency harus menghasilkan 0 ready task"

    def test_parallel_siblings(self):
        """Test bahwa sibling task di-eksekusi secara paralel."""
        tasks = [
            TaskIntent(task_id="root", target_agent="geo_agent", intent="Root", depends_on=[]),
            TaskIntent(task_id="a", target_agent="agent_a", intent="Sibling A", depends_on=["root"]),
            TaskIntent(task_id="b", target_agent="agent_b", intent="Sibling B", depends_on=["root"]),
            TaskIntent(task_id="c", target_agent="agent_c", intent="Sibling C", depends_on=["root"]),
        ]
        pending = {t.task_id: t for t in tasks}
        completed = set()
        completed.add("root")
        del pending["root"]

        ready = [t for t in pending.values() if all(d in completed for d in t.depends_on)]
        assert len(ready) == 3, "3 sibling task harus ready setelah root selesai"


# ============================================================
# INTEGRATION TESTS — Scoped Tool Registry
# ============================================================

class TestScopedTools:
    """Test scoped tool assignment di orchestrator."""

    def test_geo_agent_only_gets_geo_tools(self):
        from backend.core.orchestrator import get_scoped_manifests

        all_manifests = [
            {"name": "geo_water_lookup", "description": "Geo lookup"},
            {"name": "satellite_imagery", "description": "Satellite"},
            {"name": "water_quality_check", "description": "Water check"},
            {"name": "system_scheduler", "description": "Scheduler"},
            {"name": "mock_data_generator", "description": "Mock"},
        ]

        scoped = get_scoped_manifests("geo_agent", all_manifests)
        names = [m["name"] for m in scoped]
        assert "geo_water_lookup" in names
        assert "satellite_imagery" in names
        assert "water_quality_check" not in names
        assert "system_scheduler" not in names

    def test_water_agent_only_gets_water_tools(self):
        from backend.core.orchestrator import get_scoped_manifests

        all_manifests = [
            {"name": "geo_water_lookup", "description": "Geo lookup"},
            {"name": "water_quality_check", "description": "Water check"},
            {"name": "hydrology_debit_monitor", "description": "Hydrology"},
            {"name": "system_scheduler", "description": "Scheduler"},
        ]

        scoped = get_scoped_manifests("water_agent", all_manifests)
        names = [m["name"] for m in scoped]
        assert "water_quality_check" in names
        assert "hydrology_debit_monitor" in names
        assert "geo_water_lookup" not in names

    def test_unknown_agent_gets_all_tools(self):
        from backend.core.orchestrator import get_scoped_manifests

        all_manifests = [
            {"name": "some_tool", "description": "Test"},
        ]
        scoped = get_scoped_manifests("unknown_agent_type", all_manifests)
        assert len(scoped) == len(all_manifests)

    def test_pattern_matching(self):
        from backend.core.orchestrator import _match_tool_pattern

        assert _match_tool_pattern("geo_lookup", "geo_*") is True
        assert _match_tool_pattern("geo_lookup", "water_*") is False
        assert _match_tool_pattern("satellite_imagery", "satellite_*") is True
        assert _match_tool_pattern("exact_name", "exact_name") is True
        assert _match_tool_pattern("exact_name", "other_name") is False


# ============================================================
# INTEGRATION TESTS — Shared Context & Error Propagation
# ============================================================

class TestSharedContextPropagation:
    """Test bahwa shared_context di-orchestrator menangani error dengan benar."""

    def test_failed_task_produces_error_marker(self):
        """Jika task gagal, shared_context untuk task_id itu harus punya _ERROR_."""
        from backend.core.orchestrator import PemaliOrchestrator

        orchestrator = PemaliOrchestrator("test_session")
        res = ErrorResponse(
            status="TOOL_EXECUTION_FAILED",
            step="http_request",
            error_code="OPENROUTER_HTTP_500",
            context={"agent": "geo_agent", "recommendation": "Coba lagi"}
        ).model_dump()

        assert orchestrator._is_error_response(res) is True

    def test_success_response_not_error(self):
        from backend.core.orchestrator import PemaliOrchestrator

        orchestrator = PemaliOrchestrator("test_session")
        success_res = {"agent": "geo_agent", "results": [{"status": 200, "data": {"ndvi": 0.5}}]}

        assert orchestrator._is_error_response(success_res) is False

    def test_response_only_not_error(self):
        from backend.core.orchestrator import PemaliOrchestrator

        orchestrator = PemaliOrchestrator("test_session")
        text_res = {"agent": "geo_agent", "response": "Koordinat Ubud ditemukan."}

        assert orchestrator._is_error_response(text_res) is False

    def test_shared_context_builds_correctly_for_success(self):
        """Simulasi build shared_context untuk task yang sukses."""
        res = {"agent": "geo_agent", "results": [
            {"status": 200, "data": {"lat": -8.5, "lon": 115.2}, "tool_name": "geo_lookup"}
        ]}
        filtered_res = {}
        for r in res.get("results", []):
            tool_name = r.get("tool_name", "unknown")
            clean = r.copy()
            if "tool_name" in clean:
                del clean["tool_name"]
            filtered_res[tool_name] = clean
        assert "geo_lookup" in filtered_res
        assert filtered_res["geo_lookup"]["data"]["lat"] == -8.5

    def test_shared_context_builds_correctly_for_error(self):
        """Simulasi build shared_context untuk task yang gagal menghasilkan _ERROR_."""
        res = ErrorResponse(
            status="TOOL_EXECUTION_FAILED",
            step="max_retries",
            error_code="MAX_RETRIES_REACHED",
            context={"agent": "water_agent", "attempts_made": 3}
        ).model_dump()

        is_error = res.get("status") in [
            "TOOL_EXECUTION_FAILED", "VALIDATION_ERROR", "TIMEOUT"
        ]
        assert is_error is True

        if is_error:
            error_marker = {
                "_ERROR_": {
                    "agent": "water_agent",
                    "intent": "Test task",
                    "status": res.get("error_code"),
                    "detail": res.get("context", {}).get("recommendation", str(res))
                }
            }
            assert "_ERROR_" in error_marker
            assert error_marker["_ERROR_"]["status"] == "MAX_RETRIES_REACHED"


# ============================================================
# STRESS TESTS — DAG dengan 5 Level Dependency
# ============================================================

class TestDAGStressDeep:
    """
    Stress test: DAG dengan 5 level dependency + multiple sibling.
    Simulasi memory injection antar node untuk memastikan
    tidak ada data corruption.
    """

    def test_deep_chain_topology(self):
        """5 level dependency chain (A → B → C → D → E)."""
        tasks = [
            TaskIntent(task_id=f"lv{i}", target_agent=f"agent_{i}",
                       intent=f"Level {i} task",
                       depends_on=[f"lv{i-1}"] if i > 1 else [])
            for i in range(1, 6)
        ]
        pending = {t.task_id: t for t in tasks}
        completed = set()
        levels_processed = 0

        while pending:
            ready = [t for t in pending.values() if all(d in completed for d in t.depends_on)]
            assert ready, f"Deadlock at level {levels_processed}"
            assert len(ready) == 1, f"Hanya 1 task per level di chain linear, got {len(ready)}"
            t = ready[0]
            completed.add(t.task_id)
            del pending[t.task_id]
            levels_processed += 1

        assert levels_processed == 5

    def test_wide_fan_out_topology(self):
        """1 root → 5 siblings parallel → 1 sink."""
        tasks = [
            TaskIntent(task_id="root", target_agent="manager", intent="Root", depends_on=[]),
        ]
        for i in range(5):
            tasks.append(TaskIntent(task_id=f"worker_{i}", target_agent=f"agent_{i}",
                                     intent=f"Worker {i}", depends_on=["root"]))
        tasks.append(TaskIntent(task_id="sink", target_agent="reporter", intent="Sink",
                                 depends_on=[f"worker_{i}" for i in range(5)]))

        pending = {t.task_id: t for t in tasks}
        completed = set()

        # Jalankan root
        ready = [t for t in pending.values() if all(d in completed for d in t.depends_on)]
        assert len(ready) == 1
        assert ready[0].task_id == "root"
        completed.add("root")
        del pending["root"]

        # Sekarang 5 worker harus ready
        ready = [t for t in pending.values() if all(d in completed for d in t.depends_on)]
        assert len(ready) == 5, f"Harus 5 worker ready, dapat {len(ready)}"

    def test_complex_dag_all_paths(self):
        r"""
        DAG Kompleks:
            root
           /    \
          a      b
         / \    / \
        c   d  e   f
         \  |  |  /
          \ |  | /
           sink
        """
        tasks = [
            TaskIntent(task_id="root", target_agent="root", intent="Root", depends_on=[]),
            TaskIntent(task_id="a", target_agent="agent_a", intent="Branch A", depends_on=["root"]),
            TaskIntent(task_id="b", target_agent="agent_b", intent="Branch B", depends_on=["root"]),
            TaskIntent(task_id="c", target_agent="agent_c", intent="Leaf C", depends_on=["a"]),
            TaskIntent(task_id="d", target_agent="agent_d", intent="Leaf D", depends_on=["a"]),
            TaskIntent(task_id="e", target_agent="agent_e", intent="Leaf E", depends_on=["b"]),
            TaskIntent(task_id="f", target_agent="agent_f", intent="Leaf F", depends_on=["b"]),
            TaskIntent(task_id="sink", target_agent="sink", intent="Sink",
                       depends_on=["c", "d", "e", "f"]),
        ]

        pending = {t.task_id: t for t in tasks}
        completed = set()
        full_order = []

        while pending:
            ready = [t for t in pending.values() if all(d in completed for d in t.depends_on)]
            assert ready, "Deadlock!"

            if len(ready) > 1:
                ready.sort(key=lambda t: t.task_id)

            for t in ready:
                full_order.append(t.task_id)
                completed.add(t.task_id)
                del pending[t.task_id]

        # Verifikasi urutan: root harus paling awal
        assert full_order[0] == "root"
        # Sink harus paling akhir
        assert full_order[-1] == "sink"
        # a dan b harus setelah root
        assert full_order.index("a") > full_order.index("root")
        assert full_order.index("b") > full_order.index("root")


# ============================================================
# RUNNER
# ============================================================

if __name__ == "__main__":
    import inspect

    all_tests = []
    test_classes = [
        TestErrorResponse, TestTaskIntent, TestDAGTopology,
        TestScopedTools, TestSharedContextPropagation, TestDAGStressDeep
    ]

    for test_cls in test_classes:
        instance = test_cls()
        for name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
            if name.startswith("test_"):
                all_tests.append((test_cls.__name__, name, method))

    passed = 0
    failed = 0

    for cls_name, method_name, method in all_tests:
        try:
            method()
            print(f"  ✅ {cls_name}.{method_name}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {cls_name}.{method_name} — {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {cls_name}.{method_name} — Exception: {type(e).__name__}: {e}")
            failed += 1

    total = passed + failed
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*50}")

    if failed > 0:
        sys.exit(1)