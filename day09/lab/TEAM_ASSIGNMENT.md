# 📋 TEAM ASSIGNMENT — Day 09 Multi-Agent Lab (6 người)

**Dự án:** Multi-Agent Orchestration: Supervisor → Workers → MCP → Trace & Eval  
**Thời gian:** 4 tiếng (4 sprints × 60 phút)  
**Deadline nộp code + log:** 18:00  
**Deadline báo cáo:** Sau 18:00  

**Nguyên tắc:** 6 người bình đẳng, không role lãnh đạo, mỗi người commit ở các sprint khác nhau, task xoay vòng

---

## Group information

| Person   | Full name          |
| -------- | ------------------ |
| Person 1 | Chu Thị Ngọc Huyền |
| Person 2 | Chu Bá Tuấn Anh    |
| Person 3 | Nguyễn Mai Phương  |
| Person 4 | Hứa Quang Linh     |
| Person 5 | Nguyễn Thị Tuyết   |
| Person 6 | Nguyễn Văn Lĩnh    |

## 📊 Phân công công việc (Sprint 1–4)

Mỗi sprint có **6 công việc song song**, mỗi người nhận 1 công việc/sprint. Công việc xoay vòng để tất cả có kinh nghiệm mọi phần của pipeline.

---

### **SPRINT 1 (0:00–1:00) — Refactor Graph (graph.py)**

**Mục tiêu:** Xây dựng Supervisor + routing logic trong `graph.py`.

| Person       | Task                                                                                                                                              | Output                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Person 1** | **Task 1A:** Thiết kế `AgentState` — định nghĩa tất cả fields (task, route_reason, history, risk_high, retrieved_chunks, policy_result, v.v.).    | `AgentState` TypedDict/dataclass + field list  |
| **Person 2** | **Task 1B:** Implement `supervisor_node()` — đọc task, phân tích signal, quyết định route, ghi `route_reason` rõ ràng vào state.                  | `supervisor_node()` function                   |
| **Person 3** | **Task 1C:** Implement `route_decision()` — routing logic dựa vào keywords (P1/SLA → retrieval, hoàn tiền/policy → policy_tool, v.v.). Test 5 cases. | `route_decision()` function + test cases       |
| **Person 4** | **Task 1D:** Implement graph wiring — kết nối nodes + conditional edges: `supervisor → route → [retrieval \| policy_tool \| human_review] → synthesis → END`. | Graph structure + node connections             |
| **Person 5** | **Task 1E:** Viết ≥3 test queries (SLA/retrieval, policy/refund, multi-hop), chạy `graph.invoke()` với từng query, ghi trace output ra console.  | Test queries + initial run log                 |
| **Person 6** | **Task 1F:** Tạo `contracts/worker_contracts.yaml` skeleton — định nghĩa input/output cho Supervisor và 3 workers (retrieval, policy_tool, synthesis). | `worker_contracts.yaml` v1 (skeleton)          |

**Sprint 1 Definition of Done:**
- [ ] `python graph.py` chạy không lỗi
- [ ] Supervisor route đúng ít nhất **2 loại** câu hỏi khác nhau (retrieval vs policy_tool)
- [ ] Trace ghi `route_reason` không phải "unknown"
- [ ] `AgentState` có đủ fields: `task`, `route_reason`, `history`, `risk_high`

---

### **SPRINT 2 (1:00–2:00) — Build Workers (workers/)**

**Mục tiêu:** Implement 3 workers độc lập, test từng worker riêng, khớp contracts.

| Person       | Task                                                                                                                                                          | Output                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **Person 1** | **Task 2A:** Implement `workers/retrieval.py` — `run(state)`: nhận query từ state, gọi ChromaDB, trả về `retrieved_chunks` + `worker_io_log` vào state.      | `retrieval.py` — `run()` function                 |
| **Person 2** | **Task 2B:** Implement `workers/policy_tool.py` — `run(state)`: kiểm tra policy từ chunks, xử lý exception case (Flash Sale / digital product), ghi `policy_result`. | `policy_tool.py` — `run()` + 1 exception case  |
| **Person 3** | **Task 2C:** Implement `workers/synthesis.py` — `run(state)`: tổng hợp answer từ chunks + policy_result, gọi LLM, output `answer` + `sources` + `confidence`. | `synthesis.py` — `run()` function                 |
| **Person 4** | **Task 2D:** Cập nhật `contracts/worker_contracts.yaml` với `actual_implementation` khớp từng worker. Thêm ví dụ I/O cụ thể cho mỗi worker.                  | `worker_contracts.yaml` v2 (complete)             |
| **Person 5** | **Task 2E:** Test từng worker **độc lập** (không cần graph). Viết test script, kiểm tra input/output khớp contracts. Log kết quả test 3 queries cho mỗi worker. | Test script + test report (3 workers × 3 queries) |
| **Person 6** | **Task 2F:** Integrate workers vào `graph.py` (import + call từng worker trong node tương ứng). Test end-to-end pipeline với ≥3 queries từ Sprint 1.          | Updated `graph.py` + end-to-end test log          |

