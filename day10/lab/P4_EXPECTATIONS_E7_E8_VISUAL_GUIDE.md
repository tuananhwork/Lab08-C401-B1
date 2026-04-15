# Visual Guide: Hướng Dẫn E7 & E8 Logic Chi Tiết

---

## 🎯 E7: `effective_date_in_valid_range` — Kiểm Tra Phạm Vi Ngày

### 📍 Vị Trí Thực Hiện

```
Pipeline Flow:
┌──────────────┐
│  Raw CSV     │
│  (10 dòng)   │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│  CLEANING (remove corruption)        │
│  ✓ Validate dates                    │
│  ✓ Remove duplicates                 │
│  ✓ Fix stale refund (14→7 ngày)      │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  EXPECTATIONS CHECK (E1-E8)          │
│                                      │
│  E7: effective_date_in_valid_range  │◄─── [TẠI ĐÂY]
│      ✅ Kiểm tra ngày hợp lệ        │
│      📏 Phạm vi: [2024-01-01, 2027-12-31] │
│                                      │
└──────┬───────────────────────────────┘
       │
       ▼ (nếu E7 FAIL → halt)
```

### 🔍 Logic E7 Chi Tiết

```
Input: cleaned_rows = [
  {effective_date: "2026-02-01"},  ← OK (trong [2024, 2027])
  {effective_date: "2028-01-01"},  ← ❌ FAIL (future)
  {effective_date: "2023-12-31"},  ← ❌ FAIL (stale)
]

STEP 1: String Comparison (so sánh string)
────────────────────────────────────────
"2024-01-01" <= "2026-02-01" <= "2027-12-31" ?
     ✅ YES → trong phạm vi

"2024-01-01" <= "2028-01-01" <= "2027-12-31" ?
     ❌ NO (2028 > 2027) → ngoài phạm vi

"2024-01-01" <= "2023-12-31" <= "2027-12-31" ?
     ❌ NO (2023 < 2024) → ngoài phạm vi

STEP 2: Tạo List Ngoại Lệ
────────────────────────────
out_of_range = [
  {effective_date: "2028-01-01"},
  {effective_date: "2023-12-31"},
]

STEP 3: Kiểm Tra
────────────────
ok7 = len(out_of_range) == 0
    = 2 == 0
    = False

STEP 4: Result
────────────────
ExpectationResult(
  "effective_date_in_valid_range",
  False,  ← FAIL
  "halt", ← DỪNG PIPELINE
  "out_of_range_count=2, metric_impact=detected_future_or_stale_dates"
)

OUTPUT: PIPELINE_HALT (vì có lỗi halt)
```

### 📊 Decision Tree E7

```
                    ┌─ Tất cả dates OK?
                    │   (nằm trong [2024-01-01, 2027-12-31])
                    │
           E7 Check │
                    │
                    ├─ ✅ YES → E7: PASS
                    │           Pipeline: CONTINUE
                    │
                    └─ ❌ NO → E7: FAIL
                                Pipeline: ⛔ HALT
                                (Data corruption detected!)
```

### 🧪 Test Cases E7

```
┌─ Test 1: OK Date
│  Input:  [{effective_date: "2026-02-01"}]
│  Expected: E7 PASS ✓
│  Hiện Tượng: Ngày hợp lệ
│
├─ Test 2: Future Date
│  Input:  [{effective_date: "2028-06-15"}]
│  Expected: E7 FAIL
│  Severity: HALT ⛔
│  Hiện Tượng: Phát hiện bug export → future date
│
└─ Test 3: Stale Date
   Input:  [{effective_date: "2023-01-01"}]
   Expected: E7 FAIL
   Severity: HALT ⛔
   Hiện Tượng: Phát hiện dữ liệu migrate cũ
```

---

## 🎯 E8: `doc_id_distribution_balanced` — Kiểm Tra Phân Bố Tài Liệu

### 📍 Vị Trí Thực Hiện

```
Pipeline Flow (tiếp theo E7):
┌──────────────────────────────────────┐
│  EXPECTATIONS CHECK (E1-E8)          │
│                                      │
│  E7: effective_date_in_valid_range  │✓ PASS
│                                      │
│  E8: doc_id_distribution_balanced   │◄─── [TẠI ĐÂY]
│      ✅ Kiểm tra doc_ids đầy đủ     │
│      📋 Allowlist: 4 tài liệu        │
│                                      │
│  Allowlist: {                        │
│    "policy_refund_v4",               │
│    "sla_p1_2026",                    │
│    "it_helpdesk_faq",                │
│    "hr_leave_policy"                 │
│  }                                   │
│                                      │
└──────┬───────────────────────────────┘
       │
       ▼ (nếu E8 FAIL → warn, nhưng tiếp tục)
```

