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

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

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