**Sprint 2 Definition of Done:**
- [ ] Mỗi worker test độc lập được, input/output khớp contracts
- [ ] Policy worker xử lý đúng ít nhất 1 exception case (Flash Sale hoặc digital product)
- [ ] Synthesis worker trả về answer có citation `[1]`, không hallucinate
- [ ] `python graph.py` chạy end-to-end với ≥3 queries

---

### **SPRINT 3 (2:00–3:00) — Thêm MCP (mcp_server.py)**

**Mục tiêu:** Implement mock MCP server, tích hợp vào policy_tool worker, ghi trace.

| Person       | Task                                                                                                                                                       | Output                                         |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Person 1** | **Task 3A:** Implement MCP tool `search_kb(query, top_k)` trong `mcp_server.py` — search ChromaDB, trả về chunks + sources theo format JSON chuẩn.        | `search_kb` tool trong `mcp_server.py`         |
| **Person 2** | **Task 3B:** Implement MCP tool `get_ticket_info(ticket_id)` trong `mcp_server.py` — mock data cho P1/P2/P3 tickets. Thêm 1 tool tùy chọn (e.g., `check_policy_version`). | 2+ tools trong `mcp_server.py`              |
| **Person 3** | **Task 3C:** Tích hợp MCP client vào `workers/policy_tool.py` — gọi `search_kb` qua MCP thay vì truy cập ChromaDB trực tiếp. Verify kết quả không đổi.    | Updated `policy_tool.py` (MCP-integrated)      |
| **Person 4** | **Task 3D:** Update trace fields — thêm `mcp_tool_called` và `mcp_result` vào `AgentState` + ghi vào log mỗi lần MCP được gọi.                            | Updated `AgentState` + trace fields            |
| **Person 5** | **Task 3E:** Test MCP integration end-to-end: gọi ít nhất 2 tools, verify trace ghi `mcp_tool_called` + `mcp_result`. Chạy ≥5 queries, kiểm tra output.   | MCP test report + trace evidence               |
| **Person 6** | **Task 3F:** Update `supervisor_node()` — log "dùng MCP" vs "không dùng MCP" vào `route_reason`. Cập nhật routing keywords nếu cần sau khi test Sprint 2. | Updated `supervisor_node()` + routing log      |

**Sprint 3 Definition of Done:**
- [ ] `mcp_server.py` có ít nhất 2 tools implement
- [ ] Policy worker gọi MCP client, không direct call ChromaDB
- [ ] Trace ghi `mcp_tool_called` và `mcp_result` cho ít nhất 1 tool call thực tế
- [ ] Supervisor ghi log "chọn MCP vs không MCP" vào `route_reason`

---

### **SPRINT 4 (3:00–4:00) — Trace & Eval & Docs**

**Mục tiêu:** Chạy eval với 15 test questions, hoàn thiện docs, viết báo cáo nhóm.

| Person       | Task                                                                                                                                                                     | Output                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| **Person 1** | **Task 4A:** Implement `eval_trace.py` — chạy pipeline với 15 test questions từ `data/test_questions.json`, lưu trace vào `artifacts/traces/`. Verify không crash.       | `eval_trace.py` + `artifacts/traces/` (15 files)   |
| **Person 2** | **Task 4B:** Implement `analyze_trace()` trong `eval_trace.py` — đọc traces, tính: abstain rate, avg confidence, avg latency_ms, worker call distribution.               | `analyze_trace()` + metrics summary                 |
| **Person 3** | **Task 4C:** Viết `docs/system_architecture.md` — mô tả vai trò từng worker, ranh giới supervisor/workers, sơ đồ pipeline (Mermaid hoặc ASCII), lý do chọn multi-agent. | `docs/system_architecture.md` (complete)            |
| **Person 4** | **Task 4D:** Viết `docs/routing_decisions.md` — ghi ≥3 quyết định routing thực tế từ trace (task đầu vào, worker chọn, route_reason, kết quả).                          | `docs/routing_decisions.md` (complete, from traces) |
| **Person 5** | **Task 4E:** Implement `compare_single_vs_multi()` + viết `docs/single_vs_multi_comparison.md` — so sánh ≥2 metrics (accuracy, latency, debuggability) với số liệu thực. | `single_vs_multi_comparison.md` + code              |
| **Person 6** | **Task 4F:** Viết `reports/group_report.md` — tổng hợp pipeline, tuning decisions, kết quả grading. Quản lý format `artifacts/grading_run.jsonl` cho grading questions.  | `group_report.md` + `grading_run.jsonl` template    |