### 🔍 Logic E8 Chi Tiết

```
Input: cleaned_rows = [
  {doc_id: "policy_refund_v4", chunk_text: "..."},
  {doc_id: "sla_p1_2026", chunk_text: "..."},
  {doc_id: "it_helpdesk_faq", chunk_text: "..."},
  # ❌ Thiếu: hr_leave_policy (toàn bộ bị quarantine!)
]

STEP 1: Định Nghĩa Allowlist
─────────────────────────────
allowlist = {
  "policy_refund_v4",
  "sla_p1_2026",
  "it_helpdesk_faq",
  "hr_leave_policy"
}

STEP 2: Tạo Set Doc_IDs Hiện Diện
────────────────────────────────────
present_doc_ids = {r.get("doc_id") for r in cleaned_rows}
               = {"policy_refund_v4", "sla_p1_2026", "it_helpdesk_faq"}

STEP 3: Tìm Doc_IDs Bị Thiếu (Set Difference)
──────────────────────────────────────────────
missing_doc_ids = allowlist - present_doc_ids
               = {"policy_refund_v4", "sla_p1_2026", "it_helpdesk_faq", "hr_leave_policy"}
                 - {"policy_refund_v4", "sla_p1_2026", "it_helpdesk_faq"}
               = {"hr_leave_policy"}

STEP 4: Kiểm Tra
────────────────
ok8 = len(missing_doc_ids) == 0
    = 1 == 0
    = False

STEP 5: Result
────────────────
ExpectationResult(
  "doc_id_distribution_balanced",
  False,  ← FAIL
  "warn", ← CẢnh báo nhưng tiếp tục
  "missing_doc_ids={'hr_leave_policy'}, metric_impact=found_completely_missing_policy"
)

OUTPUT: PIPELINE_OK (warn logged, but continue)
```

### 📊 Decision Tree E8

```
             ┌─ Tất cả 4 doc_ids có mặt?
             │  {policy_refund_v4, sla_p1_2026, 
             │   it_helpdesk_faq, hr_leave_policy}
             │
    E8 Check │
             │
             ├─ ✅ YES → E8: PASS
             │           Pipeline: CONTINUE (dữ liệu đầy đủ)
             │
             └─ ❌ NO → E8: FAIL
                         Pipeline: ⚠️  WARN (logged)
                         Continue: YES (data incomplete but ok)
                         Alert: "Policy missing: {doc_ids}"
```

### 🧪 Test Cases E8

```
┌─ Test 1: Tất Cả Có Mặt (Full Set)
│  Input: [
│    {doc_id: "policy_refund_v4"},
│    {doc_id: "sla_p1_2026"},
│    {doc_id: "it_helpdesk_faq"},
│    {doc_id: "hr_leave_policy"}
│  ]
│  Expected: E8 PASS ✓
│  missing_doc_ids = {} (tập hợp rỗng)
│
├─ Test 2: Missing 1 Doc (Partial Failure)
│  Input: [
│    {doc_id: "policy_refund_v4"},
│    {doc_id: "sla_p1_2026"},
│    {doc_id: "it_helpdesk_faq"},
│    # Thiếu: hr_leave_policy
│  ]
│  Expected: E8 FAIL
│  Severity: WARN ⚠️
│  missing_doc_ids = {"hr_leave_policy"}
│  Hiện Tượng: HR rule quá tích cực → toàn bộ chunks bị loại
│
└─ Test 3: Missing Multiple Docs (Major Failure)
   Input: [
     {doc_id: "it_helpdesk_faq"}
     # Thiếu: policy_refund_v4, sla_p1_2026, hr_leave_policy
   ]
   Expected: E8 FAIL
   Severity: WARN ⚠️
   missing_doc_ids = {"policy_refund_v4", "sla_p1_2026", "hr_leave_policy"}
   Hiện Tượng: Nghiêm trọng → chỉ 1/4 tài liệu còn lại
```

---

## 📋 So Sánh E7 vs E8

