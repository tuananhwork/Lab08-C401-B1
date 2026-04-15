# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401-B1  
**Thành viên:**
| Tên | Vai trò (Day 10) | MSSV |
|-----|------------------|-------|
| Chu Thị Ngọc Huyền | P1 - Pipeline Lead  | 2A202600015 |
| Chu Bá Tuấn Anh | P2 - Cleaning & Quality Owner | 2A202600012 |
| Nguyễn Mai Phương | P3 - Cleaning Rule Dev B | 2A202600175 |
| Hứa Quang Linh | P4 - Quality / Expectation | 2A202600466 |
| Nguyễn Thị Tuyết | P5 - Embed + Eval | 2A202600215 |
| Nguyễn Văn Lĩnh | P6 - Docs + Monitoring | 2A202600412 |

**Ngày nộp:** 2026-04-15  
**Repo:** https://github.com/tuananhwork/Lab08-C401-B1  
**Độ dài báo cáo:** 850 từ (vượt khuyến nghị 600–1000)

---

> **Nộp tại:** `reports/group_report.md`  
> **Run ID chính:** `final` (baseline sạch), `inject-bad` (inject corruption), `after-fix` (khôi phục)  
> **Artifact chứng cứ:** `artifacts/eval/baseline_eval.csv`, `artifacts/eval/after_inject_bad.csv`, `artifacts/eval/after_fix_eval.csv`, `artifacts/manifests/manifest_final.json`

---

## 1. Pipeline tổng quan (200 từ)

**Nguồn raw:**  
Dữ liệu gốc là CSV export từ hệ thống quản lý policy (`data/raw/policy_export_dirty.csv`): 14 records chứa thông tin policy hoàn tiền, SLA phản hồi IT, chính sách nghỉ phép HR, và FAQ hỗ trợ. Dữ liệu có lỗi: duplicate rows, timestamp sai định dạng, stale policy version (14 ngày hoàn tiền cũ thay vì 7 ngày phiên bản mới), missing fields.

**Chuỗi luồng end-to-end:**

1. **Ingest** (P1): Load raw CSV → parse 14 rows, ghi log `run_id`
2. **Clean** (P2, P3): Áp 9 rule (6 baseline + 3 mới P2/P3) → tách thành 9 cleaned + 5 quarantine
3. **Validate** (P4): Kiểm tra 8 expectations (6 halt + 2 warn), tất cả pass ✓
4. **Embed** (P1/P5): Upsert 9 chunks vào Chroma collection `day10_kb` (OpenAI `text-embedding-3-small`), prune stale IDs
5. **Retrieve + Eval** (P5): Chạy 4 câu hỏi benchmark, so sánh before/after

**Lệnh chạy một dòng:**

```bash
python3 etl_pipeline.py run --run-id final && \
python3 eval_retrieval.py --out artifacts/eval/baseline_eval.csv
```

**Run ID và artifact:**
- `run_id`: `final` (baseline sạch), `inject-bad` (inject corruption), `after-fix` (fix lại)
- Log: `artifacts/logs/run_final.log`
- Manifest: `artifacts/manifests/manifest_final.json` → `{"run_id": "final", "raw_records": 14, "cleaned_records": 9, "quarantine_records": 5, "latest_exported_at": "2026-04-10T08:00:00+00:00"}`

---

## 2. Cleaning & expectation (200 từ)

**Baseline + mới:**

Baseline đã có 6 rules: allowlist doc_id, normalize effective_date, HR stale < 2026, deduplicate, refund 14→7 fix, min_one_row check.

Nhóm thêm:
- **P2-Rule1:** BOM/control char → quarantine (phát hiện ký tự `\ufeff` hoặc ASCII 0-31). **Metric:** `rule1_bom_control_quarantine=0` trên CSV mẫu (rows có BOM trong expanded CSV bị phát hiện)
- **P2-Rule2:** Whitespace collapse + min length 20 → quarantine nếu < 20 ký tự sau normalize. **Metric:** `rule2_whitespace_collapsed=1` (row 12 collapsed), `rule2_short_text_quarantine=1` (row 13: "Ngắn quá." = 9 chars)
- **P3-Rule3:** Validate exported_at ISO format, quarantine nếu future date. **Metric:** `rule3_exported_at_invalid_quarantine=0`, `rule3_exported_at_future_quarantine=0`
- **P4-Expect1:** `effective_date_in_valid_range` (2024–2027). **Metric:** `out_of_range_count=0` ✓
- **P4-Expect2:** `doc_id_distribution_balanced` (mỗi doc_id ≥1 chunk). **Metric:** `missing_doc_ids=[]` ✓ (all 4 doc_ids: policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy present)

### 2a. Bảng metric_impact

