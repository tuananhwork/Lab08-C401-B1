# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Thị Tuyết    
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`
- File tích hợp: `workers/policy_tool.py`, `graph.py`
- Hạng mục tôi thực hiện: mock MCP tools, tích hợp MCP vào policy worker, bổ sung trace fields MCP

Đảm nhiệm vai trò **MCP Owner** (Sprint 3). Trọng tâm công việc: xây dựng lớp năng lực tool theo kiểu MCP để worker có thể gọi external capability một cách có cấu trúc thay vì hard-code logic trong từng module, phụ trách hoàn thiện `mcp_server.py` theo hướng mock server in-process, cung cấp ít nhất hai công cụ bắt buộc là `search_kb(query, top_k)` và `get_ticket_info(ticket_id)`, đồng thời giữ cơ chế `list_tools()` và `dispatch_tool()` để mô phỏng chuẩn `tools/list` và `tools/call`, tích hợp lại vào `workers/policy_tool.py` để policy worker gọi MCP client và ghi trace đầy đủ cho từng lần gọi tool.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Đây là cầu nối giữa routing của supervisor (Sprint 1) và domain reasoning của policy/synthesis worker (Sprint 2). Supervisor quyết định `needs_tool=True`, policy worker dùng tín hiệu này để gọi MCP tools, sau đó kết quả được đẩy vào state để synthesis worker dùng tiếp.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Chọn mô hình **Mock MCP Server in-process (Standard level)** thay vì dựng HTTP MCP server ngay từ đầu.

**Các lựa chọn thay thế:**
1. Dùng class/function mock ngay trong Python process (dispatch trực tiếp).
2. Dựng HTTP server (FastAPI) để gọi qua network.
3. Dùng thư viện MCP đầy đủ theo advanced mode.

**Lý do tôi chọn hướng in-process:**

Mục tiêu của Sprint 3 là chứng minh được contract tool-call và tích hợp vào pipeline multi-agent, không phải tối ưu deployment. Với thời gian lab 60 phút/sprint, in-process mock đảm bảo nhóm đạt Definition of Done nhanh và ổn định hơn: giảm lỗi môi trường mạng, giảm chi phí debug request/response serialization, và tập trung vào phần quan trọng nhất là **worker gọi MCP thay vì gọi trực tiếp database**.

Ngoài ra, tôi thiết kế theo hướng tương thích nâng cấp: giữ lớp `dispatch_tool()` như điểm vào duy nhất. Nhờ vậy, sau này có thể thay implementation bên dưới từ in-process sang HTTP/MCP library mà không phải sửa nhiều ở policy worker. Đây là cách tách interface và implementation để giữ code dễ bảo trì.

**Trade-off đã chấp nhận:** Mock in-process không kiểm tra được lỗi transport, auth, timeout mạng như server thật; nhưng phù hợp với mục tiêu lab và vẫn thể hiện rõ kiến trúc MCP.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Trace MCP chưa có đúng field theo yêu cầu chấm điểm (`mcp_tool_called`, `mcp_result`) dù đã có `mcp_tools_used`.

**Symptom:**

Pipeline chạy được, policy worker có gọi MCP tool, nhưng khi đọc state/trace thì dữ liệu MCP chỉ nằm trong danh sách `mcp_tools_used` dạng raw log. Theo rubric Sprint 3, cần thấy rõ từng lần gọi với key cụ thể `mcp_tool_called` và `mcp_result`, nếu không dễ bị trừ điểm ở phần observability.

**Root cause:**

Code ban đầu mới append object call vào `mcp_tools_used`, chưa có lớp trace chuẩn hóa theo field-name mà đề bài yêu cầu. Tức là có dữ liệu nhưng chưa đúng “hình dạng dữ liệu” cho quá trình đánh giá.

**Cách sửa:**

Tôi bổ sung hàm `_record_mcp_trace(state, mcp_call)` trong `workers/policy_tool.py` để chuẩn hóa trace cho mỗi lần call:
- `mcp_tool_called`: tên tool
- `mcp_result`: output tool
- `error`, `timestamp`

Sau đó gọi hàm này ngay sau mỗi `search_kb` và `get_ticket_info`. Đồng thời tôi cập nhật `graph.py` để `route_reason` luôn gắn thêm quyết định MCP (`mcp_decision=use_mcp_tools` hoặc `no_mcp_needed`) nhằm đáp ứng yêu cầu supervisor log rõ “chọn MCP vs không chọn MCP”.

Kết quả sau sửa: trace có đủ trường bắt buộc, dễ debug lỗi routing/tool-call hơn.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở việc chuẩn hóa ranh giới giữa worker và tool layer: worker không cần biết chi tiết backend, chỉ cần gọi `_call_mcp_tool()` với input đúng schema. Điều này giúp giảm coupling và khiến pipeline dễ thay đổi trong các sprint sau.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Phần test tự động cho MCP tôi mới dừng ở smoke test và kiểm tra trace key; chưa có bộ unit test formal cho từng tool/error case.

**Nhóm phụ thuộc vào tôi ở đâu?**

Nếu MCP integration không ổn, policy worker sẽ quay lại gọi trực tiếp retrieval hoặc thiếu dữ liệu ticket, làm mất ý nghĩa Sprint 3.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi phụ thuộc vào retrieval/policy/synthesis contracts ổn định để đảm bảo output MCP đưa vào state đúng format downstream cần dùng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nâng từ mock in-process lên HTTP MCP server tối giản (FastAPI) để mô phỏng gần hơn môi trường production: thêm timeout, retry, và error mapping chuẩn. Đồng thời bổ sung test cases cho `dispatch_tool()` (tool không tồn tại, input sai schema, tool runtime error) và benchmark latency từng tool call để trace có thêm signal về hiệu năng, không chỉ signal logic.
