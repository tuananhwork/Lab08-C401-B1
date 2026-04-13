# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Thị Tuyết  - Nhóm C401-B1
**Vai trò trong nhóm:** Integration + Documentation 
**Ngày nộp:** 2026-04-13  
**Độ dài:** Khoảng 800 từ

---

## 1. Tôi đã làm gì trong lab này?

Nhiệm vụ:
- Sprint 1: implement `get_embedding()` trong `index.py` theo hướng ưu tiên OpenAI (`text-embedding-3-small`) và có fallback sang Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`) để tránh phụ thuộc cứng vào API key; thêm bước test embed 1 chunk ngay trong luồng chạy để xác nhận output embedding có dimension hợp lệ trước khi đi xa hơn.

- Sprint 2: tích hợp end-to-end trong `rag_answer.py`: nối retrieval, context formatting, prompt, và generation thành một hàm `rag_answer()` chạy được; bổ sung guard để khi retrieval không có chunk thì pipeline abstain sớm bằng câu trả lời chuẩn, tránh gọi LLM với context rỗng; thêm test tích hợp cho 3+ query để chứng minh đường ống hoạt động đúng mặt kỹ thuật.

- Sprint 4: hoàn thiện `docs/architecture.md` với nội dung đầy đủ: pipeline overview, indexing config, retrieval config baseline/variant, generation guardrails, và phần evaluation metrics dựa trên artifacts thật của nhóm (scorecard + grading run).

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Chất lượng RAG không đến từ một hàm duy nhất, mà đến từ tính đồng bộ giữa các bước indexing, retrieval và generation; việc chọn model, chuẩn hóa fallback, và đảm bảo cùng embedding space giữa index/query là điều bắt buộc. Nếu index bằng một cấu hình mà query bằng cấu hình khác, retrieval sẽ mất ổn định ngay.

Vai trò của integration: pipeline vẫn fail trong khi từng hàm riêng lẻ đều chạy được do dữ liệu nối giữa các bước không đúng chuẩn (ví dụ context rỗng, metadata thiếu, hoặc prompt không ép citation/abstain); trong hệ thống production, “fail safe” quan trọng hơn “cố gắng trả lời bằng mọi giá”. Với RAG, trả lời sai nhưng tự tin nguy hiểm hơn abstain. Cải thiện: bổ sung guard cho “no candidates”

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất: trạng thái môi trường và dữ liệu chạy thật. Script dù chạy đúng nhưng evaluation vẫn cho kết quả rất thấp vì retrieval trả về 0 chunk trên toàn bộ test set => root-cause lại nằm ở layer retrieval/index state (collection không tồn tại hoặc embedding path bị lệch) (kiểm tra prompt hoặc model generation xem đang có vấn đề)

Một khó khăn khác là làm việc trong repo có thay đổi song song từ nhiều thành viên. Khi pull code mới, local database file (`chroma.sqlite3`) từng gây cản trở merge. => các file runtime/local state cần được quản lý chặt (reset/ignore đúng lúc), nếu không sẽ ảnh hưởng tiến độ collaborative. Ngoài ra, việc force-push/rewrite history ở giữa sprint khiến quy trình sync cũng cần kỷ luật hơn; chỉ cần một người không sync sạch thì rất dễ phát sinh conflict dây chuyền.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** q07 — “Approval Matrix để cấp quyền hệ thống là tài liệu nào?”

Nội dung câu hỏi kiểm tra đúng điểm yếu của dense retrieval: alias query. Ở baseline, câu hỏi này không được trả lời đúng; hệ thống trả abstain và context recall gần như bằng 0. Về mặt bề nổi, output “an toàn” vì không hallucinate, nhưng về mặt chất lượng sản phẩm thì đây là fail, vì câu này thực ra có thể trả lời được nếu mapping đúng alias sang tài liệu `access_control_sop`.

Nếu phân tích theo error tree, lỗi chính nằm ở retrieval thay vì generation. Generation chỉ phản ánh đúng dữ liệu đầu vào: không có evidence thì abstain. Nghĩa là prompt chưa phải thủ phạm chính trong case này. Variant của nhóm có hướng khắc phục đúng: hybrid retrieval + query expansion + rerank. Về lý thuyết, query expansion sẽ nối được “Approval Matrix” với “Access Control SOP”; BM25 sẽ hỗ trợ bắt exact term tốt hơn dense-only; rerank giúp lọc top chunk liên quan nhất trước khi đưa vào prompt.

Tuy nhiên ở run thực tế được log lại, baseline và variant chưa tách được chất lượng vì cả hai đều rơi vào trạng thái retrieval không lấy được chunk (0 chunks). Do đó delta trong scorecard gần như 0, và kết luận công bằng là “chưa đủ điều kiện đánh giá A/B”, không phải “variant không hiệu quả”. Đây là một bài học quan trọng về evaluation hygiene: nếu tầng dưới fail thì mọi so sánh tầng trên đều mất ý nghĩa.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Ưu tiên: chuẩn hóa quy trình rebuild index + smoke test retrieval trước khi chạy eval, để tránh lặp lại tình trạng scorecard đo trên pipeline chưa sẵn sàng; thêm một bộ “pre-eval checks” tự động (kiểm tra collection tồn tại, số chunks > 0, query mẫu retrieve được source kỳ vọng) rồi mới cho phép chạy chấm điểm. Cách này giúp số liệu A/B phản ánh đúng chất lượng kỹ thuật thay vì phản ánh lỗi môi trường.

