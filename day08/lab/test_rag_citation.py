import importlib

# Import the module under test
rag = importlib.import_module('rag_answer')


def test_abstain_when_no_chunks():
    """If retrieval returns no chunks, rag_answer should abstain and return empty sources."""
    # Backup original function
    original_retrieve = rag.retrieve_dense
    rag.retrieve_dense = lambda query, top_k=rag.TOP_K_SEARCH, threshold=0.0: []
    try:
        result = rag.rag_answer("Câu hỏi không tồn tại trong tài liệu", retrieval_mode="dense")
        assert result["answer"] == "Toi khong tim thay thong tin nay trong tai lieu noi bo."
        assert result["sources"] == []
        assert result["chunks_used"] == []
        print("test_abstain_when_no_chunks: PASS")
    finally:
        rag.retrieve_dense = original_retrieve


def test_citation_present():
    """When chunks are retrieved, the answer should contain citation markers and sources list should be populated."""
    # Mock a single retrieved chunk
    mock_chunk = {
        "text": "Sample content for testing citation.",
        "metadata": {"source": "test_source.txt", "section": "Test Section"},
        "score": 0.9,
    }
    original_retrieve = rag.retrieve_dense
    rag.retrieve_dense = lambda query, top_k=rag.TOP_K_SEARCH, threshold=0.0: [mock_chunk]
    # Mock call_llm to return a deterministic answer containing a citation marker
    original_call_llm = rag.call_llm
    rag.call_llm = lambda prompt: "Đây là câu trả lời có trích dẫn từ tài liệu [1]."
    try:
        result = rag.rag_answer("Câu hỏi mẫu", retrieval_mode="dense")
        assert "[1]" in result["answer"]
        assert result["sources"] == ["test_source.txt"]
        assert len(result["chunks_used"]) == 1
        assert result["chunks_used"][0]["metadata"]["source"] == "test_source.txt"
        print("test_citation_present: PASS")
    finally:
        rag.retrieve_dense = original_retrieve
        rag.call_llm = original_call_llm

if __name__ == "__main__":
    test_abstain_when_no_chunks()
    test_citation_present()
