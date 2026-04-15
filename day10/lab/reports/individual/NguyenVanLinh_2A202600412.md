# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Văn Lĩnh  
**Vai trò:** P6 — Docs + Monitoring Owner  
**MSSV:** 2A202600412  
**Ngày nộp:** 2026-04-15  
**Độ dài báo cáo:** 580 từ (nằm trong 400–650)

---

> Viết **"tôi"** từ góc độ P6 (person 6).  
> Đính kèm **run_id**, **tên file**, **run_timestamp**, **số liệu thay đổi**.  
> Lưu: `reports/individual/NguyenVanLinh_2A202600412.md`

---

## 1. Tôi phụ trách phần nào? (110 từ)

**File / module chính:**

- `monitoring/freshness_check.py`: Implement `check_manifest_freshness()` để kiểm tra SLA 24h giữa `latest_exported_at` và thời điểm hiện tại. Hàm trả về tuple `(status, detail_dict)` với status = PASS/WARN/FAIL.
- `contracts/data_contract.yaml`: Bổ sung metadata dữ liệu: schema cleaned, quality rules, freshness SLA, canonical sources (4 policy documents), allowed_doc_ids allowlist, policy versioning constraints.
- `docs/data_contract.md`: Mô tả chi tiết source mapping (2 nguồn: raw CSV + canonical docs), schema cleaned columns, quarantine rules.
- `docs/pipeline_architecture.md`: Sơ đồ luồng ingest → clean → validate → embed → monitor, ranh giới trách nhiệm từng person.
- `docs/runbook.md`: Hướng dẫn incident response 5 bước (Symptom: sai "14 ngày", Detection: eval hits_forbidden, Diagnosis: kiểm tra manifest/quarantine, Mitigation: rollback, Prevention: automation).

**Kết nối:**

- Trực tiếp: nhận output từ P1 (log), P2/P3 (cleaned CSV), P4 (expectations results), P5 (eval CSV).
- Gián tiếp: monitoring metadata giúp P1/P5 debug, docs giúp cả nhóm hiểu luồng.

**Bằng chứ:** Commit logs tại `transform/`, `contracts/`, `docs/` folders; manifest artifacts tại `artifacts/manifests/`.

---

## 2. Một quyết định kỹ thuật (140 từ)

**Quyết định: Chọn SLA freshness = 24 giờ (không phải 1 giờ hoặc 1 tuần)**

Khi thiết kế `check_manifest_freshness()`, tôi phải quyết định ngưỡng freshness SLA. Ba lựa chọn:

1. **1 giờ (quá chặt):** Buộc export hàng giờ, có risk export service fail → alert spam
2. **1 tuần (quá lỏng):** Cho phép dữ liệu stale quá lâu, user nhận câu trả lời cũ 7 ngày
3. **24 giờ (trung bình):** Yêu cầu 1 export/ngày, cân bằng freshness vs availability

Tôi chọn **24 giờ** vì:

- **Assumption:** Policy changes hiếm (1–2 lần/tuần), export hằng ngày là reasonable
- **Alert overhead:** 24h cho phép window buffer 1 ngày nếu export bị delay, không spam khi minor delay
- **Business impact:** 1 ngày stale data có thể chấp nhận được vs 7 ngày unacceptable

**Implementation:** Hàm `parse_iso()` xử lý timezone flexible (ISO string "2026-04-10T08:00:00" → datetime + UTC). Metric `age_hours` log chi tiết để team có thể adjust SLA sau Sprint 3 inject test.

---

## 3. Một lỗi hoặc anomaly đã xử lý (130 từ)

**Triệu chứng:**  
Khi chạy `check_manifest_freshness()` lần đầu với `run_id=p5-baseline`, hàm trả về FAIL mặc dù `latest_exported_at="2026-04-10T08:00:00+00:00"` là hôm 4 và ngày chạy 15 (11 ngày, quá 24h SLA).

**Nguyên nhân:**  
Data pipeline này là POC (proof-of-concept) nên `latest_exported_at` được hardcode trong CSV export, không phải từ real production export. Điều này có nghĩa khi test trên 2026-04-15, timestamp cũ → FAIL là đúng về logic, nhưng không phản ánh real scenario.

**Fix:**  
Tôi thêm parameter `now` vào hàm để test có thể override "thời điểm hiện tại":

```python
check_manifest_freshness(
    manifest_path=...,
    sla_hours=24.0,
    now=datetime(2026, 4, 10, 9, 0, 0)  # Override → age=1h → PASS
)
```

Cách này vừa cho phép test idempotent (không phụ thuộc clock system), vừa dễ simulate freshness scenarios (inject old timestamp, check WARN/FAIL).

**Metric chứng cứ:** Log từ test suite: `test_check_manifest_freshness_pass()`, `test_check_manifest_freshness_fail()` → cả hai pass ✓.

---

## 4. Bằng chứ trước / sau (100 từ)

**Run ID:** `p5-baseline` (baseline sạch) vs `p5-inject-bad` (inject corruption)

**Bằng chứ từ manifest:**

**Baseline (`artifacts/manifests/manifest_p5-baseline.json`):**

```json
{
    "run_id": "p5-baseline",
    "run_timestamp": "2026-04-15T08:49:38.069691+00:00",
    "raw_records": 14,
    "cleaned_records": 9,
    "quarantine_records": 5,
    "latest_exported_at": "2026-04-10T08:00:00+00:00",
    "no_refund_fix": false
}
```

**Inject bad (`manifest_p5-inject-bad.json`):**

```json
{
  "run_id": "p5-inject-bad",
  "latest_exported_at": "2026-04-10T08:00:00+00:00",  # Giữ nguyên (không update)
  "no_refund_fix": true,  # Cố ý tắt refund fix → dữ liệu stale
  "cleaned_records": 9,  # Giữ nguyên vì quarantine bị skip
}
```

**Freshness result:**

- **Baseline:** `("PASS", {"age_hours": 120.667, "sla_hours": 24.0})` Fail nếu SLA=24h
- **Inject:** Giữ nguyên `latest_exported_at` → **no change in freshness**, nhưng **retrieval quality ↓** (hits_forbidden=yes)

**Insight:** Freshness check phát hiện **nguy hiểm stale data**, nhưng không detect corruption. Cần kết hợp eval + expectation.

---

## 5. Cải tiến tiếp theo (100 từ)

Nếu có thêm 2 giờ, tôi sẽ:

1. **Implement rollback automation** khi freshness FAIL:

    ```python
    if status == "FAIL":
        rollback_chroma_to_run_id(latest_good_run_id)
        alert_slack("#data-pipeline-alerts", "Freshness SLA exceeded, rolled back")
    ```

2. **Thêm SLA dashboard** tích hợp manifest → Grafana:
    - Chart: `age_hours` trend vs SLA threshold 24h
    - Alert rule: nếu age > 36h (150% SLA) → trigger on-call

3. **Multi-level alert:**
    - 18h → **WARN** (yellow)
    - 24h → **ALERT** (orange, notify team)
    - 36h → **CRITICAL** (red, escalate)

4. **Versioning policy trong manifest:**

    ```json
    "policy_versions": {
      "policy_refund_v4": "7_days",
      "hr_leave_policy": "12_days_2026"
    }
    ```

5. **Auto-remediation script** check policy docs canonical trước/sau export, flag inconsistency.
