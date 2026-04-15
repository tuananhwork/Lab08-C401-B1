# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Mai Phương
**Vai trò:** P3 — Cleaning Rule Dev B
**MSV:** 2A202600175
**Ngày nộp:** 2026-04-15
**Độ dài yêu cầu:** **400–650 từ**
---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `day10/lab/transform/cleaning_rules.py`
- `day10/lab/test_p3_cleaning_rules.py`

Tôi chịu trách nhiệm phát triển P3: rule validate `exported_at` trong pipeline ingest và chuyển xử lý garbage vào quarantine. Tôi đã thêm helper `_normalize_exported_at(...)`, metric tracking mới, và test coverage cho `missing_exported_at`, `invalid_exported_at_format`, và `future_exported_at`.

**Kết nối với thành viên khác:**

- P2 và tôi hợp tác để đảm bảo rule mới không phá vỡ rule whitespace/BOM.
- P1 dùng output của tôi để chạy pipeline tổng hợp và gửi cleaned CSV cho P5 embed.
- P4 giúp xác nhận expectation suite vẫn hoạt động với tệp cleaned sau rule mới.

**Bằng chứng (commit / comment trong code):**

- code: `transform/cleaning_rules.py`
- test: `test_p3_cleaning_rules.py`
- validation command: `python -m pytest -q test_p3_cleaning_rules.py`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật của tôi là xử lý `exported_at` ngay ở tầng cleaning, không để metadata lỗi đi vào embed. Tôi chuẩn hóa các timestamp sang UTC ISO (`dt.isoformat()`), tách hẳn `missing_exported_at` và `invalid_exported_at_format`, rồi áp quarantine trước khi duplicate detection và refund fix. Cách này giữ metadata sạch cho P5 và giúp P1/P4 dễ phân tích run-level `quarantine_records` cùng `latest_exported_at` trong manifest.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Triệu chứng: raw rows có `exported_at` bị để trống, sai format hoặc nằm trong tương lai. Nếu không xử lý, các bản ghi này vẫn có thể được cleaned và upsert vào Chroma với metadata sai, làm nhiễu phân tích before/after và freshness. Tôi thêm rule P3 để quarantines những row này: missing, format không ISO, hoặc timestamp > UTC now. Tôi cũng gắn metric `rule3_exported_at_invalid_quarantine` và `rule3_exported_at_future_quarantine` để nhóm biết impact của rule.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**run_id:** local unit test validation

Before: `{'doc_id': 'policy_refund_v4', 'exported_at': '10/04/2026'}` → quarantine reason `invalid_exported_at_format`

After: `{'doc_id': 'policy_refund_v4', 'exported_at': '2026-04-10T08:00:00'}` → cleaned, normalized `exported_at` sang `2026-04-10T08:00:00+00:00`

Đây là bằng chứng chức năng trực tiếp từ `test_p3_cleaning_rules.py`, nơi tôi đã xác nhận 4 test P3 đều pass.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ mở rộng rule P3 thành một validation contract dataset: kiểm tra `exported_at` với schema kiểm thử, thêm một file injection chuyên biệt cho `exported_at` trong Sprint 3, và ghi trực tiếp `exported_at` failure counts vào manifest để nhóm dễ so sánh trước/sau.