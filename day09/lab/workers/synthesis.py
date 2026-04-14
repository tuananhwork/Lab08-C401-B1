"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
import re
from dotenv import load_dotenv

load_dotenv()

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
3. Trích dẫn nguồn cuối mỗi câu quan trọng dùng format [1], [2], [3], v.v. (ứng với số thứ tự trong TÀI LIỆU THAM KHẢO).
4. Trả lời súc tích, có cấu trúc. Không dài dòng.
5. Nếu có exceptions/ngoại lệ → nêu rõ ràng trước khi kết luận.
6. KHÔNG dùng kiến thức bên ngoài — nếu không có trong context thì phải nói "Không đủ thông tin".
"""


def _call_llm(messages: list) -> str:
    """
    Gọi LLM để tổng hợp câu trả lời.
    Option A: OpenAI (gpt-4o-mini)
    Option B: Gemini (gemini-1.5-flash)
    """
    # Option A: OpenAI
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,  # Low temperature để grounded
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[SYNTHESIS] OpenAI failed: {e}")

    # Option B: Gemini
    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        combined = "\n".join([m["content"] for m in messages])
        response = model.generate_content(combined)
        return response.text
    except Exception as e:
        print(f"[SYNTHESIS] Gemini failed: {e}")

    # Fallback: trả về message báo lỗi (không hallucinate)
    return "[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra OPENAI_API_KEY hoặc GOOGLE_API_KEY trong .env."


def _build_context(chunks: list, policy_result: dict) -> str:
    """
    Xây dựng context string từ chunks và policy result.
    Numbered chunks cho phép citation [1], [2], [3], v.v.
    """
    parts = []

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            # Format rõ ràng cho citation
            parts.append(f"[{i}] ({source}, relevance: {score:.2f})\n{text}")

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            rule = ex.get('rule', '')
            if rule:
                parts.append(f"- Exception: {rule}")

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Ước tính confidence dựa vào:
    - Số lượng và quality của chunks (relevance score)
    - Có exceptions không
    - Answer có abstain không (nhận biết từ từ khóa)
    """
    # Nếu không có evidence → low confidence
    if not chunks:
        return 0.1

    # Nếu LLM abstain (không đủ thông tin) → moderate-low confidence
    abstain_phrases = [
        "Không đủ thông tin",
        "không có trong tài liệu",
        "không có trong",
        "[synthesis error]"
    ]
    if any(phrase.lower() in answer.lower() for phrase in abstain_phrases):
        return 0.3

    # Weighted average của chunk scores (relevance)
    avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks) if chunks else 0

    # Penalty nếu có exceptions (phức tạp hơn = kém tin cậy hơn)
    num_exceptions = len(policy_result.get("exceptions_found", []))
    exception_penalty = 0.05 * num_exceptions

    # Final confidence: avg_score - penalty, clamped to [0.1, 0.95]
    confidence = min(0.95, max(0.1, avg_score - exception_penalty))
    
    return round(confidence, 2)


def _extract_citations_from_answer(answer: str, chunks: list) -> list:
    """
    Trích xuất các citation [1], [2], [3] từ answer.
    Nếu không có citation nhưng có chunks → recommend thêm citations.
    Returns list of source filenames được cite.
    """
    if not chunks:
        return []
    
    # Find all citations in format [1], [2], etc.
    citation_pattern = r'\[(\d+)\]'
    citations = re.findall(citation_pattern, answer)
    
    sources = []
    for citation_idx in set(citations):
        try:
            idx = int(citation_idx) - 1  # Convert to 0-indexed
            if 0 <= idx < len(chunks):
                source = chunks[idx].get("source", "unknown")
                sources.append(source)
        except (ValueError, IndexError):
            pass
    
    return sources


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.
    
    Contract output:
    {
        "answer": str (có citation),
        "sources": list (sources được cite),
        "confidence": float (0.0 - 1.0)
    }
    """
    # Xây dựng context từ evidence
    context = _build_context(chunks, policy_result)
    
    # Build LLM messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Câu hỏi: {task}

{context}

Hãy trả lời câu hỏi dựa vào tài liệu trên. HÃY NHỚ DỬA VÀO CÁC CITATION [1], [2], [3] V.V. từ TÀI LIỆU THAM KHẢO."""
        }
    ]

    # Gọi LLM
    answer = _call_llm(messages)
    
    # Extract sources được cite trong answer
    cited_sources = _extract_citations_from_answer(answer, chunks)
    
    # Nếu không có citation nhưng có chunks → add hint để cty tự cite
    if chunks and not cited_sources:
        print(f"⚠️  [SYNTHESIS] Warning: Answer không có citation mà có {len(chunks)} chunks")
        # Fallback: list all sources
        cited_sources = [c.get("source", "unknown") for c in chunks]
    
    # Estimate confidence
    confidence = _estimate_confidence(chunks, answer, policy_result)
    
    return {
        "answer": answer,
        "sources": cited_sources if cited_sources else [c.get("source", "unknown") for c in chunks],
        "confidence": confidence,
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    
    Contract Input:
        - task: str (câu hỏi)
        - retrieved_chunks: list (optional, evidence từ retrieval_worker)
        - policy_result: dict (optional, result từ policy_tool_worker)
    
    Contract Output:
        - final_answer: str (câu trả lời có citation)
        - sources: list (nguồn được cite)
        - confidence: float (0.0 - 1.0)
        - worker_io_logs: list (append worker IO)
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("worker_io_logs", [])
    
    state["workers_called"].append(WORKER_NAME)

    # Log worker IO theo contract
    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy_result": bool(policy_result),
        },
        "output": None,
        "error": None,
        "timestamp": None,
    }

    try:
        result = synthesize(task, chunks, policy_result)
        
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]

        # Ghi worker IO
        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources_cited": result["sources"],
            "confidence": result["confidence"],
        }
        
        state["history"].append(
            f"[{WORKER_NAME}] SUCCESS: answer generated with confidence={result['confidence']}, "
            f"sources={result['sources']}"
        )

    except Exception as e:
        import traceback
        print(f"[SYNTHESIS] Error: {e}")
        traceback.print_exc()
        
        worker_io["error"] = {
            "code": "SYNTHESIS_FAILED",
            "reason": str(e)
        }
        state["final_answer"] = f"[SYNTHESIS_ERROR] {e}"
        state["confidence"] = 0.0
        state["sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state["worker_io_logs"].append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ. Escalation: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
    }

    result = run(test_state.copy())
    print(f"\nAnswer:\n{result['final_answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")

    print("\n--- Test 2: Exception case ---")
    test_state2 = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Flash Sale không được hoàn tiền."}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")

    print("\n✅ synthesis_worker test done.")
