** Group Name ** B1-C401

# Group Report — Day 08 RAG Lab

## 1. Mục tiêu nhóm

Nhóm triển khai một pipeline RAG hoàn chỉnh: từ indexing, retrieval, generation đến evaluation. Trong Sprint 4, nhiệm vụ chính của nhóm là hoàn thiện đánh giá, tổng hợp kết quả tuning và chuẩn bị báo cáo nhóm.

## 2. Phân công và đóng góp chính

- **Person 1 — Chu Thị Ngọc Huyền:** xây dựng retrieve_dense và trợ giúp với logic retrieval.
- **Person 2 — Chu Bá Tuấn Anh:** thiết kế rerank, cài cross-encoder và kiểm thử top-k.
- **Person 3 — Nguyễn Mai Phương:** xây query expansion alias/synonym.
- **Person 4 — Hứa Quang Linh:** viết prompt v2 tiếng Việt, few-shot và rules citation.
- **Person 5 — Nguyễn Thị Tuyết:** tổng hợp A/B comparison và đo metrics thử nghiệm.
- **Person 6 — Nguyễn Văn Lĩnh:** tổng hợp tuning decision, viết `docs/tuning-log.md` và `reports/group_report.md`.

## 3. Quyết định tuning

Nhóm chọn chiến lược hiện tại là:

- `retrieval_mode = "hybrid"` (dense + BM25 sparse)
- `use_rerank = True` với CrossEncoder `ms-marco-MiniLM-L-6-v2`
- `prompt_version = "v2"` dùng hướng dẫn tiếng Việt và few-shot examples
- `use_query_expansion = True` với alias map cho các thuật ngữ nội bộ

Lợi ích mong đợi:

- Hybrid retrieval giải quyết keyword/alias mà dense embedding dễ bỏ sót.
- Rerank giảm noise và chọn top-3 chunks phù hợp.
- Prompt v2 cải thiện citation, abstain consistency và độ phù hợp tiếng Việt.
- Query expansion giúp giải quyết các câu hỏi dùng tên cũ như "Approval Matrix".

## 4. Kết quả đánh giá

Kết quả thực tế ghi trong `logs/grading_run.json` và scorecards cho thấy:

- Cả baseline và variant đều trả về ABSTAIN cho toàn bộ 10 câu hỏi.
- `chunks_retrieved_avg = 0.0`, `context_recall_avg = 0.00`.
- Các metric baseline/variant đều giống nhau, nên A/B comparison không có ý nghĩa.

Nguyên nhân gốc:

- `get_embedding()` ném ra `NotImplementedError` trong lần chạy đánh giá.
- Retrieval layer không hoạt động, do đó LLM nhận ngữ cảnh rỗng và chọn trả lời an toàn ABSTAIN.

## 5. Phân tích bài học

### Điều gì đã hoạt động

- Cấu trúc pipeline và các thành phần tuning đã được thiết kế đủ rõ ràng để có thể bổ sung sau khi sửa lỗi.
- Khả năng abstain an toàn giúp tránh hallucination khi retrieval thất bại.

### Điều gì cần cải thiện

- Phải đảm bảo đầu vào của retrieval: embedding model cần được triển khai và load được trước khi đánh giá.
- Cần có test end-to-end trước khi ghi log đánh giá để phát hiện lỗi `get_embedding()` sớm hơn.
- Các scorecard hiện tại chưa phản ánh đúng hiệu suất thật vì đánh giá bị chặn bởi lỗi infrastructure.

## 6. Bài học nhóm

- **Phối hợp tốt giữa các thành viên:** mỗi người tập trung một mảng logic, giúp pipeline có đủ phần retrieval, rerank, prompt và evaluation.
- **Tài liệu và log cần song hành:** `docs/tuning-log.md` đã ghi lại cả thiết kế và lưu ý thực tế của lần chạy đánh giá.
- **Giải pháp an toàn tốt:** khi không có context, pipeline vẫn chọn abstain thay vì tạo thông tin sai lệch.

## 7. Khuyến nghị tiếp theo

Để hoàn thiện pipeline, nhóm cần:

1. Fix `get_embedding()` và đảm bảo model embedding load thành công.
2. Rebuild ChromaDB index và verify `list_chunks()` có dữ liệu.
3. Rerun full evaluation với cả baseline và variant.
4. Cập nhật `results/scorecard_baseline.md`, `results/scorecard_variant.md` và `logs/grading_run.json` khi có dữ liệu thực tế.

---

**Kết luận:** Nhóm đã hoàn thành phần thiết kế tuning và báo cáo tổng hợp; tuy nhiên kết quả A/B vẫn chưa xác thực do lỗi retrieval layer, nên bước tiếp theo là khắc phục embedding và chạy lại đánh giá.