**Sprint 4 Definition of Done:**
- [ ] `python eval_trace.py` chạy end-to-end 15 test questions không crash
- [ ] Trace files đủ fields bắt buộc (supervisor_route, route_reason, workers_called, v.v.)
- [ ] `docs/routing_decisions.md` có ≥3 quyết định routing thực tế
- [ ] `docs/single_vs_multi_comparison.md` có ≥2 metrics so sánh có số liệu
- [ ] `reports/group_report.md` hoàn chỉnh

**Individual Reports (Mỗi người viết sau 18:00):**
- Mỗi person viết `reports/individual/[tên].md` (500–800 từ)
- Content: Module phụ trách → 1 Quyết định kỹ thuật → 1 Lỗi đã sửa → Tự đánh giá → Nếu có 2h thêm

---

## ⏰ Timeline & Commits

| Sprint            | Person 1        | Person 2             | Person 3              | Person 4            | Person 5              | Person 6              | Sync Point                     |
| ----------------- | --------------- | -------------------- | --------------------- | ------------------- | --------------------- | --------------------- | ------------------------------ |
| **1 (0:00–1:00)** | AgentState      | supervisor_node()    | route_decision()      | Graph wiring        | Test queries + run    | contracts skeleton    | `graph.py` ready @ 1:00        |
| **2 (1:00–2:00)** | retrieval.py    | policy_tool.py       | synthesis.py          | contracts v2        | Worker tests          | Graph integration     | `workers/` ready @ 2:00        |
| **3 (2:00–3:00)** | search_kb tool  | get_ticket_info tool | MCP in policy_tool    | Trace fields        | MCP end-to-end test   | Supervisor MCP log    | `mcp_server.py` ready @ 3:00   |
| **4 (3:00–4:00)** | eval_trace.py   | analyze_trace()      | system_architecture   | routing_decisions   | single_vs_multi       | group_report + jsonl  | All docs ready @ 4:00          |

---

## 🔄 Commit Strategy (Mỗi người commit ít nhất 1 lần/sprint)

**Sprint 1 @ 1:00:**
```bash
git commit -m "Sprint 1: graph.py — AgentState, supervisor_node, routing, graph wiring
- Person 1: AgentState schema
- Person 2: supervisor_node()
- Person 3: route_decision()
- Person 4: graph wiring & edges
- Person 5: test queries & initial run
- Person 6: contracts/worker_contracts.yaml skeleton"
```

**Sprint 2 @ 2:00:**
```bash
git commit -m "Sprint 2: workers/ — retrieval, policy_tool, synthesis + contracts
- Person 1: workers/retrieval.py
- Person 2: workers/policy_tool.py (Flash Sale exception)
- Person 3: workers/synthesis.py (citation + confidence)
- Person 4: contracts/worker_contracts.yaml v2
- Person 5: worker test scripts & report
- Person 6: graph.py end-to-end integration"
```

**Sprint 3 @ 3:00:**
```bash
git commit -m "Sprint 3: mcp_server.py — search_kb, get_ticket_info, MCP integration
- Person 1: mcp_server.py search_kb tool
- Person 2: mcp_server.py get_ticket_info + extra tool
- Person 3: policy_tool.py MCP client integration
- Person 4: AgentState mcp_tool_called & mcp_result fields
- Person 5: MCP end-to-end test report
- Person 6: supervisor_node MCP routing log"
```

**Sprint 4 @ 4:00:**
```bash
git commit -m "Sprint 4: eval, docs — traces, metrics, architecture, routing decisions
- Person 1: eval_trace.py + artifacts/traces/
- Person 2: analyze_trace() metrics
- Person 3: docs/system_architecture.md
- Person 4: docs/routing_decisions.md
- Person 5: docs/single_vs_multi_comparison.md
- Person 6: reports/group_report.md + artifacts/grading_run.jsonl template"
```

**After 18:00 (Individual Reports):**
```bash
git commit -m "Individual Reports — All 6 members
- reports/individual/chu-thi-ngoc-huyen.md
- reports/individual/chu-ba-tuan-anh.md
- reports/individual/nguyen-mai-phuong.md
- reports/individual/hua-quang-linh.md
- reports/individual/nguyen-thi-tuyet.md
- reports/individual/nguyen-van-linh.md"
```

---

## ✅ Mỗi người có trách nhiệm

**Mọi sprint:**
- [ ] Hiểu code của người khác (code review nhẹ)
- [ ] Communicate khi có blocker (Slack / Discord)
- [ ] Commit ít nhất 1 lần/sprint với message rõ ràng
- [ ] Viết 1 individual report (500–800 từ) sau 18:00

