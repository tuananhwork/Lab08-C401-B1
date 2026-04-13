# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Chu Thị Ngọc Huyền    
**Vai trò trong nhóm:** Retrieval Owner + Eval Owner + Documentation Owner  
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi tham gia cả 4 sprint với vai trò chủ yếu ở phần **retrieval** và **evaluation**:

- **Sprint 1 (Task 1A):** Phân tích cấu trúc 5 documents, xác định heading patterns và metadata có sẵn, đề xuất metadata schema. Output `DOCUMENT_ANALYSIS.md` làm cơ sở cho metadata extraction và chunking.

- **Sprint 2 (Task 2A):** Implement `retrieve_dense()` — kết nối ChromaDB, embed query, convert cosine distance → similarity score, filter theo threshold.

- **Sprint 3 (Task 3A):** Implement **hybrid retrieval** gồm `retrieve_sparse()` (BM25Okapi) và `retrieve_hybrid()` (RRF fusion, k=60, dense_weight=0.6). Giải quyết vấn đề dense miss exact keywords.

- **Sprint 4 (Task 4A):** Verify `test_questions.json` — cross-check 10 câu hỏi với document gốc, bổ sung expected_answer, thêm field `expected_abstain`.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Hybrid retrieval không phải "tốt hơn" mà là "khác biệt."** Trước lab, tôi nghĩ dense retrieval là đủ cho mọi trường hợp. Nhưng khi test q07 ("Approval Matrix"), dense search hoàn toàn miss vì document đã đổi tên thành "Access Control SOP" — embedding hai cụm từ này không gần nhau trong vector space. BM25 sparse search tìm được vì match exact substring "Approval Matrix" trong ghi chú. RRF fusion kết hợp hai tín hiệu giải quyết vấn đề.

**Reciprocal Rank Fusion (RRF)** cũng là concept tôi hiểu sâu hơn. Thay vì normalize score (phức tạp vì dense và sparse có scale khác nhau), RRF chỉ dùng rank position: `1/(k + rank)`. Đơn giản nhưng robust — không phụ thuộc vào distribution của scores.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

**BM25 tokenization cho tiếng Việt** là vấn đề tôi không lường trước. BM25Okapi mặc định split theo whitespace, nhưng tiếng Việt là ngôn ngữ đơn lập — "hoàn tiền" là một từ ghép gồm 2 âm tiết. BM25 tách thành "hoàn" và "tiền" riêng biệt, dẫn đến match sai (ví dụ: "tiền lương" cũng match "tiền"). Giải pháp tạm thời là chấp nhận tokenization mặc định và bù bằng dense weight cao hơn (0.6 vs 0.4), nhưng nếu có thêm thời gian sẽ dùng Vietnamese tokenizer (underthesea).

**ChromaDB distance vs similarity** cũng gây nhầm lẫn ban đầu. ChromaDB trả về cosine **distance** (0 = giống nhau), nhưng logic ranking cần **similarity** (1 = giống nhau). Phải convert: `similarity = 1 - distance`. Lỗi nhỏ nhưng nếu không debug sớm sẽ đảo ngược toàn bộ ranking.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu hỏi **hard** vì user dùng tên cũ ("Approval Matrix for System Access") trong khi document thực tế đã đổi tên thành "Quy trình Kiểm soát Truy cập Hệ thống (Access Control SOP)". Tên cũ chỉ xuất hiện trong phần ghi chú cuối document: *"Tài liệu này trước đây có tên 'Approval Matrix for System Access'"*.

**Baseline (dense-only):** Trả lời sai. Dense embedding của "approval matrix" không khớp tốt với "access control sop" — semantic overlap thấp. Chunk chứa ghi chú alias không nằm trong top-3. Kết quả: model hallucinate hoặc nói "không tìm thấy".

**Lỗi nằm ở: Retrieval.** Indexing capture đúng (chunk có alias text), nhưng dense retrieval không tìm được.

**Variant (hybrid + query expansion):** Cải thiện rõ rệt. Query expansion map "approval matrix" → ["access control sop", "cấp quyền hệ thống"]. BM25 match exact "Approval Matrix" trong ghi chú. RRF fusion đưa chunk vào top-3, CrossEncoder rerank đẩy lên vị trí 1. Model trả lời chính xác với citation.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Vietnamese tokenizer cho BM25:** Thay whitespace splitting bằng `underthesea` để BM25 nhận diện đúng từ ghép tiếng Việt ("hoàn tiền", "nghỉ phép"). Eval cho thấy sparse retrieval match false positives vì tách sai từ — fix này cải thiện precision của hybrid.

2. **HyDE (Hypothetical Document Embedding):** Với câu mơ hồ như q10 (VIP refund), cho LLM sinh hypothetical answer rồi embed để search. Tuning-log ghi nhận q10 có Context Recall thấp — HyDE có thể giải quyết vì hypothetical answer gần hơn với actual document chunks.

