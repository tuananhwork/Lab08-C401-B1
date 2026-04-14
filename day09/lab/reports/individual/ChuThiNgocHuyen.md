# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Chu Thị Ngọc Huyền    
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py`
- Functions tôi implement: `supervisor_node()`, `route_decision()`, `build_graph()`, các wrapper node `retrieval_worker_node()` / `policy_tool_worker_node()` / `synthesis_worker_node()`, `run_graph()`, `save_trace()`

Tôi đảm nhiệm vai trò **Supervisor Owner** — sprint 1 của nhóm. Nhiệm vụ cụ thể là thiết kế `AgentState` (shared state đi xuyên toàn graph), implement logic routing trong `supervisor_node()` bằng bảng từ khóa phân tầng, và kết nối toàn bộ graph từ đầu vào đến đầu ra theo luồng `supervisor → route → [retrieval | policy_tool | human_review] → synthesis → END`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`graph.py` là điểm tích hợp trung tâm — các worker của Person 2 (retrieval, policy_tool, synthesis) được gọi qua `try/except` import trong graph. Nếu worker chưa implement thì graph tự fallback sang placeholder, đảm bảo cả nhóm có thể test độc lập song song mà không block nhau. Mọi field trong `AgentState` (như `retrieved_chunks`, `policy_result`, `workers_called`, `route_reason`) đều được tôi định nghĩa trước để Person 2, 3, 4 có contract rõ khi implement worker của mình.

**Bằng chứng:** File `graph.py` — toàn bộ nội dung do tôi implement. Trace files `artifacts/traces/run_20260414_16*.json` được sinh ra từ `python graph.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Dùng keyword-based routing phân tầng (3 bảng từ khóa: `_POLICY_KEYWORDS`, `_SLA_TICKET_KEYWORDS`, `_HIGH_RISK_KEYWORDS`) thay vì gọi LLM để classify intent trong `supervisor_node()`.

**Các lựa chọn thay thế:**
1. Gọi LLM (GPT-4o-mini) để phân loại câu hỏi vào route.
2. Regex matching thuần tuý, không có tầng priority.
3. Keyword matching đơn giản (1 bảng duy nhất), không phân biệt cross-doc.

**Lý do tôi chọn keyword phân tầng:**

LLM classification thêm ~800–1200ms latency và tốn thêm token cho mỗi request — không hợp lý khi supervisor chỉ cần phân loại vào 3 bucket cố định. Keyword matching đủ chính xác cho bộ 5 tài liệu nội bộ có domain hẹp. Điều quan trọng hơn là tôi thiết kế **5 bước ưu tiên có thứ tự**: phát hiện risk → policy → SLA → cross-doc override → human_review. Điều này cho phép xử lý đúng câu hỏi multi-hop như "P1 khẩn cấp + cần cấp quyền Level 3" — vừa chứa SLA keyword lẫn policy keyword — được route vào `policy_tool_worker` với label `cross-doc multi-hop` thay vì chỉ route vào một trong hai.

**Trade-off đã chấp nhận:** Nếu người dùng dùng từ đồng nghĩa không có trong bảng keyword (ví dụ "trả lại hàng" thay vì "hoàn tiền"), routing sẽ sai. Với bộ 5 tài liệu cố định thì đây là trade-off chấp nhận được.

**Bằng chứng từ trace:**

