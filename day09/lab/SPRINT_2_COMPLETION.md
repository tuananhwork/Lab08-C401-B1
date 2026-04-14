# Synthesis Worker — Sprint 2 Completion Checklist

## ✅ Definition of Done — ALL COMPLETED

### Code Implementation
- [x] `synthesize()` function implemented with LLM call
- [x] Input validation: `task`, `retrieved_chunks`, `policy_result`
- [x] Output contract: `answer`, `sources`, `confidence`
- [x] Citation extraction from answer using regex `[1]`, `[2]`, etc.
- [x] Confidence estimation (0.0-1.0 range, weighted by relevance scores)
- [x] Error handling with graceful fallback
- [x] No hallucination on empty chunks (abstains with low confidence)

### Worker Contract Compliance
- [x] Input/output matches `contracts/worker_contracts.yaml`
- [x] Error format: `{"code": "SYNTHESIS_FAILED", "reason": string}`
- [x] Worker IO logging: `worker_io_logs` appended with full metadata
- [x] Citation requirement: `[1]` to `[n]` references in answer
- [x] Confidence with exceptions: `-0.05 * num_exceptions` penalty
- [x] Stateless: tested independently via `python workers/synthesis.py`

### Testing
- [x] Standalone test 1: Query with chunks → proper citation
- [x] Standalone test 2: Exception case → confidence reduced
- [x] Test suite created: `tests/test_synthesis_worker.py` (8 test cases)
- [x] API key handling: fallback from OpenAI → Gemini → error message
- [x] Verification: Runs without crashing when API keys missing

### Documentation
- [x] Docstrings for all functions
- [x] System prompt explains citation format
- [x] Contract documentation updated to "done"
- [x] Implementation notes in `contracts/worker_contracts.yaml`
- [x] Summary document: `docs/SYNTHESIS_WORKER_DONE.md`

### Integration Readiness
- [x] Compatible with graph.py state schema
- [x] Compatible with retrieval_worker output
- [x] Compatible with policy_tool_worker output
- [x] Worker IO format matches trace specification
- [x] Ready for Sprint 3 integration with graph orchestrator

---

## Key Features Implemented

### 1. **Grounded LLM Generation**
```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": f"Question: {task}\n\n{context}\n..."}
]
answer = _call_llm(messages)
```

### 2. **Citation Extraction**
```python
citations = re.findall(r'\[(\d+)\]', answer)
sources = [chunks[int(c)-1].get("source") for c in citations]
```

### 3. **Confidence Scoring**
```python
confidence = min(0.95, max(0.1, avg_score - exception_penalty))
```

### 4. **Exception Handling**
```python
exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
```

---

## Contract Compliance Matrix

| Contract Element | Value | Evidence |
|-----------------|-------|----------|
| **Input: task** | ✅ | Line 247: `state.get("task", "")` |
| **Input: retrieved_chunks** | ✅ | Line 248: `state.get("retrieved_chunks", [])` |
| **Input: policy_result** | ✅ | Line 249: `state.get("policy_result", {})` |
| **Output: final_answer** | ✅ | Line 261: `state["final_answer"] = result["answer"]` |
| **Output: sources** | ✅ | Line 262: `state["sources"] = result["sources"]` |
| **Output: confidence** | ✅ | Line 263: `state["confidence"] = result["confidence"]` |
| **Output: worker_io_logs** | ✅ | Line 285: `state["worker_io_logs"].append(worker_io)` |
| **Error code** | ✅ | Line 276: `"code": "SYNTHESIS_FAILED"` |
| **Citation format [n]** | ✅ | Line 79-88: `_extract_citations_from_answer()` |
| **No hallucination** | ✅ | Line 101: Confidence 0.1-0.3 for no/empty chunks |
| **Stateless** | ✅ | Line 331-355: Standalone test runs independently |

---

## Example Output

```json
{
  "final_answer": "SLA P1 ticket phải có phản hồi ban đầu trong 15 phút [1]. Nếu không có phản hồi, ticket được escalate tự động lên Senior Engineer sau 10 phút [1].",
  "sources": ["sla_p1_2026.txt"],
  "confidence": 0.92,
  "worker_io_logs": [
    {
      "worker": "synthesis_worker",
      "input": {
        "task": "SLA ticket P1 là bao lâu?",
        "chunks_count": 1,
        "has_policy_result": false
      },
      "output": {
        "answer_length": 120,
        "sources_cited": ["sla_p1_2026.txt"],
        "confidence": 0.92
      },
      "error": null,
      "timestamp": null
    }
  ]
}
```

---

## Ready for Next Phases

✅ **Sprint 3:** MCP integration (policy_tool_worker calls dispatch_tool)  
✅ **Sprint 4:** Trace collection and evaluation (eval_trace.py)  
✅ **Integration:** graph.py supervisor orchestration

---

**Status:** 🎉 **SPRINT 2 SYNTHESIS WORKER COMPLETE**
