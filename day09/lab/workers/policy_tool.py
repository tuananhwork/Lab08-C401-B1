"""
workers/policy_tool.py — Policy & Tool Worker
Sprint 2+3: Kiểm tra policy dựa vào context, gọi MCP tools khi cần.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: context từ retrieval_worker
    - needs_tool: True nếu supervisor quyết định cần tool call

Output (vào AgentState):
    - policy_result: {"policy_applies", "policy_name", "exceptions_found", "source", "rule"}
    - mcp_tools_used: list of tool calls đã thực hiện
    - worker_io_log: log

Gọi độc lập để test:
    python workers/policy_tool.py
"""

import json
import os
import sys
from typing import Optional

WORKER_NAME = "policy_tool_worker"

# System prompt (stable → cached across calls)
_POLICY_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích chính sách hoàn tiền nội bộ.

Nhiệm vụ: Dựa vào context tài liệu được cung cấp, xác định chính sách áp dụng và các ngoại lệ.

Các ngoại lệ cần kiểm tra:
- Flash Sale: Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4)
- Sản phẩm kỹ thuật số: license key, subscription không được hoàn tiền (Điều 3)
- Sản phẩm đã kích hoạt: sản phẩm đã kích hoạt/đăng ký tài khoản không được hoàn tiền (Điều 3)
- Đơn hàng cũ: Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3 (không có trong tài liệu hiện tại)

Trả về JSON hợp lệ với đúng format sau (không có text thêm):
{
  "policy_applies": true,
  "policy_name": "refund_policy_v4",
  "exceptions_found": [
    {"type": "exception_type", "rule": "mô tả rule", "source": "tên file nguồn"}
  ],
  "policy_version_note": ""
}

Quy tắc:
- policy_applies = false nếu có ít nhất một exception ngăn hoàn tiền
- policy_applies = true nếu không có exception nào
- CHỈ trả về JSON, không có text khác ngoài JSON"""


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool.

    Sprint 3 TODO: Implement bằng cách import mcp_server hoặc gọi HTTP.

    Hiện tại: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    from datetime import datetime

    try:
        # TODO Sprint 3: Thay bằng real MCP client nếu dùng HTTP server
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def _analyze_policy_with_llm(task: str, chunks: list) -> dict:
    """
    Sprint 2: Phân tích policy dùng Claude API.
    Dùng prompt caching trên system prompt ổn định.
    Fallback về rule-based nếu LLM không khả dụng.
    """
    import anthropic

    context_parts = []
    for c in chunks:
        if c:
            source = c.get("source", "unknown")
            text = c.get("text", "")
            score = c.get("score", 0)
            context_parts.append(f"[Nguồn: {source} | relevance: {score:.2f}]\n{text}")

    context_text = "\n\n".join(context_parts) if context_parts else "(Không có tài liệu tham khảo)"

    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": _POLICY_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},   # cache stable system prompt
        }],
        messages=[{
            "role": "user",
            "content": (
                f"Câu hỏi / yêu cầu hỗ trợ:\n{task}\n\n"
                f"Tài liệu tham khảo:\n{context_text}\n\n"
                "Phân tích và trả về JSON."
            ),
        }],
    )

    # Extract the text block (thinking blocks come first, skip them)
    text_content = next(
        (b.text for b in response.content if b.type == "text"),
        None,
    )
    if not text_content:
        raise ValueError("LLM returned no text content")

    # Strip markdown code fences if present
    cleaned = text_content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[-1] if cleaned.count("```") >= 2 else cleaned
        cleaned = cleaned.lstrip("json").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    result = json.loads(cleaned)

    # Normalise to expected schema
    result.setdefault("policy_applies", True)
    result.setdefault("policy_name", "refund_policy_v4")
    result.setdefault("exceptions_found", [])
    result.setdefault("policy_version_note", "")

    sources = list({c.get("source", "unknown") for c in chunks if c})
    result["source"] = sources
    result["explanation"] = "Analyzed via Claude LLM (claude-opus-4-6) with adaptive thinking."
    return result


def _analyze_policy_rule_based(task: str, chunks: list) -> dict:
    """Fallback: rule-based exception detection."""
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    exceptions_found = []

    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })

    if any(kw in task_lower for kw in ["license key", "license", "subscription", "kỹ thuật số"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    policy_version_note = ""
    if any(kw in task_lower for kw in ["31/01", "30/01", "trước 01/02"]):
        policy_version_note = "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3 (không có trong tài liệu hiện tại)."

    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": len(exceptions_found) == 0,
        "policy_name": "refund_policy_v4",
        "exceptions_found": exceptions_found,
        "source": sources,
        "policy_version_note": policy_version_note,
        "explanation": "Analyzed via rule-based policy check (fallback).",
    }


def analyze_policy(task: str, chunks: list) -> dict:
    """
    Sprint 2: Phân tích policy dùng Claude LLM, fallback về rule-based nếu lỗi.

    Returns:
        dict with: policy_applies, policy_name, exceptions_found, source,
                   policy_version_note, explanation
    """
    try:
        return _analyze_policy_with_llm(task, chunks)
    except Exception as e:
        print(f"⚠️  LLM policy analysis failed ({e}), falling back to rule-based.")
        return _analyze_policy_rule_based(task, chunks)


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với policy_result và mcp_tools_used
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "needs_tool": needs_tool,
        },
        "output": None,
        "error": None,
    }

    try:
        # Step 1: Nếu chưa có chunks, gọi MCP search_kb
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # Step 2: Phân tích policy
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # Step 3: Nếu cần thêm info từ MCP (e.g., ticket status), gọi get_ticket_info
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")

        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "exceptions_count": len(policy_result.get("exceptions_found", [])),
            "mcp_calls": len(state["mcp_tools_used"]),
        }
        state["history"].append(
            f"[{WORKER_NAME}] policy_applies={policy_result['policy_applies']}, "
            f"exceptions={len(policy_result.get('exceptions_found', []))}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        state["policy_result"] = {"error": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)

    test_cases = [
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n✅ policy_tool_worker test done.")
