# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Chu Thị Ngọc Huyền    
**Vai trò:**  Pipeline Lead   
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `etl_pipeline.py` — entrypoint chính: điều phối luồng ingest → clean → validate → embed → manifest → freshness check.
- `contracts/data_contract.yaml` — điền `owner_team` và `alert_channel`.
- Chạy tất cả pipeline run: `sprint1`, `inject-bad`, `after-fix`, `merged-final`.

**Kết nối với thành viên khác:**

Tôi nhận code cleaning rules từ P2/P3 (`transform/cleaning_rules.py`) và expectations từ P4 (`quality/expectations.py`), sau đó chạy pipeline tổng hợp `merged-final` để verify tất cả exit 0. Kết quả cleaned CSV và Chroma DB được P5 dùng để chạy `eval_retrieval.py` so sánh before/after.

**Bằng chứng (commit / comment trong code):**

Sửa `cmd_embed_internal()` trong `etl_pipeline.py` (dòng 139–160) để hỗ trợ OpenAI embedding khi `EMBEDDING_PROVIDER=openai`, do Python 3.14 không có PyTorch. Tương tự sửa `eval_retrieval.py` và `grading_run.py`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định quan trọng nhất: **chuyển từ sentence-transformers sang OpenAI embedding**. Python 3.14 không hỗ trợ PyTorch, nên `SentenceTransformerEmbeddingFunction` không chạy được. Tôi thêm logic đọc biến `EMBEDDING_PROVIDER` từ `.env`: nếu `openai` thì dùng `OpenAIEmbeddingFunction` với model `text-embedding-3-small`, ngược lại vẫn fallback về sentence-transformers.

Tôi sửa cả 3 file: `etl_pipeline.py`, `eval_retrieval.py`, `grading_run.py` để đảm bảo embedding nhất quán — nếu embed bằng OpenAI nhưng eval bằng sentence-transformers thì vector space khác nhau, retrieval sẽ sai. Quyết định này không thay đổi logic pipeline mà chỉ thay lớp embedding, giữ nguyên idempotent upsert và prune.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Pipeline chạy `python3 etl_pipeline.py run` exit code 3 tại bước embed với lỗi `ModuleNotFoundError: No module named 'sentence_transformers'`, sau đó `No module named 'transformers'`. Cài `pip install sentence-transformers --no-deps` rồi `pip install transformers` cũng thất bại vì `ERROR: No matching distribution found for torch` — PyTorch chưa hỗ trợ Python 3.14.

**Metric phát hiện:** Exit code 3 từ `cmd_embed_internal()` + error log `"ERROR: chromadb chưa cài"` ban đầu, sau đó `ValueError` từ chromadb embedding function.

**Fix:** Thay vì downgrade Python, tôi sửa pipeline hỗ trợ dual provider (OpenAI / local) đọc từ `.env`. Sau fix, `run_id=merged-final` exit 0 với `embed_upsert count=9`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**Inject (run_id=inject-bad, `--no-refund-fix --skip-validate`):**
```
q_refund_window | hits_forbidden=yes | top1: "14 ngày làm việc"
```
Expectation `refund_no_stale_14d_window` FAIL (violations=1), nhưng `--skip-validate` cho tiếp embed → chunk stale "14 ngày" lọt vào Chroma → eval phát hiện `hits_forbidden=yes`.

**After fix (run_id=after-fix, pipeline chuẩn):**
```
q_refund_window | hits_forbidden=no  | top1: "7 ngày làm việc"
```
Tất cả 8 expectations OK, `embed_prune_removed=1` (xóa chunk stale), eval 4/4 câu `contains_expected=yes`, `hits_forbidden=no`. Câu `q_leave_version` có `top1_doc_expected=yes` (hr_leave_policy, 12 ngày phép).

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ thêm **logging embed latency** (thời gian gọi OpenAI API cho mỗi batch upsert) vào manifest, để monitoring phát hiện khi API chậm hoặc rate-limited. Hiện tại manifest chỉ ghi count và timestamp, chưa đo performance — điều này quan trọng khi corpus lớn hơn 10 chunks.
