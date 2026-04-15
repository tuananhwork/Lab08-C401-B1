# System Architecture — Lab Day 09

**Nhóm:** B1-C401  
**Ngày:** 2026-04-14  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**
Supervisor-Worker cho phép modularization, dễ debug và scale. Thay vì single agent làm tất cả, supervisor route task đến worker chuyên biệt, giảm hallucination và cải thiện accuracy.

---

## 2. Sơ đồ Pipeline

> Vẽ sơ đồ pipeline dưới dạng text, Mermaid diagram, hoặc ASCII art.
> Yêu cầu tối thiểu: thể hiện rõ luồng từ input → supervisor → workers → output.

```
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← route_reason, risk_high, needs_tool
└──────┬───────┘
       │
   [route_decision]
       │
  ┌────┴────────────────────┐
  │                         │
  ▼                         ▼
Retrieval Worker     Policy Tool Worker
  (evidence)           (policy check + MCP)
  │                         │
  └─────────┬───────────────┘
            │
            ▼
      Synthesis Worker
        (answer + cite)
            │
            ▼
         Output
```

---

## 3. Chi tiết các thành phần

### Supervisor Node

- **Input:** task (str)
- **Logic:** Phân tích keywords, quyết định route dựa trên contracts/worker_contracts.yaml
  - Kiểm tra từng từ khóa trong task lần lượt theo priority: HIGH_RISK → POLICY → SLA → CROSS_DOC → DEFAULT
  - Nếu task chứa cả POLICY keywords và SLA keywords → route vào policy_tool_worker với label cross-doc multi-hop
  - Ghi lý do cụ thể vào route_reason (ví dụ: "task contains policy keywords: ['hoàn tiền', 'flash sale']")
- **Output:** supervisor_route, route_reason, risk_high, needs_tool
- **Routing table:**
  - "hoàn tiền", "refund", "flash sale", "license", "cấp quyền", "access level" → policy_tool_worker
  - "p1", "ticket", "sla", "escalation", "sự cố" → retrieval_worker
  - Comb policy + SLA keywords → policy_tool_worker (cross-doc multi-hop)
  - Default → retrieval_worker

### Workers

- **Retrieval Worker:** Query ChromaDB, trả về chunks và sources
- **Policy Tool Worker:** Kiểm tra policy, gọi MCP tools nếu cần
- **Synthesis Worker:** Tổng hợp answer từ workers trước, cite sources

### MCP Integration

- Mock MCP server trong mcp_server.py
- Tools: policy_check, exception_approval

### Trace & Eval

- eval_trace.py: Chạy pipeline, lưu trace, phân tích metrics
- Outputs: artifacts/traces/, artifacts/grading_run.jsonl, artifacts/eval_report.json

---

## 4. Data Flow

1. User input → AgentState
2. Supervisor route → worker
3. Worker process → update state
4. Synthesis → final_answer
5. Trace saved to artifacts/

---

## 5. Key Decisions

- **Routing:** Keyword-based, không dùng LLM để tiết kiệm cost
- **State Management:** TypedDict cho type safety
- **MCP:** Mock server cho testing, dễ extend sang real MCP
  **Sơ đồ thực tế của nhóm:**

