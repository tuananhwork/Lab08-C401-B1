# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` | CSV batch export từ hệ thống quản lý policy | Duplicate rows, stale version (14→7 ngày), missing fields, invalid date format (DD/MM/YYYY), unknown doc_id | `quarantine_records`, `raw_records`, expectation `refund_no_stale_14d_window` |
| `data/docs/*.txt` (canonical) | Static file kế thừa từ Day 09 | File bị xóa/sửa ngoài pipeline, mất đồng bộ version giữa docs và CSV export | Freshness SLA (24h), `embed_prune_removed` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash ổn định: `{doc_id}_{seq}_{sha256[:16]}` — đảm bảo idempotent upsert |
| doc_id | string | Có | Phải thuộc allowlist: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy` |
| chunk_text | string | Có | Min 8 ký tự (expectation warn), min 20 ký tự sau whitespace collapse (quarantine) |
| effective_date | date | Có | ISO YYYY-MM-DD, chuẩn hóa từ DD/MM/YYYY nếu cần. HR policy < 2026-01-01 bị quarantine |
| exported_at | datetime | Có | ISO datetime từ hệ thống export |

---

## 3. Quy tắc quarantine vs drop

> Records bị quarantine được lưu tại `artifacts/quarantine/quarantine_{run_id}.csv` với cột `reason` ghi rõ lý do.
> Các lý do quarantine: `unknown_doc_id`, `missing_effective_date`, `invalid_effective_date_format`, `stale_hr_policy_effective_date`, `missing_chunk_text`, `duplicate_chunk_text`, `chunk_too_short_after_whitespace_normalize`.
> Không drop vĩnh viễn — quarantine giữ nguyên để review. Merge lại cần approval từ Cleaning/Quality Owner.

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: `data/docs/policy_refund_v4.txt` — version v4, cửa sổ hoàn tiền = **7 ngày làm việc**.
> Bản HR hiện hành: `data/docs/hr_leave_policy.txt` — effective_date ≥ 2026-01-01, **12 ngày phép năm**.
> Chunk chứa "14 ngày làm việc" (refund) hoặc "10 ngày phép năm" (HR 2025) được coi là stale và phải clean/quarantine.