| Rule / Expectation | Trước (baseline) | Sau (sau P2/P3/P4 merge) | Chứng cứ |
|---|---|---|---|
| P2-Rule1: BOM/control_char | 0 detected | 0 quarantined (CSV mẫu không có BOM) | `artifacts/quarantine/quarantine_final.csv` |
| P2-Rule2: Whitespace + min20 | 0 collapsed, 0 short | 1 collapsed, 1 quarantined ("Ngắn quá." 9 chars) | log: `rule2_whitespace_collapsed=1, rule2_short_text_quarantine=1` |
| P3-Rule3: Validate exported_at | 0 invalid | 0 quarantined | manifest_final.json: `latest_exported_at=2026-04-10T08:00:00+00:00` ✓ |
| P4-E7: date_range_2024-27 | pass | pass (out_of_range_count=0) | `run_final.log`: E7 OK (halt) |
| P4-E8: doc_id_balanced | pass | pass (4/4 doc_ids present) | `run_final.log`: E8 OK (warn) |
| **Cumulative: cleaned_records** | — | 9 | manifest_final.json |
| **Cumulative: quarantine_records** | — | 5 | manifest_final.json |

**Quyết định:** P2-Rule2 phát hiện 1 row whitespace + 1 row quá ngắn (metric thay đổi thực tế). P2-Rule1 và P3-Rule3 không phát hiện trên CSV mẫu nhưng team giữ logic để phòng thủ injection. Expectation halt nếu fail → pipeline stop, không embed dữ liệu sai.

---

## 3. Before / after ảnh hưởng retrieval (250 từ)

**Kịch bản inject Sprint 3:**

Nhóm tạo 3 snapshot để đo tác động retrieval:

1. **Baseline sạch:** `python3 etl_pipeline.py run --run-id final` (refund fix 14→7 bật) → embed sạch vào Chroma
2. **Inject corruption:** `python3 etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate` (cố ý tắt refund fix, bypass expectation halt) → dữ liệu refund 14 ngày cũ vào index. Log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`, `embed_prune_removed=1`
3. **Fix lại:** `python3 etl_pipeline.py run --run-id after-fix` (refund fix bật lại) → phục hồi dữ liệu sạch, `embed_prune_removed=1`

**Kết quả định lượng:**

**Baseline (`baseline_eval.csv`, run_id=final):**
```
q_refund_window:       contains_expected=yes, hits_forbidden=no,  top1=policy_refund_v4  ✓
q_p1_sla:              contains_expected=yes, hits_forbidden=no,  top1=sla_p1_2026       ✓
q_lockout:             contains_expected=yes, hits_forbidden=no,  top1=it_helpdesk_faq   ✓
q_leave_version:       contains_expected=yes, hits_forbidden=no,  top1=hr_leave_policy   ✓ (top1_doc_matches=true)
→ Score: 4/4 chính xác
```

**After inject (`after_inject_bad.csv`, run_id=inject-bad):**
```
q_refund_window:       contains_expected=yes, hits_forbidden=yes, top1="14 ngày làm việc" ✗
q_p1_sla:              contains_expected=yes, hits_forbidden=no,  top1=sla_p1_2026       ✓
q_lockout:             contains_expected=yes, hits_forbidden=no,  top1=it_helpdesk_faq   ✓
q_leave_version:       contains_expected=yes, hits_forbidden=no,  top1=hr_leave_policy   ✓ (top1_doc_matches=true)
→ Score: 3/4 chính xác (recall ok, precision ↓ do chunk stale)
```

**After fix (`after_fix_eval.csv`, run_id=after-fix):**
```
q_refund_window:       contains_expected=yes, hits_forbidden=no,  top1="7 ngày làm việc"  ✓
q_p1_sla:              contains_expected=yes, hits_forbidden=no,  top1=sla_p1_2026       ✓
q_lockout:             contains_expected=yes, hits_forbidden=no,  top1=it_helpdesk_faq   ✓
q_leave_version:       contains_expected=yes, hits_forbidden=no,  top1=hr_leave_policy   ✓ (top1_doc_matches=true)
→ Score: 4/4 chính xác (phục hồi baseline)
```

**Kết luận:** Inject corruption không làm giảm keyword recall nhưng **làm giảm ngữ nghĩa chính xác** của câu trả lời. Sau khi bật lại refund fix và re-embed, pipeline phục hồi hoàn toàn. Điều này chứng minh **cleaning + expectation + monitoring có tác động trực tiếp đến chất lượng retrieval của hệ thống RAG**.

---

## 4. Freshness & monitoring (120 từ)

**SLA chọn:** 24 giờ (sla_hours=24.0)

**Kết quả freshness_check (run_id=final):**

```
python3 etl_pipeline.py freshness --manifest artifacts/manifests/manifest_final.json
→ FAIL {"latest_exported_at": "2026-04-10T08:00:00+00:00", "age_hours": 121.131, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

CSV export từ ngày 2026-04-10, đã hơn 5 ngày → FAIL vì vượt SLA 24h. Team chọn 24h để tạo áp lực update data thường xuyên. Trong thực tế cần re-export CSV mới; trong lab đây là expected behavior (data mẫu cố định).

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

**Tổng kết:** Pipeline Day 10 hoàn thiện đầy đủ luồng ETL + monitoring + retrieval quality assurance. Dữ liệu 14 raw → 9 cleaned + 5 quarantine → embed 9 chunks → eval 4/4 pass. Inject corruption chứng minh `hits_forbidden` tăng khi bỏ refund fix, và phục hồi hoàn toàn sau re-run. 8 expectations (6 halt + 2 warn) + freshness SLA 24h + runbook 5 mục tạo guardrail phát hiện lỗi. Embedding dùng OpenAI `text-embedding-3-small` (do Python 3.14 không hỗ trợ PyTorch/sentence-transformers).

