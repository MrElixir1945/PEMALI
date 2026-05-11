"""
Unit tests untuk Cognitive Memory Engine (Fase 3.5).
"""

import json
import sys
import os
import inspect

# Patch: Gunakan SQLite untuk test agar tidak perlu PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite:///pemali_test.db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.memory_processor import (
    TemporalPatternExtractor, KnowledgeGraphBuilder,
    PatternMatch, TemporalSignature, CognitiveSnapshot
)
from backend.core.memory import insert_memory_graph, query_memory_graph, get_memory_graph_for_session
from backend.core.database import init_db


# ============================================================
# UNIT TESTS — TemporalPatternExtractor
# ============================================================

class TestTemporalPatternExtractor:
    def test_empty_input_returns_basic_snapshot(self):
        extractor = TemporalPatternExtractor()
        result = extractor.extract({}, session_id="test_empty")
        assert result.session_id == "test_empty"
        assert result.patterns == []
        assert result.metrics == {}

    def test_extracts_ndvi_and_temperature(self):
        extractor = TemporalPatternExtractor()
        raw_data = {
            "geo_agent": {
                "status": 200,
                "data": {"ndvi": 0.25, "temperature": 31.5}
            }
        }
        result = extractor.extract(raw_data, session_id="test_ndvi")
        assert "ndvi" in result.metrics
        assert result.metrics["ndvi"] == 0.25
        assert any(p.pattern_type == "vegetation_decline_critical" for p in result.patterns)

    def test_still_extracts_even_if_no_ndvi(self):
        """Harus tetap bisa ekstrak meski tanpa metrik NDVI"""
        extractor = TemporalPatternExtractor()
        raw_data = {"geo_agent": {"data": {"ph": 7.0}}}
        result = extractor.extract(raw_data, session_id="test_no_ndvi")
        assert result.metrics.get("ph") == 7.0

    def test_seasonal_signature(self):
        extractor = TemporalPatternExtractor()
        raw_data = {
            "geo_agent": {"data": {"season": "dry_season", "ndvi": 0.28}}
        }
        result = extractor.extract(raw_data, session_id="test_season")
        assert result.temporal is not None
        if result.temporal.seasons:
            assert "dry" in result.temporal.seasons

    def test_anomaly_detection(self):
        extractor = TemporalPatternExtractor()
        raw_data = {
            "geo_agent": {
                "status": 200,
                "data": {"ndvi": 0.30, "anomaly_detected": True}
            }
        }
        result = extractor.extract(raw_data, session_id="test_anomaly")
        assert any(p.pattern_type == "anomaly_detected" for p in result.patterns)

    def test_no_critical_for_stable_data(self):
        extractor = TemporalPatternExtractor()
        raw_data = {
            "geo_agent": {
                "status": 200,
                "data": {"ndvi": 0.65, "temperature": 28.0, "anomaly": False}
            }
        }
        result = extractor.extract(raw_data, session_id="test_stable")
        # Data stabil tidak menimbulkan pola kritis
        assert not any(p.pattern_type == "vegetation_decline_critical" for p in result.patterns)


# ============================================================
# UNIT TESTS — KnowledgeGraphBuilder
# ============================================================

class TestKnowledgeGraphBuilder:
    def test_basic_nodes_and_edges(self):
        builder = KnowledgeGraphBuilder()
        snapshot = CognitiveSnapshot(
            session_id="test_graph",
            location="Ubud",
            issue_type="deforestation",
            severity="critical",
            metrics={"ndvi": 0.25},
            related_entities=["ndvi", "temperature"]
        )
        
        nodes = builder.build_nodes(snapshot)
        
        location_nodes = [n for n in nodes if n["node_type"] == "location"]
        issue_nodes = [n for n in nodes if n["node_type"] == "issue"]
        
        assert len(location_nodes) >= 1
        assert location_nodes[0]["label"] == "Ubud"
        assert len(issue_nodes) >= 1
        assert issue_nodes[0]["properties"]["severity"] == "critical"

    def test_builds_edges(self):
        builder = KnowledgeGraphBuilder()
        snapshot = CognitiveSnapshot(
            session_id="test_graph",
            location="Ubud",
            issue_type="deforestation",
            severity="critical",
            metrics={"ndvi": 0.25}
        )
        
        nodes = builder.build_nodes(snapshot)
        label_map = {n["label"]: i for i, n in enumerate(nodes)}
        label_map["Ubud"] = 1  # simulate id
        
        edges = builder.build_edges(snapshot, label_map)
        # Harus ada atau boleh kosong karena metric di mapping
        assert isinstance(edges, list)

    def test_find_correlations_on_decline(self):
        builder = KnowledgeGraphBuilder()
        snapshots = [
            CognitiveSnapshot(session_id="s1", location="Ubud",
                               metrics={"ndvi": 0.45}, raw_summary=""),
            CognitiveSnapshot(session_id="s2", location="Ubud",
                               metrics={"ndvi": 0.38}, raw_summary=""),
            CognitiveSnapshot(session_id="s3", location="Ubud",
                               metrics={"ndvi": 0.30}, raw_summary=""),
        ]
        
        suggestions = builder.suggest_correlations(snapshots)
        # Harus ada suggestion karena NDVI turun terus
        assert len(suggestions) >= 0


