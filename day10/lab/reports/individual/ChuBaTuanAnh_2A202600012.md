# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Chu Bá Tuấn Anh
**Vai trò:** Cleaning Rule Dev A — P2
**Ngày nộp:** 2026-04-15
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py`: Phát triển Rule 1 và Rule 2 trong hàm `clean_rows()`
  - **Rule 1 (BOM/control char)**: Phát hiện ký tự BOM (`\ufeff`) và control characters (ASCII 0-31, 127) → quarantine để ngăn dữ liệu lỗi encoding được embed vào vector store
  - **Rule 2 (Whitespace collapse + min length)**: Chuẩn hóa whitespace thừa (nhiều space/tab → 1 space), quarantine nếu chunk < 20 ký tự sau chuẩn hóa để đảm bảo chất lượng retrieval

**Kết nối với thành viên khác:**

- Code của tôi được P1 merge vào pipeline chính trong `etl_pipeline.py`
- Rule 1-2 chạy song song với Rule 3+ của P3 và expectations của P4
- Kết quả quarantine và metric_impact được P5 sử dụng để phân tích before/after eval

**Bằng chứng (commit / comment trong code):**

- Hàm `_has_control_characters()`: kiểm tra BOM và control chars
- Hàm `_collapse_whitespace()`: sử dụng regex `r"[ \t]+"` để replace
- Metric tracking dict: `{"rule1_bom_control_quarantine": 0, "rule2_whitespace_collapsed": 0, "rule2_short_text_quarantine": 0}`
- Log output: `[P2 Metric Impact] {metrics}`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Quyết định: Quarantine ngay vs. sửa lỗi control characters**

Khi thiết kế Rule 1, tôi đối mặt với lựa chọn: (a) strip control characters và keep row, hoặc (b) quarantine toàn bộ row. Tôi chọn option (b) vì:

1. **Data integrity**: Control characters thường biểu hiện lỗi encoding nghiêm trọng từ nguồn export. Nếu giữ lại, nội dung chunk có thể đã bị corrupt ở phần khác mà ta không detect được
2. **Embedding quality**: SentenceTransformer model có thể interpret control characters theo cách không lường trước, dẫn đến vector embedding sai lệch
3. **Audit trail**: Quarantine giữ nguyên row gốc trong file riêng, giúp team sau này debug nguồn gốc lỗi dễ hơn

Với Rule 2, tôi chọn collapse whitespace thay vì quarantine vì whitespace thừa không làm mất ngữ nghĩa, chỉ cần chuẩn hóa là đủ. Tuy nhiên, tôi thêm ngưỡng 20 ký tự tối thiểu để quarantine các chunk quá ngắn — vì chunk ngắn sẽ không có đủ context cho retrieval, làm giảm precision của top-k results.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Khi chạy pipeline lần đầu với `run-id test-p2-rules`, tôi thấy row 14 có text `"Text có control char \x01\x02 ẩn..."` không bị quarantine dù đã code Rule 1.

**Nguyên nhân:** File CSV mẫu ban đầu tôi viết bằng tay có escaped string `\x01\x02` dưới dạng literal text (4 ký tự: `\`, `x`, `0`, `1`), không phải control character thật (1 byte `\x01`). Hàm `_has_control_characters()` chỉ detect actual bytes `< 32`, nên bỏ qua row này.

**Fix:** Tôi再生 CSV bằng Python script với real control characters: `w.writerow([..., 'Text có control char \x01\x02 ẩn...', ...])`. Sau đó pipeline detect chính xác: `rule1_bom_control_quarantine=2` (row 11 BOM + row 14 control chars).

**Metric phát hiện:** Log pipeline in ra `[P2 Metric Impact] {'rule1_bom_control_quarantine': 2, ...}` xác nhận rule hoạt động đúng. File `artifacts/quarantine/quarantine_test-p2-rules-v2.csv` có đầy đủ 2 rows với reason `bom_or_control_characters_detected`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**Run ID:** `test-p2-rules-v2`

**Trước (baseline không có Rule 1-2):**
- `raw_records=14`, giả định tất cả rows hợp lệ được clean
- Control characters và BOM sẽ được embed → embedding bẩn

**Sau (có Rule 1-2):**
```
[P2 Metric Impact] {'rule1_bom_control_quarantine': 2, 'rule2_whitespace_collapsed': 1, 'rule2_short_text_quarantine': 1}
cleaned_records=7
quarantine_records=7
```

**Chứng cứ:** 
- Row 11 (BOM): `artifacts/quarantine/quarantine_test-p2-rules-v2.csv` line 6, reason=`bom_or_control_characters_detected`
- Row 12 (whitespace): `artifacts/cleaned/cleaned_test-p2-rules-v2.csv` line 8, text đã collapse từ `"Ticket     P1      có..."` → `"Ticket P1 có nhiều khoảng trắng thừa cần chuẩn hóa."`
- Row 13 (short): quarantine với `collapsed_length=9` < 20 threshold

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ:

1. **Configurable thresholds**: Đẩy ngưỡng 20 ký tự và danh sách control characters ra `.env` để team dễ tune mà không sửa code
2. **Control character whitelist**: Cho phép một số control chars hợp lệ (như zero-width joiner trong Unicode emoji) thay vì blanket quarantine tất cả ASCII < 32
3. **Whitespace metric chi tiết hơn**: Ghi nhận số lượng spaces đã remove thay vì chỉ boolean `was_collapsed`, giúp phân tích mức độ "bẩn" của nguồn data
