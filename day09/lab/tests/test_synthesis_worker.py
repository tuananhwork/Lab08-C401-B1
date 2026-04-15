"""
test_synthesis_worker.py — Unit tests for Synthesis Worker
Sprint 2: Verify synthesis worker meets contract requirements
"""

import sys
import os
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workers.synthesis import run, synthesize, _extract_citations_from_answer, _build_context


def test_synthesis_with_chunks():
    """Test synthesize() with valid chunks."""
    print("\n▶ TEST: synthesize with chunks")
    
    state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
    }
    
    result = run(state)
    
    # Verify output contract
    assert "final_answer" in result, "final_answer not in state"
    assert "sources" in result, "sources not in state"
    assert "confidence" in result, "confidence not in state"
    assert "worker_io_logs" in result, "worker_io_logs not in state"
    
    # Verify confidence is in valid range
    assert 0.0 <= result["confidence"] <= 1.0, f"confidence out of range: {result['confidence']}"
    
    # Verify worker IO log
    assert len(result["worker_io_logs"]) > 0, "worker_io_logs is empty"
    log = result["worker_io_logs"][-1]
    assert log["worker"] == "synthesis_worker", "worker name mismatch"
    assert log["output"] is not None, "worker output is None"
    
    print(f"✅ Answer: {result['final_answer'][:80]}...")
    print(f"✅ Confidence: {result['confidence']}")
    print(f"✅ Sources: {result['sources']}")


def test_synthesis_no_chunks():
    """Test synthesize() with NO chunks (should abstain and low confidence)."""
    print("\n▶ TEST: synthesize with no chunks")
    
    state = {
        "task": "Some random question?",
        "retrieved_chunks": [],
        "policy_result": {},
    }
    
    result = run(state)
    
    # Should still have output, but with low confidence
    assert result["confidence"] <= 0.3, f"Expected low confidence for no chunks, got {result['confidence']}"
    assert len(result["sources"]) == 0, "Expected no sources"
    
    print(f"✅ Abstain properly with confidence={result['confidence']}")


def test_synthesis_with_policy_exception():
    """Test synthesis with policy exception."""
    print("\n▶ TEST: synthesize with policy exception")
    
    state = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ Flash Sale: Không được hoàn tiền theo chính sách v4 Điều 3.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [
                {
                    "type": "flash_sale_exception",
                    "rule": "Flash Sale exceptions: refunds not permitted"
                }
            ],
        },
    }
    
    result = run(state)
    
    # Policy exceptions should reduce confidence
    assert result["confidence"] < 0.88, "confidence should be reduced by exception penalty"
    assert result["sources"] is not None, "sources should not be None"
    
    print(f"✅ Exception handled: confidence={result['confidence']} (penalized from ~0.88)")


def test_extract_citations():
    """Test citation extraction from answer."""
    print("\n▶ TEST: citation extraction")
    
    chunks = [
        {"source": "file1.txt", "text": "text1", "score": 0.9},
        {"source": "file2.txt", "text": "text2", "score": 0.85},
    ]
    
    # Test with citations
    answer_with_citations = "According to the policy [1], this is allowed [2]."
    sources = _extract_citations_from_answer(answer_with_citations, chunks)
    assert sources == ["file1.txt", "file2.txt"], f"Expected ['file1.txt', 'file2.txt'], got {sources}"
    print(f"✅ Extracted citations: {sources}")
    
    # Test without citations
    answer_no_citations = "This is a plain answer"
    sources = _extract_citations_from_answer(answer_no_citations, chunks)
    assert sources == [], f"Expected empty list for no citations, got {sources}"
    print(f"✅ Handled no citations correctly")


def test_build_context():
    """Test context building."""
    print("\n▶ TEST: context building")
    
    chunks = [
        {"source": "file1.txt", "text": "Evidence 1", "score": 0.9},
        {"source": "file2.txt", "text": "Evidence 2", "score": 0.85},
    ]
    
    policy_result = {
        "exceptions_found": [
            {"rule": "Exception rule 1"},
            {"rule": "Exception rule 2"},
        ]
    }
    
    context = _build_context(chunks, policy_result)
    
    assert "file1.txt" in context, "source not in context"
    assert "Evidence 1" in context, "evidence not in context"
    assert "[1]" in context, "chunk numbering not in context"
    assert "[2]" in context, "chunk numbering not in context"
    assert "POLICY EXCEPTIONS" in context, "exceptions section not in context"
    
    print(f"✅ Context built correctly with {len(chunks)} chunks and exceptions")


def test_worker_io_logging():
    """Test that worker IO is properly logged."""
    print("\n▶ TEST: worker IO logging")
    
    state = {
        "task": "Test question",
        "retrieved_chunks": [
            {"source": "test.txt", "text": "Test content", "score": 0.9}
        ],
        "policy_result": {},
    }
    
    result = run(state)
    
    # Verify worker IO structure
    log = result["worker_io_logs"][-1]
    assert log["worker"] == "synthesis_worker"
    assert log["input"]["task"] == "Test question"
    assert log["input"]["chunks_count"] == 1
    assert log["output"] is not None
    assert "answer_length" in log["output"]
    assert "sources_cited" in log["output"]
    assert "confidence" in log["output"]
    
    # Verify history is updated
    assert any("synthesis_worker" in h for h in result.get("history", [])), "history not updated"
    
    print(f"✅ Worker IO logged correctly")


def test_empty_chunks_doesnt_hallucinate():
    """
    Test contract requirement:
    "Nếu retrieved_chunks=[] → phải abstain, không hallucinate"
    """
    print("\n▶ TEST: no hallucination with empty chunks")
    
    state = {
        "task": "What is the capital of France?",
        "retrieved_chunks": [],  # No context!
        "policy_result": {},
    }
    
    result = run(state)
    
    # Should have low confidence
    assert result["confidence"] <= 0.3, f"Expected low confidence, got {result['confidence']}"
    
    # Should NOT have valid sources
    assert len(result["sources"]) == 0, "Should not cite sources when no chunks provided"
    
    print(f"✅ Proper abstention with confidence={result['confidence']}")


if __name__ == "__main__":
    print("=" * 60)
    print("SYNTHESIS WORKER — STANDALONE UNIT TESTS")
    print("Sprint 2: Verify contract compliance")
    print("=" * 60)
    
    try:
        test_synthesis_with_chunks()
        test_synthesis_no_chunks()
        test_synthesis_with_policy_exception()
        test_extract_citations()
        test_build_context()
        test_worker_io_logging()
        test_empty_chunks_doesnt_hallucinate()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