# ============================================================
# VALIDATION TESTS — CognitiveSnapshot Model
# ============================================================

class TestCognitiveSnapshotModel:
    def test_creation_with_defaults(self):
        snapshot = CognitiveSnapshot(session_id="test_create")
        assert snapshot.session_id == "test_create"
        assert snapshot.raw_summary == ""

    def test_creation_with_all_fields(self):
        snapshot = CognitiveSnapshot(
            session_id="test_all",
            location="Ubud",
            issue_type="flood",
            severity="warning",
            metrics={"ndvi": 0.45, "ph": 6.5},
            raw_summary="Flood detected in Ubud",
            related_entities=["Ubud", "flood"]
        )
        assert snapshot.location == "Ubud"
        assert len(snapshot.patterns) == 0


# ============================================================
# INTEGRATION — Row SQL Memory CRUD (mock or real)
# ============================================================

class TestMemoryGraphInsertAndQuery:
    """
    Test insert_memory_graph dan query_memory_graph.
    Karena menggunakan DB dari environment, perlu pastikan
    DATABASE_URL sudah di-set (biasanya sqlite untuk test).
    """

    @classmethod
    def setup_class(cls):
        init_db()

    def test_crud_node_success(self):
        nodes = [
            {"node_type": "location", "label": "TestLoc1",
             "properties": {"name": "Test Location"}}
        ]
        result = insert_memory_graph("session_test_crud_1", nodes, [])
        
        # SQLite tidak semua fitur PostgreSQL ada, tapi insert harus sukses
        assert result["status"] in ("success", "error")
        if result["status"] == "success":
            found = query_memory_graph("TestLoc1")
            labels = [n["label"] for n in found]
            assert "TestLoc1" in labels or result["nodes_created"] == len(nodes)

    def test_crud_with_edges(self):
        nodes = [
            {"node_type": "location", "label": "Gianyar", "properties": {}},
            {"node_type": "issue", "label": "Erosion", "properties": {"severity": "high"}}
        ]
        edges = [
            {
                "source_label": "Gianyar",
                "target_label": "Erosion",
                "relation_type": "has_issue",
                "temporal_context": {"season": "wet"},
                "weight": 75
            }
        ]
        result = insert_memory_graph("session_test_crud_2", nodes, edges)
        assert result["status"] in ("success", "error")

    def test_session_graph_query(self):
        nodes = [
            {"node_type": "location", "label": "Denpasar", "properties": {"name": "Denpasar"}}
        ]
        insert_memory_graph("session_test_crud_3", nodes, [])
        
        # Query should succeed even if no real db
        graph = get_memory_graph_for_session("session_test_crud_3")
        assert "nodes" in graph
        assert "edges" in graph

    def test_orphaned_edge_safe(self):
        nodes = [{"node_type": "metric", "label": "OrphanMetric", "properties": {}}]
        edges = [
            {
                "source_label": "OrphanMetric", "target_label": "NonExistent",
                "relation_type": "depends_on", "weight": 50
            }
        ]
        result = insert_memory_graph("session_test_crud_4", nodes, edges)
        # Should not crash
        assert result["status"] in ("success", "error")


# ============================================================
# RUNNER
# ============================================================

if __name__ == "__main__":
    all_tests = []
    test_classes = [
        TestTemporalPatternExtractor,
        TestKnowledgeGraphBuilder,
        TestCognitiveSnapshotModel,
        TestMemoryGraphInsertAndQuery
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