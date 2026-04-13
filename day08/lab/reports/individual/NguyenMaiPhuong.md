# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Mai Phương
**Vai trò trong nhóm:** Person 3 (Chunking, LLM call integration, Variant evaluation)
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab Day 08, tôi tập trung chính vào các phần của Person 3 theo từng sprint, đồng thời hỗ trợ debug khi nhóm gặp lỗi chạy pipeline. Ở Sprint 1, tôi triển khai logic chunking theo hướng ưu tiên ranh giới tự nhiên: tách theo section heading, sau đó ghép paragraph theo kích thước mục tiêu và thêm overlap để giữ ngữ cảnh giữa các chunk. Tôi cũng kiểm tra output chunk preview để đảm bảo metadata section vẫn được giữ đúng. Ở Sprint 2, tôi triển khai call_llm với cấu hình ổn định cho evaluation (temperature thấp), đồng thời bổ sung xử lý lỗi API để pipeline không crash khi gặp lỗi kết nối hoặc key. Ở Sprint 4, tôi phụ trách chạy variant scorecard và hoàn thiện scorecard_variant.md. Công việc của tôi kết nối trực tiếp với phần retrieval, vì chunking ảnh hưởng recall và call_llm ảnh hưởng chất lượng câu trả lời cuối cùng.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau lab này, tôi hiểu rõ hơn mối quan hệ nhân quả giữa retrieval và generation trong RAG. Trước đây tôi thường nghĩ vấn đề chính nằm ở prompt, nhưng khi làm thực tế tôi thấy nếu chunking và retrieval không tốt thì prompt tốt cũng không cứu được câu trả lời. Cụ thể, chunking không chỉ là “cắt đều theo số ký tự”, mà cần tôn trọng cấu trúc tài liệu để tránh mất ý nghĩa điều khoản. Tôi cũng hiểu rõ grounded answering là một ràng buộc kỹ thuật chứ không chỉ phong cách viết: model phải trả lời dựa trên context được retrieve, nếu không đủ dữ liệu thì cần abstain thay vì suy diễn. Ngoài ra, quá trình chấm 4 metrics giúp tôi nhìn rõ một mô hình có thể faithful cao nhưng completeness vẫn thấp, tức là trả lời đúng phần có bằng chứng nhưng chưa đủ độ bao phủ.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Khó khăn lớn nhất của tôi là giai đoạn debug tưởng như lỗi ở get_embedding nhưng thực ra nguyên nhân gốc lại nằm ở trạng thái index/collection. Nhóm gặp thông báo “Collection [rag_lab] does not exist”, và ban đầu tôi giả thuyết rằng lỗi do API embedding hoặc key môi trường. Sau khi kiểm tra theo từng lớp (import dependency, chạy thử get_embedding, build_index, rồi retrieve_dense), tôi xác nhận get_embedding hoạt động bình thường; vấn đề là collection chưa được build hoặc đang truy cập sai path ChromaDB theo working directory. Điều khiến tôi ngạc nhiên là cùng một code nhưng chạy bằng interpreter hoặc cwd khác nhau có thể cho cảm giác như lỗi ngẫu nhiên. Bài học rút ra là phải debug theo pipeline end-to-end, không kết luận quá sớm tại một hàm đơn lẻ.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q07 — “Approval Matrix để cấp quyền hệ thống là tài liệu nào?”

**Phân tích:**

Đây là câu hỏi tôi thấy thú vị vì nó kiểm tra khả năng mapping alias thuật ngữ trong retrieval. Trong baseline, điểm Relevance của q07 là 2/5, dù Faithfulness vẫn 5/5. Điều này cho thấy model vẫn bám vào context retrieve được nhưng câu trả lời chưa đúng trọng tâm câu hỏi “tài liệu nào”. Ở variant, Relevance tăng lên 5/5, trong khi Faithfulness vẫn giữ 5/5 và Recall giữ 5/5. Với kết quả này, tôi đánh giá cải thiện đến từ retrieval mode hybrid + rerank giúp ưu tiên đúng chunk chứa thông tin định danh tài liệu thay vì chỉ các đoạn liên quan chung về access control. Tuy nhiên Completeness của q07 vẫn ở mức 2/5 cho cả baseline và variant, nghĩa là câu trả lời đúng ý chính nhưng chưa bao phủ đủ các chi tiết phụ hoặc format chưa tối ưu theo expected answer. Như vậy, với q07, lỗi chính ở baseline nằm ở retrieval ranking và selection; variant đã sửa tốt phần chọn ngữ cảnh, nhưng generation vẫn cần cải thiện chiều sâu thông tin.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, tôi sẽ ưu tiên hai cải tiến cụ thể. Thứ nhất, thêm query expansion có kiểm soát cho các alias/domain term (ví dụ Approval Matrix, Elevated Access) để tăng khả năng match trong retrieval mà không làm nhiễu. Thứ hai, tinh chỉnh prompt generation theo dạng checklist bắt buộc các ý chính để kéo điểm Completeness lên, vì scorecard hiện cho thấy faithful cao nhưng completeness chưa ổn định ở một số câu. Tôi cũng muốn thêm logging per-step để truy vết lỗi nhanh hơn khi chạy multi-interpreter.

---

*Lưu file này với tên: reports/individual/[ten_ban].md*
*Ví dụ: reports/individual/nguyen_van_a.md*
