# Quality report — Lab Day 10 (nhóm C401-B1)

**run_id:** p5-baseline, p5-inject-bad, p5-after-fix  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số             | Baseline (p5-baseline) | Inject Bad (p5-inject-bad) | After Fix (p5-after-fix) | Ghi chú                            |
| ------------------ | ---------------------- | -------------------------- | ------------------------ | ---------------------------------- |
| raw_records        | 14                     | 14                         | 14                       | Không đổi (cùng CSV input)         |
| cleaned_records    | 9                      | 9                          | 9                        | Không đổi (logic clean giống nhau) |
| quarantine_records | 5                      | 5                          | 5                        | Không đổi (logic clean giống nhau) |
| Expectation halt?  | PASS (6/6)             | FAIL (E6 refund stale)     | PASS (6/6)               | E6: refund_no_stale_14d_window     |

---

## 2. Before / after retrieval (bắt buộc)

> Đính kèm hoặc dẫn link tới `artifacts/eval/p5_baseline_eval.csv`, `artifacts/eval/p5_after_inject_bad.csv`, `artifacts/eval/p5_after_fix_eval.csv`.

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Baseline (p5-baseline):** contains_expected=yes, hits_forbidden=no ✓  
**Inject Bad (p5-inject-bad):** contains_expected=no, hits_forbidden=yes ✗  
**After Fix (p5-after-fix):** contains_expected=yes, hits_forbidden=no ✓

**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)

**Baseline (p5-baseline):** contains_expected=yes, hits_forbidden=no ✓  
**Inject Bad (p5-inject-bad):** contains_expected=yes, hits_forbidden=no ✓ (HR không bị inject)  
**After Fix (p5-after-fix):** contains_expected=yes, hits_forbidden=no ✓

---

## 3. Freshness & monitor

> Kết quả `freshness_check` (PASS/WARN/FAIL) và giải thích SLA bạn chọn.

**SLA chọn:** 24 giờ - cân bằng giữa freshness (không quá cũ) và operational overhead (không alert spam khi export delay nhỏ).

**Kết quả freshness check:**

- Baseline: PASS (age_hours=1.0, sla_hours=24.0)
- Inject Bad: PASS (age_hours=1.0, sla_hours=24.0)
- After Fix: PASS (age_hours=1.0, sla_hours=24.0)

**Giải thích:** Tất cả đều PASS vì `latest_exported_at="2026-04-10T08:00:00+00:00"` và test chạy trong ngày 2026-04-10 (age < 24h).

---

## 4. Corruption inject (Sprint 3)

> Mô tả cố ý làm hỏng dữ liệu kiểu gì (duplicate / stale / sai format) và cách phát hiện.

**Cách inject corruption:**

- Tắt refund fix: `--no-refund-fix` → giữ nguyên "14 ngày làm việc" thay vì fix thành "7 ngày"
- Bypass validation: `--skip-validate` → không chạy expectations, cho phép dữ liệu sai vào embed

**Phát hiện:**

- Eval metric: `hits_forbidden=yes` trên `q_refund_window` (câu hỏi về refund window)
- Expectation: E6 `refund_no_stale_14d_window` FAIL (halt severity)
- Manifest: `no_refund_fix: true` flag để track

**Tác động:** Retrieval trả về "14 ngày" (sai) thay vì "7 ngày" (đúng), chứng minh cleaning rule quan trọng.

---

## 5. Hạn chế & việc chưa làm

- **Test coverage:** Chỉ test trên data sạch, chưa test edge cases thực tế (BOM chars, invalid dates)
- **Monitoring:** Freshness check chỉ WARN/FAIL, chưa có alerting system tích hợp
- **Automation:** Chưa có CI/CD pipeline để auto-run tests khi code change
- **Scalability:** Pipeline chỉ xử lý 14 records, chưa test với 1000+ records
- **Versioning:** Policy versioning hard-code, chưa có config management system
