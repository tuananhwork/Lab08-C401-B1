"""
graph.py — Supervisor Orchestrator
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

Chạy thử:
    python graph.py
"""

import json
import os
from datetime import datetime
from typing import TypedDict, Literal, Optional

from dotenv import load_dotenv
load_dotenv()

# Uncomment nếu dùng LangGraph:
# from langgraph.graph import StateGraph, END

# ─────────────────────────────────────────────
# 1. Shared State — dữ liệu đi xuyên toàn graph
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    task: str                           # Câu hỏi đầu vào từ user

    # Supervisor decisions
    route_reason: str                   # Lý do route sang worker nào
    risk_high: bool                     # True → cần HITL hoặc human_review
    needs_tool: bool                    # True → cần gọi external tool qua MCP
    hitl_triggered: bool                # True → đã pause cho human review

    # Worker outputs
    retrieved_chunks: list              # Output từ retrieval_worker
    retrieved_sources: list             # Danh sách nguồn tài liệu
    policy_result: dict                 # Output từ policy_tool_worker
    mcp_tools_used: list                # Danh sách MCP tools đã gọi

    # Final output
    final_answer: str                   # Câu trả lời tổng hợp
    sources: list                       # Sources được cite
    confidence: float                   # Mức độ tin cậy (0.0 - 1.0)

    # Trace & history
    history: list                       # Lịch sử các bước đã qua
    workers_called: list                # Danh sách workers đã được gọi
    supervisor_route: str               # Worker được chọn bởi supervisor
    latency_ms: Optional[int]           # Thời gian xử lý (ms)
    run_id: str                         # ID của run này


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
    return {
        "task": task,
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "workers_called": [],
        "supervisor_route": "",
        "latency_ms": None,
        "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    }


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

# ─── Routing keyword tables ───────────────────────────────────
# Dựa theo contracts/worker_contracts.yaml → routing_rules

_POLICY_KEYWORDS = [
    # Refund & sales keywords
    "hoàn tiền", "refund", "hoàn trả", "flash sale", "khuyến mãi",
    # Digital product / license
    "license", "license key", "subscription", "kỹ thuật số",
    # Access control
    "cấp quyền", "access level", "access control",
    "level 1", "level 2", "level 3",
    "admin access", "tạm thời", "temporary access",
    "contractor",
]

_SLA_TICKET_KEYWORDS = [
    "p1", "ticket", "escalation", "sla", "sự cố",
    "incident", "on-call", "oncall", "2am", "2 am",
    "priority 1",
]

_HIGH_RISK_KEYWORDS = [
    "emergency", "khẩn cấp", "2am", "2 am",
    "level 3", "level 2", "tạm thời", "temporary",
]

_HUMAN_REVIEW_PATTERN = "err-"


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào (retrieval | policy_tool | human_review)
    2. Có cần MCP tool không (needs_tool)
    3. Có risk cao cần HITL không (risk_high)

    Routing rules (theo contracts/worker_contracts.yaml):
    - refund / flash sale / license / cấp quyền / access level → policy_tool_worker
    - P1 / SLA / ticket / escalation / sự cố              → retrieval_worker
    - ERR-xxx code không rõ + risk_high                   → human_review
    - default                                              → retrieval_worker
    """
    task = state["task"]
    task_lower = task.lower()
    state["history"].append(f"[supervisor] received task: {task[:80]}")

    route = "retrieval_worker"
    route_reason = "default: no specific keyword matched → retrieval_worker"
    needs_tool = False
    risk_high = False
    matched_keywords = []

    # ── Step 1: Detect risk keywords ──────────────────────────
    matched_risk = [kw for kw in _HIGH_RISK_KEYWORDS if kw in task_lower]
    if matched_risk:
        risk_high = True

    # ── Step 2: Detect policy/access keywords ─────────────────
    matched_policy = [kw for kw in _POLICY_KEYWORDS if kw in task_lower]
    if matched_policy:
        route = "policy_tool_worker"
        needs_tool = True
        matched_keywords = matched_policy
        route_reason = f"task contains policy/access keywords: {matched_policy}"

    # ── Step 3: SLA/ticket keywords always go to retrieval ────
    #    (SLA questions need document lookup first)
    matched_sla = [kw for kw in _SLA_TICKET_KEYWORDS if kw in task_lower]
    if matched_sla and not matched_policy:
        route = "retrieval_worker"
        matched_keywords = matched_sla
        route_reason = f"task contains SLA/ticket keywords: {matched_sla}"

    # ── Step 4: Cross-doc (SLA + policy both present) ─────────
    #    e.g. 'P1 lúc 2am + cần cấp quyền' → policy_tool handles both
    if matched_sla and matched_policy:
        route = "policy_tool_worker"
        needs_tool = True
        route_reason = (
            f"cross-doc multi-hop: SLA keywords {matched_sla} "
            f"+ policy keywords {matched_policy} → policy_tool_worker"
        )

    # ── Step 5: Human review override ─────────────────────────
    #    Unknown error code (ERR-xxx) + risk_high → HITL
    import re
    if risk_high and re.search(r"err-[a-z0-9]+", task_lower):
        route = "human_review"
        needs_tool = False
        route_reason = "unknown ERR-xxx code + risk_high → human_review (HITL)"

    # ── Append risk flag to reason if set ─────────────────────
    if risk_high and "risk_high" not in route_reason:
        route_reason += " | risk_high=True"

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(
        f"[supervisor] route={route} | reason={route_reason} | "
        f"risk_high={risk_high} | needs_tool={needs_tool}"
    )

    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore


# ─────────────────────────────────────────────
# 4. Human Review Node — HITL placeholder
# ─────────────────────────────────────────────

def human_review_node(state: AgentState) -> AgentState:
    """
    HITL node: pause và chờ human approval.
    Trong lab này, implement dưới dạng placeholder (in ra warning).

    TODO Sprint 3 (optional): Implement actual HITL với interrupt_before hoặc
    breakpoint nếu dùng LangGraph.
    """
    state["hitl_triggered"] = True
    state["history"].append("[human_review] HITL triggered — awaiting human input")
    state["workers_called"].append("human_review")

    # Placeholder: tự động approve để pipeline tiếp tục
    print(f"\n⚠️  HITL TRIGGERED")
    print(f"   Task: {state['task']}")
    print(f"   Reason: {state['route_reason']}")
    print(f"   Action: Auto-approving in lab mode (set hitl_triggered=True)\n")

    # Sau khi human approve, route về retrieval để lấy evidence
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved → retrieval"

    return state


# ─────────────────────────────────────────────
# 5. Import Workers (Sprint 2: real implementations)
# ─────────────────────────────────────────────

try:
    from workers.retrieval import run as _retrieval_run
    _HAS_RETRIEVAL = True
except Exception:
    _HAS_RETRIEVAL = False

try:
    from workers.policy_tool import run as _policy_tool_run
    _HAS_POLICY = True
except Exception:
    _HAS_POLICY = False

try:
    from workers.synthesis import run as _synthesis_run
    _HAS_SYNTHESIS = True
except Exception:
    _HAS_SYNTHESIS = False


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker."""
    if _HAS_RETRIEVAL:
        return _retrieval_run(state)

    # Placeholder — chạy khi Sprint 2 chưa implement
    state["workers_called"].append("retrieval_worker")
    state["history"].append("[retrieval_worker] PLACEHOLDER (Sprint 2 not done yet)")
    state["retrieved_chunks"] = [
        {"text": "SLA P1: phản hồi trong 15 phút, xử lý trong 4 giờ.",
         "source": "sla_p1_2026.txt", "score": 0.92},
        {"text": "Chính sách hoàn tiền: trong 30 ngày kể từ ngày mua.",
         "source": "policy_refund_v4.txt", "score": 0.88},
    ]
    state["retrieved_sources"] = ["sla_p1_2026.txt", "policy_refund_v4.txt"]
    state["history"].append(
        f"[retrieval_worker] retrieved {len(state['retrieved_chunks'])} chunks (placeholder)"
    )
    return state


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    if _HAS_POLICY:
        return _policy_tool_run(state)

    # Placeholder
    state["workers_called"].append("policy_tool_worker")
    state["history"].append("[policy_tool_worker] PLACEHOLDER (Sprint 2 not done yet)")
    state["policy_result"] = {
        "policy_applies": True,
        "policy_name": "refund_policy_v4",
        "exceptions_found": [],
        "source": "policy_refund_v4.txt",
    }
    state["history"].append("[policy_tool_worker] policy check complete (placeholder)")
    return state


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    if _HAS_SYNTHESIS:
        return _synthesis_run(state)

    # Placeholder
    state["workers_called"].append("synthesis_worker")
    state["history"].append("[synthesis_worker] PLACEHOLDER (Sprint 2 not done yet)")
    chunks = state.get("retrieved_chunks", [])
    sources = state.get("retrieved_sources", [])
    state["final_answer"] = (
        f"[PLACEHOLDER] Tổng hợp từ {len(chunks)} chunks. "
        f"Sources: {', '.join(sources) if sources else 'none'}"
    )
    state["sources"] = sources
    state["confidence"] = 0.50
    state["history"].append(
        f"[synthesis_worker] answer generated (placeholder), confidence={state['confidence']}"
    )
    return state


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern.

    Option A (đơn giản — Python thuần): Dùng if/else, không cần LangGraph.
    Option B (nâng cao): Dùng LangGraph StateGraph với conditional edges.

    Lab này implement Option A theo mặc định.
    TODO Sprint 1: Có thể chuyển sang LangGraph nếu muốn.
    """
    # Option A: Simple Python orchestrator (không cần LangGraph)
    def run(state: AgentState) -> AgentState:
        import time
        start = time.time()

        # Step 1: Supervisor quyết định route
        state = supervisor_node(state)
        route = route_decision(state)

        # Step 2: Route sang worker phù hợp
        # Lưu ý: policy_tool_worker cần retrieved_chunks làm context
        # → luôn chạy retrieval trước khi policy check
        if route == "human_review":
            state = human_review_node(state)
            # Sau khi human approve → chạy retrieval
            state = retrieval_worker_node(state)

        elif route == "policy_tool_worker":
            # Retrieval first → policy_tool sử dụng chunks làm evidence
            state = retrieval_worker_node(state)
            state = policy_tool_worker_node(state)

        else:
            # Default: retrieval_worker
            state = retrieval_worker_node(state)

        # Step 3: Synthesis luôn chạy cuối
        state = synthesis_worker_node(state)

        state["latency_ms"] = int((time.time() - start) * 1000)
        state["history"].append(
            f"[graph] completed | workers={state['workers_called']} | "
            f"latency={state['latency_ms']}ms"
        )
        return state

    return run


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.

    Args:
        task: Câu hỏi từ user

    Returns:
        AgentState với final_answer, trace, routing info, v.v.
    """
    state = make_initial_state(task)
    result = _graph(state)
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


# ─────────────────────────────────────────────
# 8. Manual Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:100]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2.")
