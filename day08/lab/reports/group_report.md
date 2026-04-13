# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** B1-C401  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Chu Thị Ngọc Huyền | Retrieval Owner | **_ |
| Chu Bá Tuấn Anh | Eval Owner | _** |
| Nguyễn Mai Phương | Documentation Owner | **_ |
| Hứa Quang Linh | Tech Lead | _** |
| Nguyễn Thị Tuyết | Documentation Owner | **_ |
| Nguyễn Văn Lĩnh | Documentation Owner | _** |

**Ngày nộp:** 2026-04-13  
**Repo:** Lecture-Day-08-09-10  
**Độ dài khuyến nghị:** 600–900 từ

---

> **Hướng dẫn nộp group report:**
>
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code, scorecard, hoặc tuning log** — không mô tả chung chung

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn pipeline của nhóm:
>
> - Chunking strategy: size, overlap, phương pháp tách (by paragraph, by section, v.v.)
> - Embedding model đã dùng
> - Retrieval mode: dense / hybrid / rerank (Sprint 3 variant)

**Chunking decision:**

> Nhóm dùng chunk_size=400 tokens, overlap=80 tokens, tách theo sliding window vì tài liệu có cấu trúc linh hoạt và cần giữ context liên tục giữa các phần.

**Embedding model:**

> Sử dụng paraphrase-multilingual-MiniLM-L12-v2 cho embedding, phù hợp với corpus tiếng Việt.

**Retrieval variant (Sprint 3):**

> Chọn hybrid retrieval (dense + BM25 sparse) kết hợp với rerank và query expansion để giải quyết vấn đề alias và exact keyword matching.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất trong lab.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn.

**Quyết định:** Chọn hybrid retrieval làm variant chính cho Sprint 3.

**Bối cảnh vấn đề:**

> Trong baseline, dense retrieval bỏ sót các query dùng alias hoặc exact terms như "Approval Matrix" thay vì "Access Control SOP", dẫn đến context recall thấp.

**Các phương án đã cân nhắc:**

| Phương án             | Ưu điểm         | Nhược điểm                       |
| --------------------- | --------------- | -------------------------------- |
| Dense only            | Đơn giản, nhanh | Bỏ sót keyword exact             |
| BM25 only             | Tốt cho keyword | Thiếu semantic understanding     |
| Hybrid (dense + BM25) | Kết hợp cả hai  | Phức tạp hơn, cần tuning weights |

**Phương án đã chọn và lý do:**

> Chọn hybrid vì corpus có cả ngôn ngữ tự nhiên lẫn tên riêng/mã lỗi, cần cả semantic và keyword matching. RRF fusion với weights 0.6 dense + 0.4 sparse để cân bằng.

**Bằng chứng từ scorecard/tuning-log:**

> Trong scorecard, hybrid cải thiện relevance ở q07 từ 2 lên 5, và q03 từ 4 lên 5.

---

## 3. Kết quả grading questions (100–150 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
>
> - Câu nào pipeline xử lý tốt nhất? Tại sao?
> - Câu nào pipeline fail? Root cause ở đâu (indexing / retrieval / generation)?
> - Câu gq07 (abstain) — pipeline xử lý thế nào?

**Ước tính điểm raw:** ~84/98 (từ aggregated scores)

**Câu tốt nhất:** q04 (Sản phẩm kỹ thuật số có được hoàn tiền không?) — Điểm cao nhất với faithfulness 5, relevance 5, completeness 5 vì retrieval tìm đúng chunk chính sách hoàn tiền.

**Câu fail:** q09 và q10 — Điểm faithfulness 1, relevance 1 vì abstain đúng nhưng không grounded, root cause ở retrieval không tìm được context cho câu hỏi không có answer trong docs.

**Câu gq07 (abstain):** Pipeline abstain đúng cho q09 (ERR-403-AUTH) vì không có info trong docs, nhưng abstain do retrieval fail thay vì reasoned abstain.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

> Dựa vào `docs/tuning-log.md`. Tóm tắt kết quả A/B thực tế của nhóm.

**Biến đã thay đổi (chỉ 1 biến):** Retrieval mode từ dense sang hybrid + rerank + prompt v2 + query expansion.

| Metric         | Baseline | Variant | Delta |
| -------------- | -------- | ------- | ----- |
| Faithfulness   | 4.20     | 4.20    | 0.00  |
| Relevance      | 3.20     | 3.60    | +0.40 |
| Context Recall | 5.00     | 5.00    | 0.00  |
| Completeness   | 2.90     | 2.50    | -0.40 |

**Kết luận:**

> Variant tốt hơn ở relevance (+0.40), tệ hơn ở completeness (-0.40). Cải thiện rõ ở q07 (relevance từ 2 lên 5) nhờ hybrid retrieval giải quyết alias.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên         | Phần đã làm          | Sprint   |
| ------------------ | -------------------- | -------- |
| Chu Thị Ngọc Huyền | Hybrid retrieval     | Sprint 3 |
| Chu Bá Tuấn Anh    | Rerank               | Sprint 3 |
| Nguyễn Mai Phương  | Query expansion      | Sprint 3 |
| Hứa Quang Linh     | Prompt v2            | Sprint 3 |
| Nguyễn Thị Tuyết   | A/B comparison       | Sprint 3 |
| Nguyễn Văn Lĩnh    | Tuning log & reports | Sprint 4 |

**Điều nhóm làm tốt:**

> Phân công rõ ràng, mỗi người tập trung một variant, giúp pipeline đầy đủ.

**Điều nhóm làm chưa tốt:**

> Thiếu test end-to-end sớm, dẫn đến lỗi embedding phát hiện muộn.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> Thử fine-tune embedding model cho tiếng Việt để cải thiện relevance và completeness, vì kết quả cho thấy hybrid retrieval giúp relevance nhưng completeness giảm.

---

_File này lưu tại: `reports/group_report.md`_  
_Commit sau 18:00 được phép theo SCORING.md_
