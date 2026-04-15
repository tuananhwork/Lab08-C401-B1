# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401-B1  
**Thành viên:**
| Tên | Vai trò (Day 10) | MSSV |
|-----|------------------|-------|
| Chu Bá Tuấn Anh | P2 - Cleaning & Quality Owner | 2A202600012 |
| Nguyễn Mai Phương | P3 - Cleaning Rule Dev B | 2A202600175 |
| Hứa Quang Linh | P4 - Quality / Expectation | 2A202600466 |
| Chú Thị Ngọc Huyền | P5 - Embed + Eval | 2A202600015 |
| Nguyễn Văn Linh | P6 - Docs + Monitoring | 2A202600412 |

**Ngày nộp:** 2026-04-15  
**Repo:** https://github.com/AIThucChien/assignments/Lab08-C401-B1/day10/lab  
**Độ dài báo cáo:** 850 từ (vượt khuyến nghị 600–1000)

---

> **Nộp tại:** `reports/group_report.md`  
> **Run ID chính:** `p5-baseline`, `p5-inject-bad`, `p5-after-fix`  
> **Artifact chứng cứ:** `artifacts/eval/p5_baseline_eval.csv`, `artifacts/eval/p5_after_inject_bad.csv`, `artifacts/manifests/manifest_p5-baseline.json`

---

## 1. Pipeline tổng quan (200 từ)

**Nguồn raw:**  
Dữ liệu gốc là CSV export từ hệ thống quản lý policy (`data/raw/policy_export_dirty.csv`): 14 records chứa thông tin policy hoàn tiền, SLA phản hồi IT, chính sách nghỉ phép HR, và FAQ hỗ trợ. Dữ liệu có lỗi: duplicate rows, timestamp sai định dạng, stale policy version (14 ngày hoàn tiền cũ thay vì 7 ngày phiên bản mới), missing fields.

**Chuỗi luồng end-to-end:**

1. **Ingest** (P1): Load raw CSV → parse 14 rows, ghi log run_id
2. **Clean** (P2, P3): Áp 6 rule (baseline + P2/P3 mới) → tách thành 9 cleaned + 5 quarantine
3. **Validate** (P4): Kiểm tra 6 expectations (4 halt + 2 warn), tất cả pass ✓
4. **Embed** (P5): Upsert 9 chunks vào Chroma collection `day10_kb`, prune stale IDs
5. **Retrieve + Eval** (P5): Chạy 4 câu hỏi benchmark, so sánh before/after

**Lệnh chạy một dòng (copy từ README thực tế):**

```bash
python etl_pipeline.py run --run-id p5-baseline && \
python eval_retrieval.py --out artifacts/eval/p5_baseline_eval.csv && \
python freshness_check.py --manifest artifacts/manifests/manifest_p5-baseline.json
```

**Run ID và artifact:**
- `run_id`: `p5-baseline` (baseline sạch), `p5-inject-bad` (inject corruption), `p5-after-fix` (fix lại)
- Log: `artifacts/logs/run_p5-baseline.log`
- Manifest: `artifacts/manifests/manifest_p5-baseline.json` → `{"run_id": "p5-baseline", "raw_records": 14, "cleaned_records": 9, "quarantine_records": 5, "latest_exported_at": "2026-04-10T08:00:00+00:00"}`

---

## 2. Cleaning & expectation (200 từ)

**Baseline + mới:**

Baseline đã có 6 rules: allowlist doc_id, normalize effective_date, HR stale < 2026, deduplicate, refund 14→7 fix, min_one_row check.

Nhóm thêm:
- **P2-Rule1:** BOM/control char → quarantine (phát hiện ký tự `\ufeff` hoặc ASCII 0-31). **Metric:** `rule1_bom_control_quarantine=0` (baseline test case không có BOM actual)
- **P2-Rule2:** Whitespace collapse + min length 20 → quarantine nếu < 20 ký tự sau normalize. **Metric:** `rule2_whitespace_collapsed=0`, `rule2_short_text_quarantine=0` (test data không có case này)
- **P3-Rule3:** Validate exported_at ISO format, quarantine nếu future date. **Metric:** `rule3_exported_at_invalid_quarantine=0`, `rule3_exported_at_future_quarantine=0`
- **P4-Expect1:** `effective_date_in_valid_range` (2024–2027). **Metric:** `out_of_range_count=0` ✓
- **P4-Expect2:** `doc_id_distribution_balanced` (mỗi doc_id ≥1 chunk). **Metric:** `missing_doc_ids=[]` ✓ (all 4 doc_ids: policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy present)

### 2a. Bảng metric_impact

| Rule / Expectation | Trước (baseline) | Sau (sau P2/P3/P4 merge) | Chứng cứ |
|---|---|---|---|
| P2-Rule1: BOM/control_char | 0 detected | 0 quarantined | `artifacts/quarantine/quarantine_p5-baseline.csv` |
| P2-Rule2: Whitespace + min20 | 0 affected | 0 quarantined | test_p2_cleaning_rules.py pass |
| P3-Rule3: Validate exported_at | 0 invalid | 0 quarantined | manifest: `latest_exported_at=2026-04-10T08:00:00+00:00` ✓ |
| P4-Expect1: date_range_2024-27 | pass | pass | expectation log: E7 PASS |
| P4-Expect2: doc_id_balanced | pass | pass (4/4 doc_ids) | expectation log: E8 PASS |
| **Cumulative: cleaned_records** | 9 | 9 (no change) | manifest_p5-baseline.json |
| **Cumulative: quarantine_records** | 5 | 5 (no change) | manifest_p5-baseline.json |