**Khi xong task sớm:**
- Hỗ trợ người khác hoặc review code
- Không chờ passive, tìm việc thêm

---

## 🔗 File Nộp Bài (Organized by Sprint)

```
lab/
├── [SPRINT 1 Output]
│   ├── graph.py                              (Person 1–5 contribute)
│   └── contracts/worker_contracts.yaml       (Person 6 — skeleton)
│
├── [SPRINT 2 Output]
│   ├── workers/
│   │   ├── retrieval.py                      (Person 1)
│   │   ├── policy_tool.py                    (Person 2)
│   │   └── synthesis.py                      (Person 3)
│   └── contracts/worker_contracts.yaml       (Person 4 — complete)
│
├── [SPRINT 3 Output]
│   ├── mcp_server.py                         (Person 1 + 2)
│   └── workers/policy_tool.py (updated)      (Person 3)
│
├── [SPRINT 4 Output — Eval & Docs]
│   ├── eval_trace.py                         (Person 1 + 2)
│   ├── artifacts/
│   │   ├── grading_run.jsonl                 (Person 6 + group @ 17:00–18:00)
│   │   └── traces/                           (Person 1)
│   ├── docs/
│   │   ├── system_architecture.md            (Person 3)
│   │   ├── routing_decisions.md              (Person 4)
│   │   └── single_vs_multi_comparison.md     (Person 5)
│   └── reports/
│       ├── group_report.md                   (Person 6)
│       └── individual/
│           ├── chu-thi-ngoc-huyen.md         (After 18:00)
│           ├── chu-ba-tuan-anh.md
│           ├── nguyen-mai-phuong.md
│           ├── hua-quang-linh.md
│           ├── nguyen-thi-tuyet.md
│           └── nguyen-van-linh.md
```

---

## ⚡ Tips Để Collaboration Suôn Sẻ

1. **Setup Google Doc** để track notes real-time (routing keywords, contract fields, MCP tool format)

2. **30' check-in:**
   - 0:30 — Mọi người confirm `AgentState` fields (Person 1 share schema)
   - 1:30 — Merge workers vào graph, test end-to-end
   - 2:30 — MCP integration done, trace fields confirmed
   - 3:30 — Merge docs, final grading run check

3. **Parallel work:**
   - Sprint 1: Person 1 + 6 share schema sớm (3 người còn lại cần AgentState)
   - Sprint 2: Person 4 update contracts song song khi workers code xong
   - Sprint 3: Person 1 + 2 code MCP tools đồng thời, Person 3 chờ API ready
   - Sprint 4: Person 1 chạy traces sớm để Person 4 có data viết routing_decisions

4. **Debug Tree:**
   - Routing sai? → Xem `route_reason` trong trace
   - Worker sai? → Test worker độc lập
   - MCP sai? → Xem `mcp_tool_called` và `mcp_result`
   - Synthesis sai? → Kiểm tra `retrieved_sources` + prompt

5. **Lưu ý quan trọng:**
   - `AgentState` schema **lock sau Sprint 1** (không đổi tên fields)
   - MCP tools **chỉ mock** (full credit) — không cần HTTP server thật (bonus +2)
   - Grading questions public lúc **17:00** → cả nhóm tập trung chạy pipeline

---

## ✅ Checklist Trước Nộp (30' cuối)

**Code (Deadline 18:00 — CHẶT):**
- [ ] `python graph.py` — chạy không lỗi, route ≥2 loại query
- [ ] `python eval_trace.py` — chạy 15 test questions không crash
- [ ] `artifacts/grading_run.jsonl` — đủ 10 entries, đúng format
- [ ] Commit tất cả `.py`, `worker_contracts.yaml`, `grading_run.jsonl`

**Docs (Deadline 18:00 — CHẶT):**
- [ ] `docs/system_architecture.md` — có sơ đồ + mô tả vai trò + lý do multi-agent
- [ ] `docs/routing_decisions.md` — ≥3 quyết định routing thực tế từ trace
- [ ] `docs/single_vs_multi_comparison.md` — ≥2 metrics có số liệu thực
- [ ] Commit docs

**Reports (Deadline LINH HOẠT — sau 18:00 OK):**
- [ ] `reports/group_report.md` — 500–800 từ
- [ ] `reports/individual/[6 tên].md` — mỗi file 500–800 từ
- [ ] Nộp reports trong 1 giờ sau deadline code

---

**Good luck! 🚀**

Ngày chuẩn bị: 2026-04-13  
Ngày nộp: 2026-04-14 (18:00 code + log, sau 18:00 reports)
