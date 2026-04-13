# 📋 TEAM ASSIGNMENT — Day 08 RAG Lab (6 người)

**Dự án:** Full RAG Pipeline: Indexing → Retrieval → Generation → Evaluation  
**Thời gian:** 4 tiếng (4 sprints × 60 phút)  
**Deadline nộp code + log:** 18:00  
**Deadline báo cáo:** Sau 18:00  

**Nguyên tắc:** 6 người bình đẳng, không role lãnh đạo, mỗi người commit ở các sprint khác nhau, task xoay vòng

---

## Group infomation

| Person   | Full name          |
| -------- | ------------------ |
| Person 1 | Chu Thị Ngọc Huyền |
| Person 2 | Chu Bá Tuấn Anh    |
| Person 3 | Nguyễn Mai Phương  |
| Person 4 | Hứa Quang Linh     |
| Person 5 | Nguyễn Thị Tuyết   |
| Person 6 | Nguyễn Văn Lĩnh    |

## 📊 Phân công công việc (Stream 1–6)

Mỗi sprint có **6 công việc song song**, mỗi người nhận 1 công việc/sprint. Công việc xoay vòng qua các sprint để tất cả có kinh nghiệm mọi phần của pipeline.

---

### **SPRINT 1 (0:00–1:00) — Indexing Setup**

| Person       | Task                                                                                                 | Output                                 |
| ------------ | ---------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **Person 1** | **Task 1A:** Load + analyze documents (5 files). Mô tả structure từng document.                      | Document analysis notes                |
| **Person 2** | **Task 1B:** Implement preprocessing + tokenizer. Clean text, normalize. Test với 1 doc.             | `preprocessing()` function             |
| **Person 3** | **Task 1C:** Implement chunking logic (sliding window/recursive). Test chunk size, overlap.          | `chunking()` function + chunk examples |
| **Person 4** | **Task 1D:** Design + implement metadata extraction (source, section, effective_date, thêm 1 field). | Metadata schema + example              |
| **Person 5** | **Task 1E:** Implement embedding function (OpenAI hoặc Sentence Transformers). Test embed 1 chunk.   | `get_embedding()` function             |
| **Person 6** | **Task 1F:** Implement ChromaDB storage + `build_index()`. Upsert all chunks. Test `list_chunks()`.  | ChromaDB integration + verify index    |

**Sprint 1 Definition of Done:**
- [ ] All 6 tasks có function chạy được
- [ ] Full `index.py` integrate từ 1A → 1F hoàn chỉnh
- [ ] Test: `python index.py` → ChromaDB index đủ 5 docs, mỗi chunk có 4+ metadata fields

---

### **SPRINT 2 (1:00–2:00) — Baseline RAG (Retrieval + Generation)**

| Person       | Task                                                                                                                         | Output                                     |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **Person 1** | **Task 2A:** Implement `retrieve_dense()` — query ChromaDB, return top_k chunks. Config params (top_k, threshold).           | `retrieve_dense()` function + test queries |
| **Person 2** | **Task 2B:** Implement `format_context()` — format retrieved chunks thành readable context string. Add `[1]`, `[2]` markers. | Context formatter function                 |
| **Person 3** | **Task 2C:** Implement `call_llm()` — gọi OpenAI/Gemini model. Pass system_prompt + context + query. Handle API errors.      | `call_llm()` function + error handling     |
| **Person 4** | **Task 2D:** Design + implement system_prompt. Yêu cầu: trả lời từ context, cite sources, abstain nếu không biết.            | System prompt v1 (baseline)                |
| **Person 5** | **Task 2E:** Integrate 2A+2B+2C+2D → `rag_answer()` main function. Test với 3+ test queries.                                 | End-to-end `rag_answer()` function         |
| **Person 6** | **Task 2F:** Test citation & abstention logic. Verify: có citation `[1]` không? Mơ hồ → abstain?                             | Test report: 10 test queries results       |

**Sprint 2 Definition of Done:**
- [ ] `python rag_answer.py` chạy 10 test queries không crash
- [ ] Output có citation + abstention logic hoạt động
- [ ] All 6 functions merge vào 1 file chạy được

---

### **SPRINT 3 (2:00–3:00) — Tuning (Retrieval hoặc Generation)**

Mỗi người chọn **1 trong 3 retrieval variants** hoặc **prompt variant**, implement + A/B test.