**Quyết định:** Khi P2/P3 rule không phát hiện issue (vì test data sạch), team quyết định giữ logic rule để sẵn sàng inject corruption Sprint 3. Expectation halt nếu fail → pipeline stop, không embed dữ liệu sai.

---

## 3. Before / after ảnh hưởng retrieval (250 từ)

**Kịch bản inject Sprint 3:**

P5 tạo 3 snapshot để đo tác động retrieval:

1. **Baseline sạch:** `python etl_pipeline.py run --run-id p5-baseline` (refund fix 14→7 bật) → embed sạch vào Chroma
2. **Inject corruption:** `python etl_pipeline.py run --run-id p5-inject-bad --no-refund-fix --skip-validate` (cố ý tắt refund fix, bypass expectation halt) → dữ liệu refund 14 ngày cũ vào index
3. **Fix lại:** `python etl_pipeline.py run --run-id p5-after-fix` (refund fix bật lại) → phục hồi dữ liệu sạch

**Kết quả định lượng:**

**Baseline (`p5_baseline_eval.csv`):**
```
q_refund_window:       contains_expected=yes, hits_forbidden=no  ✓
q_p1_sla:              contains_expected=yes, hits_forbidden=no  ✓
q_lockout:             contains_expected=yes, hits_forbidden=no  ✓
q_leave_version:       contains_expected=yes, hits_forbidden=no  ✓
→ Score: 4/4 chính xác
```

**After inject (`p5_after_inject_bad.csv`):**
```
q_refund_window:       contains_expected=yes, hits_forbidden=yes ✗ (chứa dữ liệu "14 ngày" cũ)
q_p1_sla:              contains_expected=yes, hits_forbidden=no  ✓
q_lockout:             contains_expected=yes, hits_forbidden=no  ✓
q_leave_version:       contains_expected=yes, hits_forbidden=no  ✓
→ Score: 3/4 chính xác (recall ok, precision ↓)
```

**After fix (`p5_after_fix_eval.csv`):**
```
q_refund_window:       contains_expected=yes, hits_forbidden=no  ✓
q_p1_sla:              contains_expected=yes, hits_forbidden=no  ✓
q_lockout:             contains_expected=yes, hits_forbidden=no  ✓
q_leave_version:       contains_expected=yes, hits_forbidden=no  ✓
→ Score: 4/4 chính xác (phục hồi baseline)
```

**Kết luận:** Inject corruption không làm giảm keyword recall nhưng **làm giảm ngữ nghĩa chính xác** của câu trả lời. Sau khi bật lại refund fix và re-embed, pipeline phục hồi hoàn toàn. Điều này chứng minh **cleaning + expectation + monitoring có tác động trực tiếp đến chất lượng retrieval của hệ thống RAG**.

---

## 4. Freshness & monitoring (120 từ)

**SLA chọn:** 24 giờ (sla_hours=24.0)

**Kết quả freshness_check:**

```python
check_manifest_freshness(
    manifest_path=Path("artifacts/manifests/manifest_p5-baseline.json"),
    sla_hours=24.0,
    now=datetime(2026, 4, 15, 9, 0, 0, tzinfo=timezone.utc)
)
→ ("PASS", {
    "latest_exported_at": "2026-04-10T08:00:00+00:00",
    "age_hours": 120.667,  # ~5 ngày
    "sla_hours": 24.0
})
# FAIL vì age_hours > sla_hours
```

Nếu tăng SLA lên 120 giờ (5 ngày) → "PASS". Team chọn 24h để tạo áp lực update data thường xuyên (yêu cầu export mới ít nhất 1 lần/ngày).

---

## 5. Liên hệ Day 09 (80 từ)

**Embed trong Day 09 multi-agent:**  
Pipeline Day 10 tạo collection `day10_kb` chứa 9 chunks từ 4 documents (policy refund, SLA IT, HR, FAQ). Day 09 multi-agent có thể:
- (A) Tái sử dụng collection này nếu docs chung
- (B) Tạo collection riêng `day09_kb` nếu agent cần context độc lập

Nhóm Day 10 **khuyến nghị (B)** vì:
- Day 09 agent cần 100% độc lập không phụ thuộc pipeline Day 10
- Versioning docs khác (Day 09 có thể dùng phiên bản cũ để test)
- Monitoring freshness riêng lẻ dễ debug

---

## 6. Rủi ro còn lại & việc chưa làm

- **Risk 1:** Control character / BOM rule (P2-Rule1) chưa test trên real export → có thể false negative
  - Mitigation: Add injection test case Sprint 4
  
- **Risk 2:** Freshness SLA 24h quá chặt nếu export service down
  - Mitigation: Thêm circuit breaker + fallback older manifest
  
- **Risk 3:** Expectation halt có thể block pipeline ngay nếu dữ liệu hơi lỗi
  - Mitigation: Thêm severity warn + alert thay vì halt cho rule mới P2/P3
  
- **Chưa làm:** Rollback automation khi freshness FAIL (manual only hiện tại)

---

**Tổng kết:** Pipeline Day 10 hoàn thiện 80% chức năng monitoring + retrieval quality assurance. Dữ liệu cleaned → embed → eval tạo full trace before/after. Freshness + expectation + runbook tạo guardrail tự động phát hiện lỗi. Sprint 4 tiếp tục tối ưu alert + ownership.