```
                    E7                          E8
                    ──                          ──
Tên              effective_date_         doc_id_distribution_
                 in_valid_range          balanced

Phát Hiện        Ngày sai                Tài liệu mất
Gì?              (tương lai/cũ)          (hoàn toàn)

Severity         HALT ⛔                 WARN ⚠️

Tác Động         Pipeline dừng           Pipeline tiếp tục
Khi FAIL                                 (nhưng ghi log)

Kiểm Tra         Từng dòng               Toàn bộ dataset
Mức               (row-level)            (set-level)

Metric           out_of_range_count     missing_doc_ids
Chỉ Số           (số dòng sai)           (danh sách thiếu)

Khi OK           Tất cả dates OK         Cả 4 doc_ids OK
                 [2024-01-01,            {p_refund, sla,
                  2027-12-31]            faq, hr_leave}

Ví Dụ Lỗi        Date 2028-01-01         No chunks từ
                                         hr_leave_policy

Nguyên Nhân      Bug export DB           Cleaning rule
Lỗi              (future date)           quá tích cực
```

---

## 🌊 Luồng Hoàn Chỉnh E7 → E8

```
┌─────────────────────────────────────────────────────────────┐
│ DATA COMES IN (raw CSV)                                     │
│ 10 dòng từ policy_export_dirty.csv                         │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ CLEANING PHASE                                              │
│ ✓ Normalize dates → ISO format (ngày DD/MM/YY → YYYY-MM-DD)│
│ ✓ Remove duplicates                                         │
│ ✓ Fix stale refund (14 ngày → 7 ngày)                      │
│ ✓ Quarantine bad records                                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
         [6 cleaned, 4 quarantine]
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ EXPECTATIONS VALIDATION                                     │
│                                                             │
│  E1-E6: Basic checks (dòng cơ bản)                         │
│  └─ All pass ✓                                             │
│                                                             │
│  E7: Date Range Check (kiểm tra ngày)                      │
│  ├─ Input: 6 dòng cleaned                                  │
│  ├─ Check: "2026-02-01" ∈ [2024-01-01, 2027-12-31]? YES   │
│  ├─ Result: ✓ PASS → out_of_range_count = 0               │
│  └─ Action: CONTINUE                                       │
│                                                             │
│  E8: Doc Distribution Check (kiểm tra tài liệu)           │
│  ├─ Input: 6 dòng cleaned                                  │
│  ├─ Doc IDs Present: {policy_refund, sla, faq, hr_leave}  │
│  ├─ Check: allowlist ⊆ present? YES                        │
│  ├─ Result: ✓ PASS → missing_doc_ids = none                │
│  └─ Action: CONTINUE                                       │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ PIPELINE_OK ✓       │
         │ All checks passed   │
         │ Ready for embed     │
         └─────────────────────┘
```

---

## 🎓 Học Liệu: Tạo Expectation Mới

Nếu bạn muốn thêm E9, E10… theo mẫu, làm như sau:

```python
# TEMPLATE để Copy

# E9: [TÊN_MỚI]
# [MỤC ĐÍCH]
[LOGIC_KIỂM_TRA] = [
    r
    for r in cleaned_rows
    if [ĐIỀU_KIỆN_FAIL]
]
ok9 = len([LOGIC_KIỂM_TRA]) == 0  # hoặc != 0 tuỳ trường hợp
results.append(
    ExpectationResult(
        "[e9_name_snake_case]",
        ok9,
        "halt",  # hoặc "warn"
        f"[metric_name]={len([LOGIC_KIỂM_TRA])}, metric_impact=[tác_động]",
    )
)
```

### Ví Dụ: E9 (Giả Định)

```python
# E9: chunk_text_not_empty
# Phát hiện khi chunk_text là whitespace-only
empty_text = [
    r
    for r in cleaned_rows
    if not (r.get("chunk_text") or "").strip()
]
ok9 = len(empty_text) == 0
results.append(
    ExpectationResult(
        "chunk_text_not_empty",
        ok9,
        "warn",
        f"empty_chunks={len(empty_text)}, metric_impact=lost_content_due_to_whitespace_only",
    )
)
```

---

## 📌 Kết Luận

| Khía Cạnh | E7 | E8 |
|-----------|----|----|
| **Tên** | Date range | Doc distribution |
| **Tác Dụng** | Phát hiện date lỗi | Phát hiện policy mất |
| **Severity** | HALT | WARN |
| **Cơ Chế** | String comparison | Set difference |
| **Khi Fail** | Dừng pipeline | Ghi cảnh báo |

**Cả E7 & E8 đều bảo vệ chất lượng dữ liệu cho pipeline, đặc biệt trước khi nhúng vector vào Chroma.**

---

*Hướng Dẫn: 15/4/2026 — P4 Quality Engineer*
