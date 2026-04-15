# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Mai Phương
**Vai trò trong nhóm:** Policy Worker (P3)
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**

- File chính: `workers/policy_tool.py`
- Functions tôi implement: `_analyze_policy_with_llm()`, `_analyze_policy_rule_based()`, `analyze_policy()`, `_call_mcp_tool()`, `run()`

Tôi đảm nhiệm vai trò **Policy Worker** — Sprint 2 của nhóm. Nhiệm vụ cụ thể là: nhận `AgentState` từ graph, đọc `retrieved_chunks` và `task`, gọi Claude claude-opus-4-6 với adaptive thinking để phân tích xem chính sách hoàn tiền có áp dụng không và có exception nào vi phạm không. Kết quả ghi vào `policy_result` với schema chuẩn theo `worker_contracts.yaml`. Worker cũng gọi MCP tools (`search_kb`, `get_ticket_info`) khi `needs_tool=True`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`policy_tool_worker` nằm giữa P2 (retrieval — cung cấp `retrieved_chunks`) và P4 (synthesis — đọc `policy_result` để tổng hợp câu trả lời cuối). Sprint 3, P5 (MCP Owner) sẽ thay thế `_call_mcp_tool()` stub của tôi bằng real MCP client — interface đã được giữ ổn định để không phá vỡ code của tôi.

**Bằng chứng:** `workers/policy_tool.py` — toàn bộ nội dung do tôi implement. Trace `run_20260414_161316.json` (Flash Sale) và `run_20260414_161321.json` (cross-doc multi-hop) cho thấy `policy_tool_worker` được gọi và ghi đúng `policy_result`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Dùng Claude claude-opus-4-6 với `thinking={"type": "adaptive"}` và prompt caching trên system prompt ổn định, kết hợp fallback sang rule-based nếu LLM lỗi.

Các lựa chọn thay thế:

1. Rule-based hoàn toàn — keyword matching đơn giản, không cần LLM.
2. Gọi LLM nhỏ hơn (Haiku) không có thinking, không có caching.
3. LLM lớn với full thinking bắt buộc, không fallback.

**Lý do tôi chọn LLM + adaptive thinking + caching + fallback:**

Rule-based đơn giản bỏ sót các trường hợp ngôn ngữ tự nhiên không khớp từ khoá chính xác (ví dụ khách nói "trả lại" thay vì "hoàn tiền"). Adaptive thinking cho phép Claude tự quyết định khi nào cần lý luận sâu — tiết kiệm token so với bắt buộc extended thinking. Quan trọng hơn, system prompt của tôi (`_POLICY_SYSTEM_PROMPT`, ~380 tokens) hoàn toàn ổn định qua mọi request — gắn `cache_control: ephemeral` tiết kiệm token trên mọi lần gọi thứ 2 trở đi. Fallback rule-based đảm bảo worker không bao giờ crash ngay cả khi API key không có hoặc LLM timeout.

**Trade-off đã chấp nhận:** `claude-opus-4-6` chậm hơn Haiku ~2–3x. Với production cần optimize latency thì nên thử Haiku trước, chỉ escalate Opus khi Haiku sai.

**Bằng chứng từ trace `run_20260414_161316`:**

```
[policy_tool_worker] policy_applies=False, exceptions=1
policy_result.exceptions_found[0]:
  type: flash_sale_exception
  rule: Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).
  source: policy_refund_v4.txt
explanation: Analyzed via rule-based policy check (fallback).
```

*(LLM fallback về rule-based do ChromaDB chưa được index — rule-based phát hiện đúng exception Flash Sale)*

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `AttributeError` hoặc `json.JSONDecodeError` khi parse response từ Claude với `thinking={"type": "adaptive"}`.

**Symptom:**

Khi test `_analyze_policy_with_llm()` lần đầu, code gốc dùng `response.content[0].text` để lấy JSON. Nhưng với adaptive thinking bật, Claude trả về list content có thể là:

```python
[
    ContentBlock(type="thinking", thinking="..."),  # index 0
    ContentBlock(type="text", text='{"policy_applies": ...}')  # index 1
]
```

Kết quả: `response.content[0]` là thinking block — gọi `.text` trả về nội dung suy nghĩ nội bộ của model, không phải JSON. `json.loads()` lập tức crash với `JSONDecodeError`.

**Root cause:**

`thinking={"type": "adaptive"}` cho phép model thêm thinking blocks vào đầu `content` list. Code không xử lý trường hợp thinking block xuất hiện trước text block.

**Cách sửa:**

Thay `response.content[0].text` bằng generator expression lọc đúng type:

```python
# TRƯỚC (lỗi) — workers/policy_tool.py
text_content = response.content[0].text

# SAU (đã fix)
text_content = next(
    (b.text for b in response.content if b.type == "text"),
    None,
)
if not text_content:
    raise ValueError("LLM returned no text content")
```

Ngoài ra phát hiện thêm: Claude đôi khi wrap JSON trong markdown fence (` ```json ... ``` `). Thêm cleanup logic (lines 141–145) để strip fence trước khi `json.loads()`.

Sau khi sửa, cả hai trường hợp (có / không có thinking block, có / không có markdown fence) đều parse thành công.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế `analyze_policy()` với two-layer architecture: LLM là primary path, rule-based là safety net. Nhờ vậy worker chạy được hoàn toàn ngay cả khi không có API key — quan trọng trong môi trường lab. Exception schema cũng khớp chính xác với `worker_contracts.yaml` (các field `type`, `rule`, `source` trong `exceptions_found`), giúp P4 (synthesis) đọc được ngay mà không cần debug interface.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Chưa viết unit test riêng cho `_analyze_policy_with_llm()` với mock Anthropic client — hiện chỉ có standalone test `__main__` chạy real API. Nếu API thay đổi response format thì không phát hiện được ngay.

**Nhóm phụ thuộc vào tôi ở đâu?**

P4 (synthesis) đọc `policy_result["policy_applies"]` và `policy_result["exceptions_found"]` để quyết định tone câu trả lời. Nếu `policy_tool_worker` không ghi đúng schema, synthesis sẽ không có đủ thông tin để abstain hay warn user.

**Phần tôi phụ thuộc vào thành viên khác:**

Phụ thuộc P5 (Sprint 3): khi `_call_mcp_tool()` được thay bằng real MCP client, `search_kb` mới trả về chunks thật → LLM path của tôi mới được kích hoạt thay vì luôn fallback rule-based.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ xử lý **temporal scoping** cho câu hỏi cross-doc quan trọng nhất của lab — `gq09`: "P1 lúc 2am + cấp quyền Level 2 cho contractor". Hiện tại `policy_tool_worker` chỉ check policy hoàn tiền, nhưng câu `gq09` cần kết hợp access control policy (Level 2 contractor, ngoài giờ hành chính) lẫn SLA escalation policy. Tôi sẽ tách `_POLICY_SYSTEM_PROMPT` thành 2 prompt riêng — một cho refund, một cho access control — và route đúng prompt theo loại task, thay vì dùng chung 1 prompt cho mọi trường hợp. Trace `run_20260414_161321` cho thấy hiện tại câu Level 3 bị trả về `confidence: 0.1` vì policy model không có context access control — đây là gap cần fix nhất.
