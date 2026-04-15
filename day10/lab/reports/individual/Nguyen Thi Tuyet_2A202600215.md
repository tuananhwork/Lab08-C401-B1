# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Thị Tuyết
**Vai trò:** P5 — Embed + Eval  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400-650 từ**

---

## 1. Phần phụ trách (80–120 từ)

**File / module:**

- `day10/lab/eval_retrieval.py`
- `day10/lab/grading_run.py`
- các artifact trong `day10/lab/artifacts/eval/` và `day10/lab/artifacts/manifests/`
- phối hợp cập nhật bằng chứng trong `day10/lab/reports/group_report.md`

Phạm vi phụ trách gồm chạy embed/eval trên Chroma, kiểm tra idempotent upsert + prune, và tạo bằng chứng before/after khi inject corruption. Luồng thực hiện dựa trên output cleaned đã được P1 merge từ P2/P3/P4. Các run được thực thi tuần tự gồm `p5-baseline`, `p5-inject-bad`, `p5-after-fix`, sau đó so sánh CSV eval để kết luận ảnh hưởng của dữ liệu bẩn lên retrieval quality.

**Kết nối với thành viên khác:**

Phần việc này nhận cleaned dataset từ pipeline của P1, sử dụng expectation signal của P4 để diễn giải kết quả inject, và cung cấp số liệu định lượng cho P6 hoàn thiện báo cáo nhóm/quality report.

**Bằng chứng (commit / log):**

- commit: `17e2317` (message: `embed +eval`)
- log run có dòng: `embed_upsert count=9 collection=day10_kb`
- artifact chính: `p5_baseline_eval.csv`, `p5_after_inject_bad.csv`, `p5_after_fix_eval.csv`, `grading_run.jsonl`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật chính là dùng chiến lược **đo cùng một bộ câu hỏi trên cùng collection, nhưng thay snapshot dữ liệu theo từng run_id** để tạo so sánh công bằng. Cụ thể, cấu hình được giữ cố định với `CHROMA_COLLECTION=day10_kb`, chạy lần lượt baseline -> inject -> after-fix và luôn đánh giá bằng cùng file câu hỏi (`data/test_questions.json`, `top_k=3`). Cách này giúp loại bỏ nhiễu do thay đổi query set hoặc tham số retrieval.

Phân tích cũng ưu tiên chỉ số `hits_forbidden` bên cạnh `contains_expected`. Lý do là khi corruption xảy ra, hệ thống có thể vẫn trả về nội dung "có vẻ đúng" (`contains_expected=yes`) nhưng lẫn thông tin cấm hoặc phiên bản cũ. Trong bối cảnh policy QA, đây là rủi ro lớn hơn so với việc chỉ thiếu recall. Vì vậy, kết luận chất lượng cần xem song song 2 tín hiệu này, không chỉ nhìn mỗi top1.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Có hai anomaly phát sinh trong quá trình chạy P5.  
Anomaly 1: khi chạy `python eval_retrieval.py --out artifacts/eval/p5_current_eval.csv`, chương trình báo `Collection [day10_kb] does not exist`. Nguyên nhân là Chroma collection chưa được dựng trong môi trường hiện tại. Cách xử lý là chạy lại pipeline baseline (`python etl_pipeline.py run --run-id p5-baseline`) để tạo collection rồi mới chạy eval.

Anomaly 2: ở run inject (`--no-refund-fix --skip-validate`), console Windows bị `UnicodeEncodeError` do ký tự mũi tên trong log. Cách khắc phục là chạy với `PYTHONIOENCODING=utf-8`. Sau đó pipeline hoàn tất và ghi đúng manifest/eval files.

Ngoài ra, `grading_run.py` mặc định đọc `data/grading_questions.json` (không tồn tại). Tham số được đổi sang `--questions data/test_questions.json` để vẫn tạo được `artifacts/eval/grading_run.jsonl`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**Run ID:** `p5-baseline`, `p5-inject-bad`, `p5-after-fix`

Trích từ CSV eval:

- Baseline (`artifacts/eval/p5_baseline_eval.csv`):  
`q_refund_window,...,contains_expected=yes,hits_forbidden=no,...`
- After inject (`artifacts/eval/p5_after_inject_bad.csv`):  
`q_refund_window,...,contains_expected=yes,hits_forbidden=yes,...`
- After fix (`artifacts/eval/p5_after_fix_eval.csv`):  
`q_refund_window,...,contains_expected=yes,hits_forbidden=no,...`

Tổng hợp định lượng 4 câu hỏi:

- Baseline: `contains_expected=4/4`, `hits_forbidden=0/4`
- Inject: `contains_expected=4/4`, `hits_forbidden=1/4`
- After fix: `contains_expected=4/4`, `hits_forbidden=0/4`

Kết quả này chứng minh dữ liệu corruption làm tăng nguy cơ trả lời sai phiên bản, và clean/fix có tác dụng phục hồi chất lượng retrieval.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, ưu tiên tiếp theo là bổ sung script tự động tạo bảng so sánh before/after từ nhiều file CSV eval (tự đếm `contains_expected`, `hits_forbidden`, `top1_doc_expected`) và xuất markdown trực tiếp vào report. Cách này giúp giảm thao tác thủ công, hạn chế sai số khi tổng hợp số liệu Sprint 3 và chuẩn hóa quy trình chấm lại.
