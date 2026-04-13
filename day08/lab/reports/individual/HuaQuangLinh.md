# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hứa Quang Linh  
**Vai trò trong nhóm:** Person 4 — Metadata Schema, System Prompt, A/B Delta Analysis  
**Ngày nộp:** 13/4/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi chịu trách nhiệm 4 task trải dài qua cả 4 sprint, tập trung vào phần **schema dữ liệu** và **prompt engineering**.

- **Sprint 1 (Task 1D):** Thiết kế metadata schema cho chunks — bao gồm các field `source`, `section`, `effective_date`, và thêm field `doc_type` (phân loại tài liệu: policy, sop, faq, guideline) để hỗ trợ filtering sau.
- **Sprint 2 (Task 2D):** Viết `SYSTEM_PROMPT_V1` — prompt tiếng Anh yêu cầu LLM trả lời từ context, gắn citation `[1]`, và abstain bằng câu chuẩn khi không đủ thông tin.
- **Sprint 3 (Task 3D):** Nâng cấp thành `SYSTEM_PROMPT_V2` — chuyển sang tiếng Việt, thêm 3 few-shot examples cho 3 tình huống: có đủ thông tin, abstain hoàn toàn, và partial answer. Prompt v2 enforce citation sau mọi nhận định.
- **Sprint 4 (Task 4D):** Tạo `logs/grading_run.json` — ghi kết quả A/B cho 10 câu hỏi (baseline dense vs. variant hybrid+rerank) cùng delta analysis đầy đủ.

Công việc của tôi kết nối với retrieval (Person 1, 2, 3) ở đầu vào của generation, và với eval (Person 2, 3) ở đầu ra khi chấm điểm faithfulness và citation.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Grounded prompt vs. generic prompt:**

Trước khi làm lab, tôi nghĩ system prompt chỉ là "hướng dẫn chung" cho LLM. Sau khi viết cả v1 và v2, tôi thấy rõ sự khác biệt: một prompt không có few-shot ví dụ cụ thể sẽ khiến LLM tự "sáng tác" format citation theo cách riêng, không nhất quán. Khi thêm 3 ví dụ (câu trả lời mẫu kèm `[1][2]` đúng chỗ, câu abstain chuẩn, câu partial answer), LLM bắt đầu follow đúng pattern.

**Abstain là kỹ năng, không phải fallback:**

Câu abstain tưởng đơn giản nhưng thực ra rất khó cân bằng. Nếu prompt quá "sợ sai", LLM sẽ abstain cả khi có đủ thông tin. Nếu prompt không rõ điều kiện abstain, LLM sẽ hallucinate. Few-shot example với trường hợp cụ thể ("ERR-403-AUTH không có trong tài liệu → abstain") giúp model phân biệt được hai trường hợp này tốt hơn nhiều so với instruction thuần túy.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Kết quả A/B hoàn toàn nằm ngoài kỳ vọng: **cả 10 câu hỏi của cả hai config đều trả về ABSTAIN với 0 chunks retrieved**.

Ban đầu tôi nghĩ lỗi nằm ở prompt — có thể prompt v1 quá "trigger abstain". Nhưng sau khi debug, root cause nằm ở tầng dưới: hàm `get_embedding()` raise `NotImplementedError` trong quá trình eval run, khiến `retrieve_dense()` không lấy được chunk nào. LLM nhận context rỗng → tự động abstain — không phải vì nó "hiểu" không đủ thông tin, mà vì không có gì để trả lời.

Điều này tạo ra một false positive nguy hiểm: câu q09 (câu mà expected_abstain=true) bị đánh dấu "đúng" trong scorecard, nhưng thực ra đúng vì lý do sai — pipeline fail chứ không phải model reasoning đúng.

Bài học: khi toàn bộ câu trả lời đều giống nhau (100% ABSTAIN), đó là dấu hiệu của infrastructure failure, không phải prompt tốt.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*

**Tại sao chọn câu này:** Đây là câu "hard" được chú thích trong grading_run.json vì là alias query — người dùng hỏi tên cũ "Approval Matrix" trong khi tài liệu nội bộ đã đổi tên thành "Access Control SOP".

**Baseline:** Faithfulness=1, Relevance=1, Recall=0, Completeness=2/5. Trả về ABSTAIN vì 0 chunks retrieved. Ngay cả nếu retrieval hoạt động, dense embedding rất khó map "Approval Matrix" → "Access Control SOP" vì vector similarity của hai cụm này thấp — chúng khác tên hoàn toàn dù chỉ một tài liệu.

**Lỗi nằm ở đâu:** Chủ yếu ở retrieval. Dense embedding không xử lý được alias/tên cũ. Indexing không có vấn đề (tài liệu đã được chunk đúng). Generation không được gọi đến.

**Variant có cải thiện không:** Về lý thuyết, hybrid + query expansion của Task 3A và 3C được thiết kế chính xác cho trường hợp này — BM25 bắt exact term, query expansion map "approval matrix" → ["access control sop", "ma trận phê duyệt"]. Nhưng do retrieval layer fail, variant không có cơ hội thể hiện ưu điểm. Delta = 0 cho q07, không phải vì variant không tốt hơn, mà vì cả hai đều bị block bởi cùng một lỗi infrastructure.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Có hai việc cụ thể:

1. **Fix `get_embedding()` và chạy lại eval:** Kết quả hiện tại hoàn toàn không có giá trị so sánh. Sau khi fix, tôi muốn xem delta thực sự giữa prompt v1 và v2 trên metric Citation Accuracy — tuning-log dự báo +15%, nhưng chưa verify được.

2. **Thêm retrieval health check vào `eval.py`:** Kiểm tra trước khi chạy rằng `chunks_retrieved > 0` cho ít nhất 1 câu. Nếu 100% câu trả về 0 chunks, dừng và báo lỗi thay vì tiếp tục chấm điểm — tránh false positive như q09 trong lần chạy này.
