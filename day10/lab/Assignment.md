# Phân công nhóm — Day 10 Lab (6 người)

## Tổng quan vai trò

| # | Vai trò | File chính phụ trách |
|---|---------|---------------------|
| **P1** | Pipeline Lead | `etl_pipeline.py`, log/manifest |
| **P2** | Cleaning Rule Dev A | `transform/cleaning_rules.py` (rule 1–2) |
| **P3** | Cleaning Rule Dev B | `transform/cleaning_rules.py` (rule 3+) |
| **P4** | Quality / Expectation | `quality/expectations.py` (2+ expectation mới) |
| **P5** | Embed + Eval | `eval_retrieval.py`, Chroma embed, before/after evidence |
| **P6** | Docs + Monitoring | `monitoring/freshness_check.py`, 4 file `docs/*.md`, `contracts/` |

---

## Timeline song song theo Sprint

### Sprint 1 (60') — Ingest & Schema

| Người | Việc cần làm |
|-------|-------------|
| **P1** | Chạy pipeline lần đầu (`python etl_pipeline.py run --run-id sprint1`), kiểm tra log có `run_id`, `raw_records`, `cleaned_records`, `quarantine_records` |
| **P2** | Đọc CSV bẩn (`data/raw/policy_export_dirty.csv`), phân tích lỗi, thiết kế rule 1–2 (VD: BOM/control char, chuẩn hóa whitespace) |
| **P3** | Đọc CSV bẩn, phân tích lỗi, thiết kế rule 3+ (VD: validate `exported_at`, quarantine nếu tương lai) |
| **P4** | Đọc `quality/expectations.py` baseline E1–E4, thiết kế 2 expectation mới (VD: date range check, doc_id distribution) |
| **P5** | Đọc `eval_retrieval.py` + hiểu Chroma embed flow, setup `.env`, test embed idempotent |
| **P6** | Điền `docs/data_contract.md` (source map ≥2 nguồn), `contracts/data_contract.yaml`, bắt đầu `docs/pipeline_architecture.md` (sơ đồ) |

### Sprint 2 (60') — Clean + Validate + Embed

| Người | Việc cần làm |
|-------|-------------|
| **P1** | Review + merge rules từ P2, P3 vào pipeline, chạy pipeline tổng hợp, verify exit 0 |
| **P2** | Code rule 1–2 trong `cleaning_rules.py`, test trên CSV bẩn, ghi `metric_impact` |
| **P3** | Code rule 3+ trong `cleaning_rules.py`, test trên CSV bẩn, ghi `metric_impact` |
| **P4** | Code 2+ expectation trong `expectations.py`, test halt/warn logic, ghi `metric_impact` |
| **P5** | Embed cleaned → Chroma, verify upsert + prune, chạy `eval_retrieval.py` lưu baseline eval CSV |
| **P6** | Hoàn thiện `docs/pipeline_architecture.md`, bắt đầu `docs/runbook.md` (5 mục Symptom→Prevention) |

### Sprint 3 (60') — Inject Corruption & Before/After

| Người | Việc cần làm |
|-------|-------------|
| **P1** | Chạy inject: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, lưu log inject, chạy lại pipeline chuẩn |
| **P2** | Ghi `metric_impact` vào `reports/group_report.md` (bảng so sánh trước/sau), hỗ trợ P5 phân tích |
| **P3** | Ghi `metric_impact` vào `reports/group_report.md` (bảng so sánh trước/sau), hỗ trợ P5 phân tích |
| **P4** | Test expectation fail khi inject, so sánh pass/fail trước/sau inject |
| **P5** | Chạy eval "xấu" (`after_inject_bad.csv`), so sánh 2 file eval, tạo bảng chứng cứ before/after |
| **P6** | Viết quality report (theo `docs/quality_report_template.md`), ghi số liệu before/after vào report |

### Sprint 4 (60') — Monitoring + Docs + Báo cáo

| Người | Việc cần làm |
|-------|-------------|
| **P1** | Chạy freshness check, chạy `grading_run.py` (sau 17:00), viết individual report |
| **P2** | Viết `reports/individual/[tên].md` (400–650 từ) |
| **P3** | Viết `reports/individual/[tên].md` (400–650 từ) |
| **P4** | Viết `reports/individual/[tên].md` (400–650 từ) |
| **P5** | Chạy `grading_run.py` (sau 17:00), viết `reports/individual/[tên].md` |
| **P6** | Hoàn thiện `docs/runbook.md`, tổng hợp `reports/group_report.md`, viết individual report |

---

## Dependency — Ai chờ ai

```
P2, P3 (rules) ──┐
                  ├──→ P1 merge & chạy pipeline ──→ P5 embed + eval
P4 (expects) ────┘                                      │
                                                        ▼
P6 (docs) ◄──── lấy số liệu từ log/eval ─────── Sprint 3 evidence
```

- **P2, P3, P4, P6** làm **song song hoàn toàn** trong Sprint 1–2
- **P1** merge code từ P2+P3+P4 vào cuối Sprint 2, chạy pipeline tổng hợp
- **P5** chờ pipeline chạy xong mới embed + eval (Sprint 1 setup/test Chroma trước)
- **P6** viết docs song song từ đầu, cần số liệu cuối Sprint 3 để điền quality report

---

## Gợi ý rule/expectation mới

### P2 — 2 cleaning rules

1. **BOM / control char**: Loại chunk có BOM character (`\ufeff`) hoặc control char → quarantine
2. **Whitespace collapse**: Chuẩn hóa whitespace thừa trong `chunk_text` (nhiều space → 1 space), quarantine nếu chunk < 20 ký tự sau chuẩn hóa

### P3 — 1+ cleaning rule

3. **Validate exported_at**: Kiểm tra `exported_at` hợp lệ (ISO format), quarantine nếu `exported_at` trong tương lai (data corruption)

### P4 — 2 expectations

1. **`effective_date_in_valid_range`**: Tất cả cleaned rows có `effective_date` trong khoảng 2024–2027 (severity: halt)
2. **`doc_id_distribution_balanced`**: Mỗi `doc_id` trong allowlist phải có ≥1 chunk (phát hiện mất toàn bộ policy) (severity: warn)

---

## Checklist nộp bài — Ai chịu trách nhiệm file nào

| File | Người chính | Review |
|------|------------|--------|
| `etl_pipeline.py` | P1 | P5 |
| `transform/cleaning_rules.py` | P2 + P3 | P1 |
| `quality/expectations.py` | P4 | P1 |
| `eval_retrieval.py` | P5 | P4 |
| `monitoring/freshness_check.py` | P6 | P1 |
| `contracts/data_contract.yaml` | P6 | P1 |
| `docs/pipeline_architecture.md` | P6 | P1 |
| `docs/data_contract.md` | P6 | P2 |
| `docs/runbook.md` | P6 | P5 |
| `docs/quality_report` | P6 + P5 | cả nhóm |
| `reports/group_report.md` | P6 (tổng hợp) | cả nhóm |
| `reports/individual/*.md` | mỗi người tự viết | — |
| `artifacts/eval/grading_run.jsonl` | P5 hoặc P1 | — |
