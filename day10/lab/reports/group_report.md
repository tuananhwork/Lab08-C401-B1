# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

_________________

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| P2-Rule1: BOM/control_char → quarantine | 0 rows detected | 2 rows quarantined (row 11: BOM `\ufeff`, row 14: control chars `\x01\x02`) | `artifacts/quarantine/quarantine_test-p2-rules-v2.csv`, log: `rule1_bom_control_quarantine=2` |
| P2-Rule2: Whitespace collapse + min length 20 | 0 rows affected | 1 row collapsed (row 12), 1 row quarantined for short text (row 13: 9 chars) | `artifacts/quarantine/quarantine_test-p2-rules-v2.csv`, log: `rule2_whitespace_collapsed=1, rule2_short_text_quarantine=1` |
| P3-Rule3: Validate exported_at future date | TBD | TBD | TBD |
| P4-Expect1: effective_date_in_valid_range | TBD | TBD | TBD |
| P4-Expect2: doc_id_distribution_balanced | TBD | TBD | TBD |
| **E7: effective_date_in_valid_range** (P4) | out_of_range_count=0 | out_of_range_count=0 (no false alarm) | logs: p4-sprint2-final, inject-bad-p4-test |
| **E8: doc_id_distribution_balanced** (P4) | missing_doc_ids=none | missing_doc_ids=none (all 4 doc_ids present) | before/after comparison in P4_SPRINT_3_INJECTION_RESULTS.md |

**Rule chính (baseline + mở rộng):**

- **Baseline**: allowlist doc_id, normalize effective_date, HR stale < 2026, deduplicate chunk_text, refund 14→7 days
- **P2新增**: 
  - Rule 1: Phát hiện BOM (`\ufeff`) hoặc control characters (ASCII 0-31, 127) → quarantine để tránh embed dữ liệu lỗi encoding
  - Rule 2: Collapse whitespace thừa (nhiều space/tab → 1 space), quarantine nếu chunk < 20 ký tự sau chuẩn hóa (chất lượng retrieval thấp)
- **P3新增**: Validate exported_at ISO format, quarantine nếu date trong tương lai
- **P4新增**: (see expectations.py)

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

_________________

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

P5 chạy 3 pha để tạo bằng chứng before/after trên cùng collection `day10_kb`:

1) **Baseline sạch**: `python etl_pipeline.py run --run-id p5-baseline` (có refund fix 14→7) rồi chạy `python eval_retrieval.py --out artifacts/eval/p5_baseline_eval.csv`.
2) **Inject corruption**: `python etl_pipeline.py run --run-id p5-inject-bad --no-refund-fix --skip-validate` để cố ý đưa dữ liệu refund cũ vào index; expectation `refund_no_stale_14d_window` fail nhưng vẫn embed để đo tác động retrieval; sau đó chạy `python eval_retrieval.py --out artifacts/eval/p5_after_inject_bad.csv`.
3) **Fix lại dữ liệu**: `python etl_pipeline.py run --run-id p5-after-fix` rồi chạy `python eval_retrieval.py --out artifacts/eval/p5_after_fix_eval.csv` và `python grading_run.py --questions data/test_questions.json --out artifacts/eval/grading_run.jsonl`.

Manifest chứng cứ: `artifacts/manifests/manifest_p5-baseline.json`, `manifest_p5-inject-bad.json`, `manifest_p5-after-fix.json`.

**Kết quả định lượng (từ CSV / bảng):**

So sánh theo 4 câu hỏi retrieval chuẩn:

- **Baseline (`p5_baseline_eval.csv`)**: `contains_expected=4/4`, `hits_forbidden=0/4`.
- **After inject (`p5_after_inject_bad.csv`)**: `contains_expected=4/4`, nhưng `hits_forbidden=1/4` (câu `q_refund_window` bị dính nội dung cấm trong top-k do dữ liệu refund cũ quay lại).
- **After fix (`p5_after_fix_eval.csv`)**: phục hồi về `contains_expected=4/4`, `hits_forbidden=0/4`.

Kết luận: inject corruption không làm giảm recall keyword (`contains_expected` giữ nguyên), nhưng làm giảm **độ an toàn/ngữ nghĩa đúng phiên bản** của câu trả lời (tăng `hits_forbidden`). Sau khi bật lại refund fix và re-embed, chất lượng retrieval trở về baseline. Điều này chứng minh pipeline clean + expectation có tác động trực tiếp đến hành vi truy xuất của hệ thống RAG.

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …
