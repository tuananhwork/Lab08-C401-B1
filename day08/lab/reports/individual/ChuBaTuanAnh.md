# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Chu Bá Tuấn Anh
**Vai trò trong nhóm:** Preprocessing Owner / Context Formatter Owner / Eval Owner
**Ngày nộp:** 2026-04-13
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab ngày 08, tôi chịu trách nhiệm implement 3 tasks chính xuyên suốt pipeline RAG:

**Sprint 1 - Task 1B (Preprocessing + Tokenizer):** Tôi implement hàm `preprocess_document()` trong `index.py`, bao gồm extract metadata từ header (Source, Department, Effective Date, Access), làm sạch văn bản, normalize khoảng trắng và ký tự đặc biệt, cùng với hàm `tokenize_text()` để tách text tiếng Việt thành tokens. Hàm này là nền tảng cho toàn bộ pipeline indexing.

**Sprint 2 - Task 2B (Context Formatter):** Tôi phát triển `format_context()` trong `rag_answer.py`, format các retrieved chunks thành readable context string với citation markers `[1]`, `[2]`, hiển thị metadata (source, section, similarity score). Function này giúp LLM dễ dàng trích dẫn nguồn khi trả lời.

**Sprint 4 - Task 4B (Baseline Evaluation):** Tôi implement 3 scoring functions trong `eval.py`: `score_faithfulness()`, `score_answer_relevance()`, và `score_completeness()` để chấm điểm tự động baseline pipeline. Tôi cũng cấu hình để chạy evaluation trên 10 test questions và generate `results/scorecard_baseline.md`.

Tất cả công việc của tôi kết nối chặt chẽ: preprocessing → chunking → retrieval → context formatting → evaluation, tạo thành pipeline hoàn chỉnh.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi thực sự hiểu rõ hơn về **tầm quan trọng của data preprocessing trong RAG pipeline**. Trước đây tôi nghĩ embedding model và retrieval algorithm là quan trọng nhất, nhưng thực tế preprocessing quyết định chất lượng đầu vào cho toàn bộ hệ thống.

Khi implement `preprocess_document()`, tôi nhận ra việc extract metadata chính xác (source, section, effective_date) không chỉ giúp organize data mà còn enabling advanced retrieval strategies sau này như filter theo department hay time range. Việc normalize text (xóa ký tự thừa, chuẩn hóa khoảng trắng) cũng ảnh hưởng trực tiếp đến chunking quality và最终 embedding accuracy.

Ngoài ra, qua việc implement `format_context()`, tôi hiểu sâu hơn về **grounded prompting** - cách format context để LLM có thể trích dẫn nguồn chính xác, giảm hallucination và tăng trustworthiness của câu trả lời.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là **độ phức tạp của tiếng Việt trong tokenization**. Tôi ban đầu nghĩ chỉ cần split theo whitespace là đủ, nhưng thực tế tiếng Việt có nhiều từ ghép, dấu câu đặc biệt, và cấu trúc ngữ pháp phức tạp. Hàm `tokenize_text()` cần xử lý carefully để không làm mất ý nghĩa.

Khi implement scoring functions cho Task 4B, tôi gặp khó khăn trong việc **đánh giá faithfulness tự động**. Ban đầu tôi định dùng LLM-as-Judge, nhưng approach này tốn API calls và không ổn định. Tôi chuyển sang heuristic-based scoring (keyword overlap), hoạt động khá tốt nhưng vẫn có false positives khi context chứa nhiều từ chung chung.

Một difficulty khác là debugging retrieval quality - nhiều khi answer sai không phải do LLM mà do retrieved chunks không chứa thông tin cần thiết, khiến việc root cause analysis phức tạp hơn dự kiến.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q02 - "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"

**Phân tích:**

Baseline pipeline trả lời câu hỏi này khá tốt. Retrieve_dense() tìm thấy chunk chứa "7 ngày làm việc" từ `policy_refund_v4.txt`, và format_context() present information rõ ràng với citation marker.

Tuy nhiên, có một số điểm thú vị:

1. **Retrieval quality:** Query này có expected source là `policy/refund-v4.pdf` nhưng actual file là `policy_refund_v4.txt`. Sự khác biệt này khiến context_recall scoring cần dùng partial matching thay vì exact match.

2. **Faithfulness score cao** (ước lượng 4-5/5) vì answer trực tiếp rút từ context, không thêm thông tin ngoài.

3. **Completeness có thể bị trừ** nếu expected answer yêu cầu chi tiết về điều kiện kèm theo (sản phẩm lỗi, chưa sử dụng) mà model bỏ sót.

4. **Lỗi tiềm ẩn:** Nếu chunking cắt không đúng ranh giới điều khoản, model có thể miss important conditions.

Variant (nếu có hybrid retrieval) có thể cải thiện recall cho câu này bằng cách kết hợp keyword matching cho "hoàn tiền" và "ngày".

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử implement **LLM-as-Judge cho faithfulness scoring** để so sánh với heuristic-based approach hiện tại. Scorecard baseline cho thấy nhiều cases mà keyword overlap không phản ánh đúng semantic grounding.

Ngoài ra, tôi muốn thêm **citation accuracy metric** để kiểm tra xem model có gắn `[1]`, `[2]` đúng với sources trong context không - đây là yếu tố quan trọng cho trustworthiness mà eval hiện tại chưa đo lường.

---

*Lưu file này với tên: `reports/individual/ChuBaTuanAnh.md`*
