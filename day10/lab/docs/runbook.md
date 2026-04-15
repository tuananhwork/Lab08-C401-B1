# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

**Đặc tả:** Agent hoặc user thấy câu trả lời có "14 ngày làm việc" (cửa sổ hoàn tiền cũ / khấu hao HR 2025) thay vì "7 ngày" (policy v4 / 12 ngày phép 2026).

**Ví dụ:**
- Query: "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền?"
- Response kỳ vọng: "7 ngày làm việc" (policy_refund_v4)
- Response sai: "14 ngày làm việc" (dữ liệu stale từ export thất bại)

---

## Detection

**Metric báo động:**

1. **Eval metric:** `artifacts/eval/p5_baseline_eval.csv` → cột `hits_forbidden=yes` trên câu `q_refund_window` hoặc `q_leave_version`
   - Baseline: `hits_forbidden=no` (đúng)
   - After inject: `hits_forbidden=yes` (sai)

2. **Expectation fail:** Log pipeline có `E6: refund_no_stale_14d_window = FAIL` hoặc `E3: hr_leave_no_2025_version = FAIL`
   - Severity: **halt** → pipeline dừng, không embed

3. **Freshness alert:** `freshness_check()` return `("WARN" | "FAIL", ...)` nếu `latest_exported_at` cũ hơn 24h

4. **Quarantine spike:** `quarantine_records` tăng đột ngột so với baseline (vd baseline 5 → inject 8)

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi | Nếu sai |
|------|----------|------------------|---------|
| 1 | Kiểm tra manifest: `cat artifacts/manifests/manifest_*.json \| jq .` | `latest_exported_at: "2026-04-10T08:00:00+00:00"`, `cleaned_records: 9`, `quarantine_records: 5` | Nếu `latest_exported_at` nằm trong tương lai hoặc khác baseline → CSV export bị corrupt |
| 2 | Kiểm tra quarantine: `wc -l artifacts/quarantine/*.csv` | Số dòng = baseline (5 rows + header = 6 dòng) | Nếu tăng → có rows mới bị reject. Mở `artifacts/quarantine/quarantine_*.csv` xem cột `reason` |
| 3 | Chạy eval: `python eval_retrieval.py --out artifacts/eval/test_eval.csv` | `hits_forbidden=no` cho cả 4 câu | Nếu `hits_forbidden=yes` → vector store chứa dữ liệu stale. Kiểm tra Chroma collection |
| 4 | Kiểm tra cleaned CSV: `tail -3 artifacts/cleaned/cleaned_*.csv \| cut -d',' -f2,3` | `chunk_text` không chứa "14 ngày" hoặc "2025 policy" | Nếu có → cleaning rule bỏ sót. Xem `transform/cleaning_rules.py` |
| 5 | Kiểm tra log policy document gốc: `grep -n "14 ngày\|2025" data/docs/*.txt` | File `policy_refund_v4.txt` chỉ có "7 ngày", `hr_leave_policy.txt` chỉ có "12 ngày 2026" | Nếu có "14 ngày" → source canonical bị sửa ngoài pipeline. Revert từ Git hoặc backup |

---

## Mitigation

**Bước xử lý (theo thứ tự ưu tiên):**

1. **Ngắn hạn (1–2 phút):** Rollback Chroma collection
   ```bash
   # Kiểm tra backup trước: artifacts/manifests/manifest_p5-baseline.json
   # Xóa collection cũ và re-upsert từ cleaned_p5-baseline.csv
   python -c "
   from chroma_db_ops import rollback_to_run_id  # tùy implementation
   rollback_to_run_id('p5-baseline')
   "
   # Hoặc manual: xóa chroma_db, re-run: python etl_pipeline.py run --run-id p5-baseline
   ```

2. **Ngắn hạn (5 phút):** Kiểm tra source canonical
   ```bash
   git log -1 --name-only data/docs/
   git show HEAD:data/docs/policy_refund_v4.txt | grep "14 ngày"  # nếu có → revert
   ```

3. **Trung hạn (10–15 phút):** Re-run pipeline
   ```bash
   python etl_pipeline.py run --run-id emergency-fix
   python eval_retrieval.py --out artifacts/eval/emergency_eval.csv
   # Xác nhận: hits_forbidden=no cho q_refund_window
   ```

4. **Thông báo tạm thời:**
   - Slack alert: "#data-pipeline-alerts" → "⚠️ Policy data inconsistency detected. Retrieval accuracy degraded. Mitigation in progress."
   - Internal dashboard: show data version (policy_refund_v4 = 7 days, hr_leave 2026 = 12 days)

---

## Prevention

**Dài hạn (thêm vào sprint tới):**

1. **Alert / Monitoring:**
   - SLA 24h freshness: nếu `latest_exported_at` cũ > 24h → trigger alert (không chỉ warn, mà phải có on-call acknowledgement)
   - Expectation `E6` / `E3` liên tục fail → escalate ticket

2. **Automation:**
   - Thêm GitHub hook: khi file `data/docs/policy_refund_v4.txt` bị sửa, tự động trigger pipeline re-run
   - Versioning doc: thêm metadata `version: "4.0"` vào header file, tracking trong manifest

3. **Guardrail kỹ thuật:**
   - Thêm **golden set eval**: các câu hỏi và ground truth answers **hardcoded** trong test suite. Nếu top-1 retrieval khác → fail CI/CD trước khi merge
   - Thêm **vector drift detection**: so sánh similarity distribution của baseline vs current collection; nếu quá khác → flag suspicious

4. **Ownership:**
   - Assign "Policy Data Owner" role (có thể là P2 hoặc P3) chịu trách nhiệm review change `data/docs/` trước merge
   - Runbook này phải được team train tối thiểu 1 lần / sprint