```
# Trace run_20260414_161311 — câu hỏi SLA
route: retrieval_worker
reason: task contains SLA/ticket keywords: ['p1', 'ticket', 'sla']
workers: ['retrieval_worker', 'synthesis_worker']
latency: 5265ms

# Trace run_20260414_161316 — câu hỏi Flash Sale
route: policy_tool_worker
reason: task contains policy/access keywords: ['hoàn tiền', 'flash sale']
workers: ['retrieval_worker', 'policy_tool_worker', 'synthesis_worker']
latency: 4429ms

# Trace run_20260414_161321 — cross-doc multi-hop
route: policy_tool_worker
reason: cross-doc multi-hop: SLA keywords ['p1'] + policy keywords ['cấp quyền', 'level 3']
        → policy_tool_worker | risk_high=True
workers: ['retrieval_worker', 'policy_tool_worker', 'synthesis_worker']
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Conflict code kép trong section "Import Workers" sau khi pull task của Person 2 và Person 3 về — pipeline bị lỗi `SyntaxError` ngay khi import.

**Symptom:**

Sau khi pull code, chạy `python graph.py` lập tức báo `SyntaxError: invalid syntax` tại dòng `<<<<<<< Updated upstream`. Pipeline không khởi động được, toàn bộ nhóm bị block vì `graph.py` là file tích hợp trung tâm.

**Root cause:**

Có 2 nguồn conflict chồng nhau trong cùng section 5:

1. Upstream (người khác push) vẫn giữ block comment `# TODO Sprint 2: Uncomment sau khi implement workers` — chưa wire worker thật.
2. Stashed changes (của tôi) đã implement `try/except` import với flag `_HAS_RETRIEVAL`, `_HAS_POLICY`, `_HAS_SYNTHESIS`.

Ngoài ra, từ lần conflict trước đó, `retrieval_worker_node()` còn sót code thừa: gọi `retrieval_run(state)` unconditional ở đầu hàm rồi lại gọi `_retrieval_run(state)` bên trong `if _HAS_RETRIEVAL` — khiến retrieval chạy 2 lần và `workers_called` bị append trùng.

**Cách sửa:**

Xoá toàn bộ 4 conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`), giữ phiên bản `try/except` phân tách rõ "có worker thật" vs "chạy placeholder". Đồng thời xoá unconditional import `from workers.retrieval import run as retrieval_run` đã được thêm nhầm.

**Bằng chứng trước/sau:**

```
# TRƯỚC (lỗi) — graph.py dòng 236
<<<<<<< Updated upstream
# TODO Sprint 2: Uncomment sau khi implement workers
# from workers.retrieval import run as retrieval_run
=======
try:
    from workers.retrieval import run as _retrieval_run
    _HAS_RETRIEVAL = True
...
>>>>>>> Stashed changes

# SAU (đã fix) — graph.py
try:
    from workers.retrieval import run as _retrieval_run
    _HAS_RETRIEVAL = True
except Exception:
    _HAS_RETRIEVAL = False
```

Sau khi sửa, `python graph.py` chạy thành công, `workers_called` đúng thứ tự, không có worker nào bị gọi 2 lần.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế `AgentState` và interface giữa supervisor và workers. Nhờ định nghĩa rõ từng field trong `AgentState` ngay từ đầu (bao gồm `route_reason`, `workers_called`, `worker_io_logs`, `mcp_tools_used`), các thành viên Person 2, 3, 4 biết chính xác họ cần đọc field nào và ghi vào field nào — không cần họp thêm để align interface. Đây là điều tiết kiệm nhiều thời gian nhất cho nhóm.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Quản lý merge/rebase kém — để xảy ra conflict đến 2 lần trong cùng 1 file do không thống nhất workflow git với nhóm từ đầu (nên dùng feature branch thay vì cùng commit thẳng vào `main`).

**Nhóm phụ thuộc vào tôi ở đâu?**

`graph.py` là điểm tích hợp duy nhất. Nếu tôi chưa xong `AgentState` và `run_graph()`, Person 4 (eval_trace.py) không thể import `run_graph` để chạy 15 test questions, và Person 6 không có trace để phân tích.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi cần Person 2 finalize `workers/retrieval.py` để ChromaDB trả về chunks thật thay vì placeholder — khi có chunks thật thì `confidence` mới > 0.5 và `final_answer` mới có citation `[1]` thực sự.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm **confidence-based re-routing** vào supervisor: nếu synthesis worker trả về `confidence < 0.4`, supervisor tự động route lại sang `human_review` thay vì trả answer thấp tin cậy ra ngoài. Bằng chứng từ trace: câu `run_20260414_161311` (SLA P1) và `run_20260414_161321` (Level 3 cross-doc) đều có `confidence: 0.1` vì ChromaDB chưa được index đầy đủ — đây là điểm mà hệ thống nên tự nhận biết "không đủ tự tin" và escalate thay vì trả câu "Không đủ thông tin" một cách lặng lẽ.
