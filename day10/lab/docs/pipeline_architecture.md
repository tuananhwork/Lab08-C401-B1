# Kiến trúc pipeline — Lab Day 10

**Nhóm:** C401-B1
**Cập nhật:** 2026-04-15

---

## 1. Sơ đồ luồng

```
┌─────────────────────┐
│  data/raw/           │
│  policy_export_      │
│  dirty.csv           │
└────────┬────────────┘
         │ load_raw_csv()
         ▼
┌─────────────────────┐     ┌───────────────────────┐
│  clean_rows()        │────▶│  artifacts/quarantine/ │
│  transform/          │     │  quarantine_{run_id}   │
│  cleaning_rules.py   │     │  .csv                  │
│                      │     │  (reason column)       │
│  • allowlist doc_id  │     └───────────────────────┘
│  • normalize date    │
│  • quarantine stale  │
│  • fix refund 14→7   │
│  • dedupe            │
│  • [P2/P3 rules]    │
└────────┬────────────┘
         │ write_cleaned_csv()
         ▼
┌─────────────────────┐
│  artifacts/cleaned/  │
│  cleaned_{run_id}    │
│  .csv                │
└────────┬────────────┘
         │ run_expectations()
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│  quality/            │     │  PIPELINE_HALT       │
│  expectations.py     │──▶  │  (nếu halt severity  │
│                      │     │   fail + không        │
│  • min_one_row       │     │   --skip-validate)    │
│  • no_empty_doc_id   │     └─────────────────────┘
│  • refund_no_stale   │
│  • chunk_min_length  │
│  • [P4 expectations] │
└────────┬────────────┘
         │ pass → embed
         ▼
┌─────────────────────┐
│  cmd_embed_internal  │
│  Chroma upsert by   │
│  chunk_id            │
│  + prune stale ids   │
│  (idempotent)        │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐     ┌───────────────────────┐
│  chroma_db/          │     │  artifacts/manifests/  │
│  day10_kb collection │     │  manifest_{run_id}     │
└─────────────────────┘     │  .json                 │
                            │  (run_id, counts,      │
         ┌──────────────────│   freshness status)    │
         │                  └───────────────────────┘
         ▼
┌─────────────────────┐
│  freshness_check()   │
│  monitoring/         │
│  freshness_check.py  │
│  SLA: 24h            │
│  → PASS / WARN / FAIL│
└─────────────────────┘

📊 Đo lường: run_id ghi trong log + manifest + Chroma metadata
📁 Log: artifacts/logs/run_{run_id}.log
```

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|--------------|
| Ingest | `data/raw/policy_export_dirty.csv` | `List[Dict]` raw rows (14 records) | P1 (Pipeline Lead) |
| Transform | Raw rows | `cleaned_{run_id}.csv` (9 records) + `quarantine_{run_id}.csv` (5 records) | P2, P3 (Cleaning Rule Dev) |
| Quality | Cleaned rows | Expectation results (6 checks: 4 halt + 2 warn) | P4 (Quality Owner) |
| Embed | Cleaned CSV | Chroma collection `day10_kb` (upsert + prune) | P5 (Embed + Eval) |
| Monitor | Manifest JSON | Freshness status (PASS/WARN/FAIL) | P6 (Docs + Monitor) |

---

## 3. Idempotency & rerun

> **Strategy:** Upsert theo `chunk_id` (hash ổn định = `{doc_id}_{seq}_{sha256[:16]}`).
> Sau mỗi lần publish, pipeline **pruned** các vector id tồn tại trong Chroma nhưng không còn trong cleaned CSV hiện tại (`embed_prune_removed` trong log).
> Rerun 2 lần cùng data → collection count không đổi, không duplicate vector.
> Chạy với `--run-id` khác nhau tạo artifact riêng nhưng Chroma chỉ giữ snapshot cuối cùng.

---

## 4. Liên hệ Day 09

> Pipeline Day 10 xử lý **cùng corpus** `data/docs/` của Day 09 (CS + IT Helpdesk).
> CSV export đại diện cho lớp ingestion từ DB/API — mô phỏng real-world nơi raw data có lỗi trước khi embed.
> Sau khi Day 10 pipeline chạy, Chroma `day10_kb` chứa dữ liệu đã clean, phục vụ retrieval worker của Day 09.

---

## 5. Rủi ro đã biết

- **Python 3.14:** `sentence-transformers` (PyTorch) không hỗ trợ → phải dùng OpenAI embedding thay thế
- **Freshness FAIL:** Data CSV export từ 2026-04-10, quá SLA 24h → cần re-export hoặc tăng SLA
- **Single CSV source:** Chỉ 1 file raw → nếu file corrupt thì toàn bộ pipeline fail (không có fallback)
