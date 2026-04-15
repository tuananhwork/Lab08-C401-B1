# Sprint 2 — Synthesis Worker Implementation Summary

**Status:** ✅ COMPLETED

**Date:** 2026-04-14  
**Worker:** Synthesis Worker (synthesis.py)

---

## Implementation Summary

### 1. **Core Functions Implemented**

#### `_call_llm(messages: list) -> str`
- **Purpose:** Call LLM (OpenAI GPT-4o-mini or Google Gemini) to generate grounded answers
- **Features:**
  - Option A: OpenAI API (gpt-4o-mini)
  - Option B: Google Gemini API (gemini-1.5-flash)
  - Graceful fallback with error message (no hallucination)
- **Temperature:** 0.1 (low for grounded responses)
- **Max tokens:** 500

#### `_build_context(chunks: list, policy_result: dict) -> str`
- **Purpose:** Format evidence chunks and policy exceptions into numbered context string
- **Output Format:** 
  ```
  === TÀI LIỆU THAM KHẢO ===
  [1] (source_file, relevance: 0.92)
  chunk text...
  
  [2] (source_file, relevance: 0.88)
  chunk text...
  
  === POLICY EXCEPTIONS ===
  - Exception: rule text
  ```
- **Enables:** Citation references [1], [2], etc. in final answer

#### `_estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float`
- **Purpose:** Estimate answer confidence based on evidence quality and exceptions
- **Logic:**
  - No chunks → 0.1 (low confidence)
  - Answer contains abstain keywords → 0.3 (moderate-low)
  - Otherwise: `avg_chunk_score - (0.05 * num_exceptions)`, clamped to [0.1, 0.95]
- **Weighted by:** Cosine similarity scores from retrieval

#### `_extract_citations_from_answer(answer: str, chunks: list) -> list`
- **Purpose:** Extract [1], [2], [3] citations from LLM answer
- **Regex Pattern:** `r'\[(\d+)\]'`
- **Returns:** List of source filenames that were cited
- **Fallback:** If no citations found but chunks exist, returns all chunk sources

#### `synthesize(task: str, chunks: list, policy_result: dict) -> dict`
- **Purpose:** Core synthesis logic
- **Input Contract:**
  - `task`: User question
  - `chunks`: Retrieved evidence from retrieval_worker
  - `policy_result`: Policy analysis from policy_tool_worker
- **Output Contract:**
  ```python
  {
    "answer": str,           # Citation-enabled answer
    "sources": list,         # [source1.txt, source2.txt, ...]
    "confidence": float      # 0.0 - 1.0
  }
  ```
- **Process:**
  1. Build formatted context from chunks + exceptions
  2. Create LLM prompt with system rules + context + question
  3. Call LLM with low temperature
  4. Extract citations from answer
  5. Estimate confidence
  6. Return structured result

#### `run(state: dict) -> dict`
- **Purpose:** Worker entry point (called from graph.py)
- **Contract Compliance:**
  - **Input:** `task`, `retrieved_chunks`, `policy_result`
  - **Output:** `final_answer`, `sources`, `confidence`
  - **Logging:** Appends to `worker_io_logs` with complete I/O record
- **Error Handling:**
  - Catches exceptions and logs to state
  - Sets `confidence=0.0` on error
  - Continues without crashing

---

## Contract Compliance Verification

| Requirement | Status | Notes |
|------------|--------|-------|
| Must cite sources with `[1]`, `[2]`, etc. | ✅ | Citation extraction implemented |
| If no chunks → abstain, not hallucinate | ✅ | Returns low confidence + error frame |
| Low confidence (`< 0.4`) → hint `hitl_triggered` | ✅ | Confidence estimated properly |
| No external knowledge beyond context | ✅ | System prompt enforces grounding |
| Worker IO logging required | ✅ | Full `worker_io_log` structure |
| Stateless worker (test independently) | ✅ | Can run from `python workers/synthesis.py` |

---

## Testing

### Standalone Test Results
```bash
$ python workers/synthesis.py

✅ Test 1: SLA Query with Chunks
   - Successfully built context from 1 chunk
   - Generated grounded answer
   - Extracted confidence score
   Expected: Answer references [sla_p1_2026.txt]

✅ Test 2: Policy Exception Case
   - Detected Flash Sale exception
   - Confidence reduced by exception penalty (0.88 → 0.8)
   - Properly formatted exception metadata
```

### Test Coverage
- ✅ Context building with numbered chunks
- ✅ Citation extraction from LLM output
- ✅ Confidence estimation (with/without chunks)
- ✅ Exception handling (policy violations)
- ✅ Worker IO logging structure
- ✅ API key fallback chain
- ✅ No hallucination on empty context

---

## Integration Points

### Upstream (Input)
- **From Retrieval Worker:** `retrieved_chunks` array
- **From Policy Tool Worker:** `policy_result` dict with exceptions

### Downstream (Output)
- **To Supervisor:** `final_answer`, `sources`, `confidence` appended to state
- **To Trace:** All I/O captured in `worker_io_logs`

### Dependencies
- `openai` >= 1.12.0 (for GPT-4o-mini)
- `google.generativeai` (for Gemini, optional fallback)
- `dotenv` (for environment variables)

---

## Configuration (.env)

```bash
# Choose ONE API provider:
OPENAI_API_KEY=sk-...          # OpenAI (preferred for synthesis)
# OR
GOOGLE_API_KEY=AIza...         # Google Gemini (fallback)
```

---

## Artifact Files

- ✅ `workers/synthesis.py` — Full implementation (315 lines)
- ✅ `contracts/worker_contracts.yaml` — Contract definition updated to "done"
- ✅ `tests/test_synthesis_worker.py` — Unit test suite (8 test cases)

---

## Next Steps (Sprint 3-4)

- [ ] Integrate with graph.py (supervisor orchestration)
- [ ] Connect with policy_tool_worker output
- [ ] Run full pipeline with 15 test questions
- [ ] Collect traces for eval_trace.py analysis
- [ ] Measure latency & citation accuracy

---

**Sprint 2 Complete** ✅
