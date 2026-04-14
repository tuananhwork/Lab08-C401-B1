"""
tests/test_retrieval_worker.py — Unit Tests for P2 Retrieval Worker
=====================================================================
Test coverage:
  1. retrieve_dense returns correct chunks structure
  2. retrieve_dense handles empty results (abstention)
  3. run() integrates with AgentState correctly
  4. Score values are in [0, 1] range
  5. Sources are extracted correctly

Cách chạy:
    pytest tests/test_retrieval_worker.py -v
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path để import workers
sys.path.insert(0, str(Path(__file__).parent.parent))

from workers.retrieval import retrieve_dense, run, _get_collection, _get_embedding_fn


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_collection():
    """Mock ChromaDB collection với sample data."""
    mock = MagicMock()
    mock.query.return_value = {
        "documents": [
            [
                "SLA P1: phản hồi trong 15 phút, xử lý trong 4 giờ.",
                "Ticket P1 cần escalation lên manager nếu quá 2 giờ.",
                "P1 là mức ưu tiên cao nhất trong hệ thống.",
            ]
        ],
        "distances": [
            [0.15, 0.25, 0.35]
        ],
        "metadatas": [
            [
                {"source": "sla_p1_2026.txt", "section": "SLA Policy", "department": "IT"},
                {"source": "sla_p1_2026.txt", "section": "Escalation", "department": "IT"},
                {"source": "sla_p1_2026.txt", "section": "Priorities", "department": "IT"},
            ]
        ],
    }
    return mock


@pytest.fixture
def mock_embedding_fn():
    """Mock embedding function trả về vector cố định."""
    def fake_embed(text: str) -> list:
        return [0.1] * 384
    return fake_embed


# =============================================================================
# Tests for retrieve_dense
# =============================================================================

class TestRetrieveDense:
    """Tests cho hàm retrieve_dense."""

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_returns_correct_chunk_structure(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """retrieve_dense phải trả về chunks với đúng structure."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        results = retrieve_dense("SLA P1 là bao lâu?", top_k=3)

        assert len(results) == 3
        for chunk in results:
            assert "text" in chunk
            assert "source" in chunk
            assert "score" in chunk
            assert "metadata" in chunk
            assert isinstance(chunk["text"], str)
            assert isinstance(chunk["source"], str)
            assert isinstance(chunk["score"], float)
            assert isinstance(chunk["metadata"], dict)

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_scores_in_valid_range(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """Score phải nằm trong [0, 1] (cosine similarity)."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        results = retrieve_dense("SLA P1 là bao lâu?", top_k=3)

        for chunk in results:
            assert 0.0 <= chunk["score"] <= 1.0, f"Score {chunk['score']} out of range"

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_scores_computed_correctly(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """Score = 1 - distance (cosine similarity)."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        results = retrieve_dense("SLA P1 là bao lâu?", top_k=3)

        # Distance 0.15 → score 0.85
        assert results[0]["score"] == pytest.approx(0.85, abs=0.01)
        # Distance 0.25 → score 0.75
        assert results[1]["score"] == pytest.approx(0.75, abs=0.01)
        # Distance 0.35 → score 0.65
        assert results[2]["score"] == pytest.approx(0.65, abs=0.01)

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_sources_extracted_correctly(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """Sources phải được extract từ metadata."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        results = retrieve_dense("SLA P1 là bao lâu?", top_k=3)

        for chunk in results:
            assert chunk["source"] == "sla_p1_2026.txt"

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_respects_top_k_parameter(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """retrieve_dense phải tôn trọng top_k parameter."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        results = retrieve_dense("SLA P1 là bao lâu?", top_k=2)

        mock_collection.query.assert_called_once()
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs["n_results"] == 2

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_handles_empty_results_gracefully(
        self, mock_get_collection, mock_get_embed_fn,
        mock_embedding_fn
    ):
        """Khi không có results, phải trả về [] (abstain)."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_collection_empty = MagicMock()
        mock_collection_empty.query.return_value = {
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]],
        }
        mock_get_collection.return_value = mock_collection_empty

        results = retrieve_dense("câu hỏi không có trong DB", top_k=3)

        assert results == []

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_handles_chromadb_error_gracefully(
        self, mock_get_collection, mock_get_embed_fn,
        mock_embedding_fn
    ):
        """Khi ChromaDB lỗi, phải trả về [] thay vì raise exception."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_collection_error = MagicMock()
        mock_collection_error.query.side_effect = Exception("Connection failed")
        mock_get_collection.return_value = mock_collection_error

        results = retrieve_dense("SLA P1 là bao lâu?", top_k=3)

        assert results == []


# =============================================================================
# Tests for run() — AgentState integration
# =============================================================================

class TestRunWithState:
    """Tests cho hàm run() tích hợp với AgentState."""

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_updates_retrieved_chunks_in_state(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """run() phải update retrieved_chunks trong state."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        state = {"task": "SLA P1 là bao lâu?", "retrieval_top_k": 3}
        result = run(state)

        assert "retrieved_chunks" in result
        assert len(result["retrieved_chunks"]) == 3

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_updates_retrieved_sources_in_state(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """run() phải update retrieved_sources trong state."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        state = {"task": "SLA P1 là bao lâu?", "retrieval_top_k": 3}
        result = run(state)

        assert "retrieved_sources" in result
        assert len(result["retrieved_sources"]) > 0
        assert "sla_p1_2026.txt" in result["retrieved_sources"]

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_appends_to_workers_called(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """run() phải append worker name vào workers_called."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        state = {
            "task": "SLA P1 là bao lâu?",
            "retrieval_top_k": 3,
            "workers_called": [],
        }
        result = run(state)

        assert "retrieval_worker" in result["workers_called"]

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_appends_worker_io_log(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """run() phải append worker IO log vào state."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        state = {
            "task": "SLA P1 là bao lâu?",
            "retrieval_top_k": 3,
            "workers_called": [],
        }
        result = run(state)

        assert "worker_io_logs" in result
        assert len(result["worker_io_logs"]) > 0
        log = result["worker_io_logs"][-1]
        assert log["worker"] == "retrieval_worker"
        assert log["output"] is not None
        assert log["error"] is None

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_appends_to_history(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """run() phải append message vào history."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_get_collection.return_value = mock_collection

        state = {
            "task": "SLA P1 là bao lâu?",
            "retrieval_top_k": 3,
            "workers_called": [],
            "history": [],
        }
        result = run(state)

        assert len(result["history"]) > 0
        assert any("[retrieval_worker]" in msg for msg in result["history"])

    @patch("workers.retrieval._get_embedding_fn")
    @patch("workers.retrieval._get_collection")
    def test_handles_error_in_run(
        self, mock_get_collection, mock_get_embed_fn,
        mock_collection, mock_embedding_fn
    ):
        """Khi retrieval lỗi, run() phải set empty chunks và log error."""
        mock_get_embed_fn.return_value = mock_embedding_fn
        mock_collection_error = MagicMock()
        mock_collection_error.query.side_effect = Exception("DB error")
        mock_get_collection.return_value = mock_collection_error

        state = {
            "task": "SLA P1 là bao lâu?",
            "retrieval_top_k": 3,
            "workers_called": [],
            "history": [],
        }
        result = run(state)

        assert result["retrieved_chunks"] == []
        assert result["retrieved_sources"] == []
        assert len(result["worker_io_logs"]) > 0
        assert result["worker_io_logs"][-1]["error"] is not None


# =============================================================================
# Integration Test — chạy với ChromaDB thật (nếu có index)
# =============================================================================

@pytest.mark.integration
class TestIntegrationWithChromaDB:
    """Integration tests — yêu cầu ChromaDB index đã được build."""

    def test_retrieve_dense_with_real_data(self):
        """Test retrieve_dense với ChromaDB thật."""
        db_path = Path(__file__).parent.parent / "chroma_db"
        if not db_path.exists():
            pytest.skip("ChromaDB index chưa được build. Chạy python index.py trước.")

        results = retrieve_dense("SLA ticket P1 là bao lâu?", top_k=3)

        assert len(results) > 0, "Phải có ít nhất 1 chunk"
        for chunk in results:
            assert "text" in chunk
            assert "source" in chunk
            assert 0.0 <= chunk["score"] <= 1.0

    def test_run_with_real_data(self):
        """Test run() với ChromaDB thật."""
        db_path = Path(__file__).parent.parent / "chroma_db"
        if not db_path.exists():
            pytest.skip("ChromaDB index chưa được build. Chạy python index.py trước.")

        state = {
            "task": "SLA ticket P1 là bao lâu?",
            "retrieval_top_k": 3,
            "workers_called": [],
            "history": [],
        }
        result = run(state)

        assert len(result["retrieved_chunks"]) > 0
        assert len(result["retrieved_sources"]) > 0
        assert "retrieval_worker" in result["workers_called"]