| Person       | Task                                                                                                                                                   | Output                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| **Person 1** | **Task 3A:** Implement Hybrid Retrieval (dense + BM25 sparse). API: `retrieve_hybrid()`.                                                               | Hybrid retrieve function + test     |
| **Person 2** | **Task 3B:** Implement Reranking (CrossEncoder). Load model, rerank top 10 → top 3. API: `rerank()`.                                                   | Rerank function + test              |
| **Person 3** | **Task 3C:** Implement Query Expansion (alias + synonym expansion). Test "SLA P1" → expand variants. API: `expand_query()`.                            | Query expansion function + examples |
| **Person 4** | **Task 3D:** Design + implement Prompt Variant v2 (e.g., JSON format / few-shot / detailed). Test faithfulness.                                        | System prompt v2 + comparison       |
| **Person 5** | **Task 3E:** Compare baseline vs variant (từ Person 1–4 tasks) trên 10 test questions. Score metrics: Context Recall, Faithfulness, Citation Accuracy. | Comparison table + delta scores     |
| **Person 6** | **Task 3F:** Write tuning decision rationale. Giải thích tại sao chọn variant nào, bằng chứng là metrics nào. Ghi vào notes.                           | Tuning decision doc + justification |

**Sprint 3 Definition of Done:**
- [ ] **Ít nhất 1 variant** (3A hoặc 3B hoặc 3C hoặc 3D) chạy được, tốt nhất chọn 1–2 variants từ người khác
- [ ] A/B comparison table có metrics rõ ràng (Person 3E)
- [ ] Tuning decision ghi trong notes (Person 3F) → sau ghi vào `docs/tuning-log.md`

---

### **SPRINT 4 (3:00–4:00) — Evaluation + Documentation + Reports**

| Person       | Task                                                                                                                                        | Output                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Person 1** | **Task 4A:** Prepare test_questions.json — verify 10 questions đủ, có expected_answer + expected_sources. Expand nếu thiếu.                 | Final `data/test_questions.json`               |
| **Person 2** | **Task 4B:** Run full grading: baseline config, 10 questions, score Context Recall + Faithfulness. Fill `results/scorecard_baseline.md`.    | `scorecard_baseline.md` (complete)             |
| **Person 3** | **Task 4C:** Run full grading: variant config, 10 questions, score metrics. Fill `results/scorecard_variant.md`.                            | `scorecard_variant.md` (complete)              |
| **Person 4** | **Task 4D:** A/B Delta Analysis — compare baseline vs variant. Calculate % improvement, identify pros/cons. Create `logs/grading_run.json`. | `grading_run.json` + delta summary             |
| **Person 5** | **Task 4E:** Write `docs/architecture.md` — pipeline overview, indexing config, retrieval config, generation config, evaluation metrics.    | `docs/architecture.md` (complete)              |
| **Person 6** | **Task 4F:** Write `docs/tuning-log.md` + `reports/group_report.md`. Consolidate tuning decision + results + lessons learned.               | `tuning-log.md` + `group_report.md` (complete) |

**Sprint 4 Definition of Done:**
- [ ] All scorecard + logs files complete + merged
- [ ] Both docs files (`architecture.md` + `tuning-log.md`) complete
- [ ] Group report complete

**Individual Reports (Mỗi người viết sau 18:00):**
- Mỗi person viết `reports/individual/[tên].md` (500–800 từ)
- Content: Công việc → Technical Contribution → Challenges & Solutions → Learnings → Reflection

---

## ⏰ Timeline & Commits

| Sprint            | Person 1 | Person 2       | Person 3        | Person 4      | Person 5     | Person 6            | Sync Point                   |
| ----------------- | -------- | -------------- | --------------- | ------------- | ------------ | ------------------- | ---------------------------- |
| **1 (0:00–1:00)** | Analysis | Preprocessing  | Chunking        | Metadata      | Embedding    | Index               | `index.py` ready @ 1:00      |
| **2 (1:00–2:00)** | Retrieve | Format         | LLM Call        | System Prompt | Integration  | Testing             | `rag_answer.py` ready @ 2:00 |
| **3 (2:00–3:00)** | Hybrid   | Rerank         | Query Transform | Prompt v2     | A/B Compare  | Tuning Doc          | Variant ready + notes @ 3:00 |
| **4 (3:00–4:00)** | Test Qs  | Baseline Score | Variant Score   | A/B Delta     | Architecture | Tuning-log + Report | All docs ready @ 4:00        |

---

## 🔄 Commit Strategy (Mỗi người commit ít nhất 1 lần/sprint)

**Sprint 1 @ 1:00:**
```bash
git commit -m "Sprint 1: index.py — preprocessing, chunking, embedding, metadata, storage
- Person 1: document analysis
- Person 2: preprocessing
- Person 3: chunking
- Person 4: metadata schema
- Person 5: embedding integration
- Person 6: ChromaDB storage & build_index()"
```

**Sprint 2 @ 2:00:**
```bash
git commit -m "Sprint 2: rag_answer.py — baseline retrieval & generation
- Person 1: retrieve_dense()
- Person 2: context formatting
- Person 3: call_llm()
- Person 4: system_prompt v1
- Person 5: rag_answer() end-to-end
- Person 6: citation & abstention tests"
```

**Sprint 3 @ 3:00:**
```bash
git commit -m "Sprint 3: tuning — [Hybrid/Rerank/Query Transform/Prompt v2]
- Person 1: [if variant chosen]
- Person 2: [if variant chosen]
- Person 3: [if variant chosen]
- Person 4: [if variant chosen]
- Person 5: A/B comparison & metrics
- Person 6: tuning rationale & notes"
```