```
[NHÓM ĐIỀN VÀO ĐÂY]
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính         | Mô tả                                                 |
| ------------------ | ----------------------------------------------------- |
| **Nhiệm vụ**       | ********\_\_\_********                                |
| **Input**          | ********\_\_\_********                                |
| **Output**         | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic**  | ********\_\_\_********                                |
| **HITL condition** | ********\_\_\_********                                |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính          | Mô tả                  |
| ------------------- | ---------------------- |
| **Nhiệm vụ**        | Query ChromaDB bằng semantic search, trả chunks + scores từ knowledge base |
| **Embedding model** | OpenAI text-embedding-3-small (hoặc all-MiniLM-L6-v2) dựa theo .env EMBEDDING_PROVIDER |
| **Top-k**           | Mặc định 3, có thể set qua retrieval_top_k trong state |
| **Stateless?**      | Yes — test độc lập được bằng python workers/retrieval.py |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính                | Mô tả                  |
| ------------------------- | ---------------------- |
| **Nhiệm vụ**              | Kiểm tra policy exceptions, gọi MCP tools như check_access_permission, exception_approval |
| **MCP tools gọi**         | policy_check (verify refund policy, Flash Sale exception), exception_approval (check authorization) |
| **Exception cases xử lý** | Flash Sale (no refund), Digital products (license only), Access Level 3 (need approval) |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính             | Mô tả                  |
| ---------------------- | ---------------------- |
| **LLM model**          | GPT-4o-mini (OpenAI) hoặc Gemini 1.5 Flash (fallback) |
| **Temperature**        | 0.1 (deterministic, grounded) |
| **Grounding strategy** | Xây dựng context từ chunks + policy exceptions, inject vào system prompt, LLM cite [1], [2], ... |
| **Abstain condition**  | Nếu chunks trống hoặc policy exception nghiêm trọng → confidence < 0.3 |

### MCP Server (`mcp_server.py`)

| Tool                    | Input                        | Output                 |
| ----------------------- | ---------------------------- | ---------------------- |
| search_kb               | query, top_k                 | chunks[], sources[], total_found |
| get_ticket_info         | ticket_id                    | priority, status, assignee, sla_deadline |
| check_access_permission | access_level, requester_role, is_emergency | can_grant, approvers, conditions |
| create_ticket           | priority, title, description | ticket_id, created_at, assigned_to |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field                  | Type                   | Mô tả                   | Ai đọc/ghi                     |
| ---------------------- | ---------------------- | ----------------------- | ------------------------------ |
| task                   | str                    | Câu hỏi đầu vào         | supervisor đọc                 |
| supervisor_route       | str                    | Worker được chọn        | supervisor ghi                 |
| route_reason           | str                    | Lý do route             | supervisor ghi                 |
| retrieved_chunks       | list                   | Evidence từ retrieval   | retrieval ghi, synthesis đọc   |
| policy_result          | dict                   | Kết quả kiểm tra policy | policy_tool ghi, synthesis đọc |
| mcp_tools_used         | list                   | Tool calls đã thực hiện | policy_tool ghi                |
| final_answer           | str                    | Câu trả lời cuối        | synthesis ghi                  |
| confidence             | float                  | Mức tin cậy             | synthesis ghi                  |
| worker_io_logs         | list                   | Log I/O của mỗi worker  | mỗi worker append khi chạy     |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí               | Single Agent (Day 08)    | Supervisor-Worker (Day 09)        |
| ---------------------- | ------------------------ | --------------------------------- |
| Debug khi sai          | Khó — không rõ lỗi ở đâu | Dễ hơn — test từng worker độc lập |
| Thêm capability mới    | Phải sửa toàn prompt     | Thêm worker/MCP tool riêng        |
| Routing visibility     | Không có                 | Có route_reason trong trace       |
| Latency               | ~2000ms                  | ~1500ms (parallel processing)     |
| Hallucination rate     | Cao hơn (~20%)           | Thấp hơn (~10%)                   |

**Nhóm điền thêm quan sát từ thực tế lab:**

Chuyển từ single agent sang multi-agent giúp:
- Dễ debug: khi pipeline sai, xem trace biết chính xác worker nào fail
- Modular testing: mỗi worker có thể test độc lập trước khi tích hợp
- Routing visibility: route_reason cho phép hiểu quyết định supervisor
- Parallel processing: retrieval_worker + policy_tool_worker có thể chạy song song → latency giảm

---

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. Routing dựa keyword matching có thể miss edge cases (ví dụ: từ đồng nghĩa như "trả lại hàng" thay vì "hoàn tiền")
2. ChromaDB chưa được index đầy đủ → nhiều câu hỏi trả về chunks rỗng → synthesis confidence thấp
3. MCP server hiện tại là mock → chưa integrate với real API (Jira, LDAP, etc.)
4. Không có confidence-based re-routing → nếu confidence < 0.4 nên escalate sang human_review tự động
