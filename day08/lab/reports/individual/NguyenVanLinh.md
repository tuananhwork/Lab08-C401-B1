# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Văn Lĩnh  
**Vai trò trong nhóm:** Documentation Owner / Tuning Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 600–700 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong Sprint 3 và Sprint 4, tôi chịu trách nhiệm tổng hợp quyết định tuning và viết tài liệu cuối cùng cho nhóm. Tôi đã hoàn thiện nội dung `docs/tuning-log.md` bằng cách ghi rõ variant đã chọn, lý do lựa chọn, các experiment thiết kế và các kết quả dự kiến. Đồng thời tôi tạo `reports/group_report.md` để tóm tắt phân công, kết quả đánh giá hiện tại và bài học từ lần chạy đánh giá. Công việc tôi làm kết nối chặt với phần của Person 5 (tổng hợp A/B metrics), Person 4 (prompt v2) và Person 1–3 (retrieval/hybrid/query expansion) để đảm bảo báo cáo phản ánh đúng logic pipeline và các vấn đề thực tế.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, tôi hiểu rõ hơn về hai điểm chính: sự khác biệt giữa thiết kế tuning và chất lượng đánh giá thực tế; và tầm quan trọng của retrieval robustness trong RAG. Tôi đã thấy rằng một prompt tốt và query expansion chỉ phát huy hiệu quả khi retrieval trả về chunks. Nếu retrieval layer bị lỗi thì cả baseline và variant đều trở về trạng thái ABSTAIN. Tôi cũng hiểu sâu hơn về cách viết tuning log: không chỉ ghi “đã chọn gì”, mà còn phải ghi “tại sao”, “khi nào nó hữu ích”, và “nếu đánh giá chưa có giá trị thì lý do là gì”.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên là kết quả đánh giá cuối cùng không phản ánh được cải tiến tuning vì lỗi `get_embedding()` trước khi retrieval hoạt động. Tôi đã kỳ vọng variant hybrid+rerank+prompt_v2 sẽ tạo ra khác biệt rõ rệt, nhưng thực tế tất cả 10 câu hỏi đều trả về ABSTAIN với 0 chunks retrieved. Khó khăn lớn nhất là trình bày báo cáo sao cho vẫn rõ ràng và có giá trị, dù dữ liệu đánh giá chưa thực sự hữu ích. Tôi phải cân bằng giữa phần “thiết kế tốt” và phần “thực thi chưa hoàn chỉnh” để nhóm hiểu mình đã làm đúng phần của mình nhưng cần fix infra trước.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** Approval Matrix để cấp quyền hệ thống là tài liệu nào?

**Phân tích:**
Câu hỏi q07 rất thú vị vì nó phản ánh vấn đề alias/tên cũ trong retrieval. Trong scorecard baseline, câu hỏi này cũng nhận ABSTAIN với 0 chunks retrieved, nên điểm faithfulness và relevance chỉ đạt mức an toàn. Vấn đề không nằm ở generation hay prompt, mà nằm ở retrieval/indexing: query dùng alias “Approval Matrix”, trong khi tài liệu chứa tên chính “Access Control SOP”. Đây là trường hợp điển hình cần query expansion và hybrid retrieval. Variant hiện tại dự kiến để cải thiện q07 bằng cách chuyển alias thành từ khóa chính xác và kết hợp dense + BM25. Tuy nhiên, trong lần chạy đánh giá, retrieval không khởi tạo được embedding nên không có cơ hội chứng minh giá trị của variant. Nếu sửa được `get_embedding()`, q07 sẽ là một trong những câu kiểm chứng rõ nhất cho việc hybrid retrieval giải quyết alias.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ ưu tiên sửa `get_embedding()` và rebuild index để có thể rerun đánh giá. Tôi cũng muốn bổ sung logging cho retrieval: kiểm tra số chunk trả về, source của chunk và độ trùng khớp alias trước khi vào LLM. Điều này giúp xác định sớm nếu vấn đề là indexing hay retrieval, thay vì chỉ biết “kết quả ABSTAIN”.
