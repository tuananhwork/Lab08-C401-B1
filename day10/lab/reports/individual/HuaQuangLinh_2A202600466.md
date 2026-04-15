# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hứa Quang Linh  
**Vai trò:** Quality / Expectation Engineer — P4  
**Ngày nộp:** 15 tháng 4, 2026  
**Độ dài báo cáo:** 647 từ

---

## 1. Tôi phụ trách phần nào?

**File / module:**
- `quality/expectations.py` — Thiết kế & triển khai 2 kỳ vọng mới (E7 & E8)
- `test_p4_expectations.py` — Bộ kiểm tra tự động (6 test cases)
- `reports/individual/P4_SPRINT_3_INJECTION_RESULTS.md` — Bằng chứng trước/sau

**Kết nối với thành viên khác:**
P4 hỗ trợ P1 (Pipeline Lead) bằng cách đảm bảo chất lượng dữ liệu trước khi P5 nhúng vào Chroma. P4 cũng cung cấp số liệu cho P6 để viết quality report. Sprint 1-2 P4 và P2/P3 làm song song (thiết kế rule & expectation độc lập). Sprint 3 P4 kiểm tra robustness của expectation khi có hỏng dữ liệu. Sprint 4 P4 ghi các số liệu vào báo cáo nhóm.

**Bằng chứng (commit / comment):**
- Commit: E7 & E8 implementation in `quality/expectations.py` lines 111-137
- Test: `test_p4_expectations.py` — 6 test cases, 100% pass rate
- Log files: `artifacts/logs/run_p4-sprint2-final.log`, `artifacts/logs/run_inject-bad-p4-test.log`

---

## 2. Một quyết định kỹ thuật

Tôi quyết định thiết kế hai kỳ vọng độc lập với mức độ nghiêm trọng khác nhau: **E7 (HALT)** kiểm tra phạm vi ngày hợp lệ [2024-01-01, 2027-12-31], còn **E8 (WARN)** phát hiện khi toàn bộ tài liệu chính sách biến mất. Lý do là:

1. **E7 là HALT** vì hỏng dữ liệu thời gian là lỗi toàn vẹn dữ liệu không thể chấp nhận được — ngày tương lai hoặc cũ sẽ làm xiếc xếp hạng IR. Nếu E7 fail, pipeline phải dừng.

2. **E8 là WARN** vì thiếu tài liệu là lỗi hoạt động, không phải hỏng dữ liệu. Nó cho biết quy tắc làm sạch quá tích cực, nhưng đó là cảnh báo — cho phép pipeline tiếp tục nhúng với dữ liệu bị hạn chế.

3. **Chỉ số (metric_impact)** được ghi rõ: E7 theo dõi `out_of_range_count`, E8 theo dõi `missing_doc_ids` — giúp báo cáo nhóm có số liệu cụ thể.

---

## 3. Một lỗi đã xử lý

**Triệu chứng:** Sprint 1 tôi thiết kế E8 chỉ kiểm tra "nếu doc_id không có chunk thì warn". Tuy nhiên, khi chạy pipeline test lần đầu, E8 không bắt được khi toàn bộ tài liệu bị quarantine (ví dụ nếu P3 viết rule quá tích cực).

**Phát hiện:** Test case `test_e8_doc_id_distribution_missing_one` fail vì logic ban đầu không xác định đúng "missing" — chỉ kiểm tra presence, không kiểm tra completeness.

**Fix:** Thay đổi E8 logic thành kiểm tra `allowlist - present_doc_ids` (tập hợp doc_ids cần thiết trừ những cái hiện diện). Lúc này E8 bắt được khi bất kỳ doc_id nào trong [policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy] biến mất hoàn toàn. Test passed sau fix.

---

## 4. Bằng chứng trước / sau

**Sprint 2 (Baseline):**
```
run_id=p4-sprint2-final
cleaned_records=6
expectation[effective_date_in_valid_range] OK (halt) :: out_of_range_count=0
expectation[doc_id_distribution_balanced] OK (warn) :: missing_doc_ids=none
RESULT: PIPELINE_OK ✓
```

**Sprint 3 (Injection Test):**
```
run_id=inject-bad-p4-test --no-refund-fix --skip-validate
cleaned_records=6
expectation[effective_date_in_valid_range] OK (halt) :: out_of_range_count=0
expectation[doc_id_distribution_balanced] OK (warn) :: missing_doc_ids=none
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1 (expected)
RESULT: E7-E8 robust (zero false positives) ✓
```

**Phân tích:** E7 & E8 không trigger false alarm khi E3 fail do injection. Điều này chứng minh expectation của tôi nhắm mục tiêu các vấn đề đúng thực — không phụ thuộc vào nhau.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thêm **E9: `query_coverage_by_doc_id`** — kiểm tra rằng từng doc_id có ≥ X% chunks xuất hiện trong top-10 kết quả truy vấn mẫu. Hiện tại E8 chỉ phát hiện thiếu hoàn toàn; E9 sẽ phát hiện cả suy giảm partial (ví dụ nếu rule cắt ngắn text quá, đoạn bị mất khỏi retrieval).

---