**Sprint 4 @ 4:00:**
```bash
git commit -m "Sprint 4: evaluation & documentation
- Person 1: test_questions.json finalized
- Person 2: scorecard_baseline.md
- Person 3: scorecard_variant.md
- Person 4: grading_run.json & A/B analysis
- Person 5: docs/architecture.md
- Person 6: docs/tuning-log.md & reports/group_report.md"
```

**After 18:00 (Individual Reports):**
```bash
git commit -m "Individual Reports — All 6 members
- reports/individual/person1.md
- reports/individual/person2.md
- reports/individual/person3.md
- reports/individual/person4.md
- reports/individual/person5.md
- reports/individual/person6.md"
```

---

## ✅ Mỗi người có trách nhiệm

**Mọi sprint:**
- [ ] Hiểu code của người khác (code review nhẹ)
- [ ] Communicate khi có blocker (Slack / Discord)
- [ ] Commit ít nhất 1 lần/sprint với message rõ ràng
- [ ] Viết 1 individual report (500–800 từ) sau 18:00

**Khi xong task sớm:**
- Hỗ trợ người khác hoặc review code
- Không chờ passive, tìm việc thêm

---

## 🔗 File Nộp Bài (Organized by Sprint)

```
lab/
├── [SPRINT 1 Output]
│   └── index.py                          (6 người contribute)
│
├── [SPRINT 2 Output]
│   └── rag_answer.py                     (6 người contribute)
│
├── [SPRINT 3 Output — Variant]
│   └── rag_answer.py (updated)           (4 người tuning + 2 người support)
│
├── [SPRINT 4 Output — Eval & Docs]
│   ├── eval.py
│   ├── data/test_questions.json          (Person 1 @ Sprint 4)
│   ├── logs/grading_run.json             (Person 4 @ Sprint 4)
│   ├── results/
│   │   ├── scorecard_baseline.md         (Person 2 @ Sprint 4)
│   │   └── scorecard_variant.md          (Person 3 @ Sprint 4)
│   ├── docs/
│   │   ├── architecture.md               (Person 5 @ Sprint 4)
│   │   └── tuning-log.md                 (Person 6 @ Sprint 4)
│   └── reports/
│       ├── group_report.md               (Person 6 @ Sprint 4)
│       └── individual/
│           ├── person1.md                (After 18:00)
│           ├── person2.md
│           ├── person3.md
│           ├── person4.md
│           ├── person5.md
│           └── person6.md
```

---

## ⚡ Tips Để Collaboration Suôn Sẻ

1. **Setup Google Doc** để track notes real-time (chiến lược chunk, metrics, variant choice)
2. **30' check-in:**
   - 0:30 — Lưu các function từ Sprint 1 task A–E
   - 1:30 — Merge code Sprint 1 → 2
   - 2:30 — Config tuning ready
   - 3:30 — Merge docs, final check

3. **Parallel work:**
   - Sprint 1: Person 1–6 độc lập (không phụ thuộc)
   - Sprint 2: Person 1 + 5 integrate từ Sprint 1, person 2–4 code, person 6 test
   - Sprint 3: Chọn variant, Person 5 chạy A/B parallel
   - Sprint 4: Person 4 chạy grading parallel, Person 5–6 viết docs

4. **Debug Tree:** Nếu fail, kiểm tra từ Indexing → Retrieval → Generation

5. **Lưu ý:**
   - Chunk size, embedding model, LLM model **lock after Sprint 1** (không đổi)
   - Variant (tuning) **chọn 1 cái duy nhất** ở Sprint 3
   - Test questions **fixed sau Sprint 1**

---

## ✅ Checklist Trước Nộp (30' cuối)

**Code (Deadline 18:00 — CHẶT):**
- [ ] `python index.py` — chạy không lỗi, index 5 docs
- [ ] `python rag_answer.py` — retrieve + generate 10 test queries
- [ ] `python eval.py` — chạy 10 test_questions không crash
- [ ] Commit tất cả file `.py`, `logs/grading_run.json`, `results/*.md`

**Docs (Deadline 18:00 — CHẶT):**
- [ ] `docs/architecture.md` — đầy đủ 3 section (indexing, retrieval, generation)
- [ ] `docs/tuning-log.md` — có bảng so sánh + kết luận rõ ràng
- [ ] Commit docs

**Reports (Deadline LINH HOẠT — sau 18:00 OK):**
- [ ] `reports/group_report.md` — 500–800 từ
- [ ] `reports/individual/[6 tên].md` — mỗi file 500–800 từ
- [ ] Nộp reports trong 1 giờ sau deadline code

---

**Good luck! 🚀**

Ngày chuẩn bị: 2026-04-13  
Ngày nộp: 2026-04-13 (18:00 code + log, sau 18:00 reports)
