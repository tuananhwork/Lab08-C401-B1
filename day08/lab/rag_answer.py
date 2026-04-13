"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(
    query: str, 
    top_k: int = TOP_K_SEARCH,
    threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.

    Args:
        query: Câu hỏi của người dùng
        top_k: Số chunk tối đa trả về
        threshold: Điểm similarity tối thiểu (0-1). Chunks dưới threshold bị lọc bỏ.
                  Gợi ý: 0.0 (không filter) → 0.5 (filter mạnh)

    Returns:
        List các dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata (source, section, effective_date, ...)
          - "score": cosine similarity score (0-1)

    Sprint 2 Implementation:
    1. Embed query bằng cùng model đã dùng khi index (từ index.py)
    2. Query ChromaDB với embedding đó
    3. Convert distance → similarity (1 - distance for cosine)
    4. Filter theo threshold và trả về top_k kết quả đã sắp xếp
    """
    try:
        import chromadb
        from index import get_embedding, CHROMA_DB_DIR
    except ImportError as e:
        print(f"❌ Error import: {e}")
        return []

    try:
        # Khởi tạo ChromaDB client
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")

        # Embed query
        query_embedding = get_embedding(query)
        
        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Format kết quả: convert distance → similarity
        # ChromaDB cosine distance: distance = 1 - similarity
        # Vậy: similarity = 1 - distance
        retrieved_chunks = []
        
        if results and results["documents"] and len(results["documents"]) > 0:
            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ):
                similarity_score = 1 - distance  # Convert distance to similarity
                
                # Filter theo threshold
                if similarity_score >= threshold:
                    retrieved_chunks.append({
                        "text": doc,
                        "metadata": metadata,
                        "score": round(similarity_score, 4),
                    })
        
        return retrieved_chunks

    except Exception as e:
        if "does not exist" in str(e) and "rag_lab" in str(e):
            print(
                "❌ Error retrieving dense: Collection [rag_lab] does not exist. "
                "Hãy chạy build_index() trong index.py trước."
            )
        else:
            print(f"❌ Error retrieving dense: {e}")
        return []


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    Sprint 3 (Task 3A — Person 1): Implemented BM25 search.
    1. Load tất cả chunks từ ChromaDB
    2. Tokenize corpus + query
    3. BM25Okapi scoring
    4. Return top_k results với metadata
    """
    try:
        import chromadb
        from rank_bm25 import BM25Okapi
        from index import CHROMA_DB_DIR
    except ImportError as e:
        print(f"[retrieve_sparse] Missing dependency: {e}")
        print("  → pip install rank-bm25")
        return []

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")

        # Load all chunks from ChromaDB
        all_data = collection.get(include=["documents", "metadatas"])
        if not all_data["documents"]:
            return []

        corpus = all_data["documents"]
        metadatas = all_data["metadatas"]

        # Tokenize corpus và query
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        tokenized_query = query.lower().split()

        # BM25 scoring
        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(tokenized_query)

        # Sort và lấy top_k
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Chỉ lấy chunks có score > 0
                results.append({
                    "text": corpus[idx],
                    "metadata": metadatas[idx],
                    "score": round(float(scores[idx]), 4),
                })

        return results

    except Exception as e:
        print(f"[retrieve_sparse] Error: {e}")
        return []


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).

    Sprint 3 (Task 3A — Person 1): Implemented RRF fusion.
    - dense_weight/sparse_weight: trọng số cho mỗi signal
    - RRF constant k=60 (standard)
    - Merge by text content as unique key
    """
    RRF_K = 60  # Hằng số RRF tiêu chuẩn

    # Lấy kết quả từ cả 2 retriever
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Nếu sparse trả về rỗng, fallback về dense
    if not sparse_results:
        return dense_results

    # Build RRF scores
    # Key = chunk text (unique identifier)
    rrf_scores = {}   # key → {"score": float, "chunk": dict}

    # Dense RRF scores
    for rank, chunk in enumerate(dense_results):
        key = chunk["text"][:200]  # Dùng 200 ký tự đầu làm key
        rrf_score = dense_weight * (1.0 / (RRF_K + rank + 1))
        if key not in rrf_scores:
            rrf_scores[key] = {"score": 0.0, "chunk": chunk}
        rrf_scores[key]["score"] += rrf_score

    # Sparse RRF scores
    for rank, chunk in enumerate(sparse_results):
        key = chunk["text"][:200]
        rrf_score = sparse_weight * (1.0 / (RRF_K + rank + 1))
        if key not in rrf_scores:
            rrf_scores[key] = {"score": 0.0, "chunk": chunk}
        rrf_scores[key]["score"] += rrf_score

    # Sort by RRF score descending
    sorted_items = sorted(
        rrf_scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    # Return top_k với RRF score thay thế
    results = []
    for item in sorted_items[:top_k]:
        chunk = item["chunk"].copy()
        chunk["score"] = round(item["score"], 6)
        results.append(chunk)

    return results


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

# Cache cross-encoder model để không load lại mỗi lần gọi
_cross_encoder_model = None

def _get_cross_encoder():
    """Lazy-load cross-encoder model (cache singleton)."""
    global _cross_encoder_model
    if _cross_encoder_model is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder_model


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder.

    Sprint 3 (Task 3B — Person 2): Implemented CrossEncoder reranking.
    - Model: cross-encoder/ms-marco-MiniLM-L-6-v2
    - Funnel: search rộng (top_k_search) → rerank → select (top_k)
    - Score mới từ cross-encoder thay thế score cũ
    """
    if not candidates:
        return []

    try:
        model = _get_cross_encoder()

        # Tạo query-document pairs
        pairs = [[query, chunk["text"]] for chunk in candidates]

        # Predict relevance scores
        scores = model.predict(pairs)

        # Sort by cross-encoder score (descending)
        ranked_pairs = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )

        # Return top_k với cross-encoder score
        results = []
        for chunk, ce_score in ranked_pairs[:top_k]:
            reranked = chunk.copy()
            reranked["score"] = round(float(ce_score), 4)
            reranked["rerank_score"] = round(float(ce_score), 4)
            results.append(reranked)

        return results

    except ImportError:
        print("[rerank] sentence-transformers not installed, falling back to truncation")
        return candidates[:top_k]
    except Exception as e:
        print(f"[rerank] Error: {e}, falling back to truncation")
        return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

# =============================================================================
# QUERY ALIAS MAP — Sprint 3 Task 3C (Person 3)
# Bảng alias/synonym cho các thuật ngữ trong corpus
# =============================================================================
QUERY_ALIAS_MAP = {
    # Access Control aliases
    "approval matrix": ["access control sop", "kiểm soát truy cập", "cấp quyền"],
    "access control": ["kiểm soát truy cập", "cấp quyền hệ thống", "approval matrix"],
    "cấp quyền": ["access control", "truy cập hệ thống", "approval matrix"],
    # SLA aliases
    "sla": ["service level agreement", "quy định xử lý sự cố", "thời gian phản hồi"],
    "sla p1": ["ticket p1", "sự cố critical", "sự cố khẩn cấp", "p1 critical"],
    "p1": ["critical", "khẩn cấp", "sự cố nghiêm trọng", "priority 1"],
    "escalation": ["leo thang", "chuyển cấp", "tự động escalate"],
    # Refund aliases
    "hoàn tiền": ["refund", "trả tiền", "hoàn trả"],
    "refund": ["hoàn tiền", "hoàn trả", "trả lại tiền"],
    # HR aliases
    "nghỉ phép": ["leave", "annual leave", "phép năm"],
    "remote": ["làm việc từ xa", "work from home", "wfh"],
    "overtime": ["làm thêm giờ", "tăng ca", "OT"],
    # IT Helpdesk aliases
    "mật khẩu": ["password", "đăng nhập", "reset password"],
    "vpn": ["kết nối từ xa", "cisco anyconnect", "remote connection"],
    "tài khoản bị khóa": ["account locked", "đăng nhập sai", "khóa tài khoản"],
}


def expand_query(query: str) -> List[str]:
    """
    Mở rộng query bằng alias/synonym mapping.

    Sprint 3 (Task 3C — Person 3): Static alias expansion.
    - Lookup từ khóa trong query → thêm alias variants
    - Test: "SLA P1" → ["SLA P1", "ticket p1", "sự cố critical", ...]
    """
    expanded = [query]  # Luôn giữ query gốc

    query_lower = query.lower()
    for key, aliases in QUERY_ALIAS_MAP.items():
        if key in query_lower:
            for alias in aliases:
                # Tạo variant query bằng cách thay thế key bằng alias
                variant = query_lower.replace(key, alias)
                if variant != query_lower and variant not in expanded:
                    expanded.append(variant)

    return expanded


def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Sprint 3 (Task 3C — Person 3): Implemented expansion strategy.
    - "expansion": Dùng expand_query() với alias map
    - "decomposition": Tách query phức tạp (placeholder)
    - "hyde": Hypothetical document (placeholder)
    """
    if strategy == "expansion":
        return expand_query(query)
    # Placeholder cho các strategy khác
    return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

# =============================================================================
# CONTEXT FORMATTER — FORMAT RETRIEVED CHUNKS (Task 2B - Person 2)
# =============================================================================

def format_context(
    chunks: List[Dict[str, Any]],
    include_scores: bool = True,
    include_metadata: bool = True,
) -> str:
    """
    Format retrieved chunks thành readable context string với citation markers [1], [2], ...

    Args:
        chunks: List các chunks từ retrieval (mỗi chunk có "text", "metadata", "score")
        include_scores: Có hiển thị similarity score không
        include_metadata: Có hiển thị metadata (source, section) không

    Returns:
        Formatted context string để đưa vào LLM prompt

    Sprint 2 (Person 2 - Task 2B):
    - Format chunks thành readable string
    - Thêm citation markers [1], [2], ... cho mỗi chunk
    - Hiển thị metadata (source, section, score)
    - Giữ nguyên nội dung chunk để model có thể trích dẫn

    Example output:
        [1] policy/refund-v4.pdf | Điều 2: Điều kiện được hoàn tiền | score=0.85
        Khách hàng được quyền yêu cầu hoàn tiền khi đáp ứng...

        [2] sla_p1_2026.txt | SLA Response Times | score=0.78
        P1 tickets must be acknowledged within 15 minutes...
    """
    if not chunks:
        return "No relevant context found."

    context_parts = []
    
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        text = chunk.get("text", "").strip()
        score = chunk.get("score", 0)
        
        # Build header với citation marker
        # Citation marker luôn có: [1] source
        header_parts = []
        
        # Citation marker với source
        source = meta.get("source", "unknown")
        header_parts.append(f"[{i}] {source}")
        
        # Section (nếu có)
        section = meta.get("section", "")
        if section:
            header_parts.append(section)
        
        # Score (nếu được yêu cầu)
        if include_scores and score > 0:
            header_parts.append(f"score={score:.2f}")
        
        # Join header parts với " | "
        header = " | ".join(header_parts)
        
        # Format chunk: header + text
        context_parts.append(f"{header}\n{text}")
    
    # Join tất cả chunks với 2 dòng trống
    context = "\n\n".join(context_parts)
    
    return context


def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    
    Deprecated: Dùng format_context() thay thế.
    """
    return format_context(chunks, include_scores=True, include_metadata=True)


# System prompt v1 — Task 2D (Person 4)
SYSTEM_PROMPT_V1 = """You are a helpful enterprise internal assistant.
Answer employee questions using ONLY the retrieved documents listed in the context.

Rules:
1. EVIDENCE ONLY: Use only information explicitly stated in the context. Do not add external knowledge or make assumptions.
2. CITATION (mandatory): After every factual claim, cite the source number in brackets, e.g. [1] or [1][2]. Never make a claim without a citation.
3. ABSTAIN: If the context does not contain enough information, respond exactly: "Toi khong tim thay thong tin nay trong tai lieu noi bo."
4. LANGUAGE: Reply in the same language as the question (Vietnamese question → Vietnamese answer).
5. CONCISE: 1–5 sentences max, or a short bullet list when listing multiple items."""


# =============================================================================
# System prompt v2 — Sprint 3 Task 3D (Person 4)
# Detailed + few-shot examples → improve faithfulness & citation accuracy
# =============================================================================
SYSTEM_PROMPT_V2 = """Bạn là trợ lý nội bộ doanh nghiệp. Nhiệm vụ: trả lời câu hỏi nhân viên DỰA TRÊN DUY NHẤT các tài liệu trong phần Context bên dưới.

Quy tắc BẮT BUỘC:
1. CHỈ DÙNG BẰNG CHỨNG: Chỉ sử dụng thông tin có trong context. KHÔNG thêm kiến thức bên ngoài.
2. TRÍCH DẪN BẮT BUỘC: Sau MỖI nhận định, ghi nguồn trong ngoặc vuông [1], [2], hoặc [1][2]. Không có nhận định nào được thiếu trích dẫn.
3. TỪ CHỐI TRẢ LỜI: Nếu context KHÔNG ĐỦ thông tin, trả lời chính xác: "Tôi không tìm thấy thông tin này trong tài liệu nội bộ."
4. NGÔN NGỮ: Trả lời bằng tiếng Việt nếu câu hỏi bằng tiếng Việt.
5. NGẮN GỌN: 1–5 câu, hoặc bullet list ngắn.

Ví dụ minh họa:

--- Ví dụ 1 (có answer) ---
Question: SLA P1 phản hồi ban đầu bao lâu?
Context: [1] support/sla-p1-2026.pdf | SLA theo mức độ ưu tiên
Ticket P1: Phản hồi ban đầu (first response): 15 phút kể từ khi ticket được tạo.
Answer: SLA phản hồi ban đầu cho ticket P1 là 15 phút kể từ khi ticket được tạo [1].

--- Ví dụ 2 (abstain) ---
Question: Chính sách thưởng Tết là gì?
Context: [1] hr/leave-policy-2026.pdf | Các loại nghỉ phép
Nghỉ phép năm: 12 ngày/năm cho nhân viên dưới 3 năm.
Answer: Tôi không tìm thấy thông tin này trong tài liệu nội bộ.

--- Ví dụ 3 (partial info) ---
Question: Hoàn tiền VIP có khác gì không?
Context: [1] policy/refund-v4.pdf | Quy trình hoàn tiền
Tất cả yêu cầu hoàn tiền theo quy trình tiêu chuẩn: 3-5 ngày làm việc.
Answer: Theo tài liệu, tất cả yêu cầu hoàn tiền đều theo quy trình tiêu chuẩn 3-5 ngày làm việc [1]. Tài liệu không đề cập đến quy trình đặc biệt cho khách hàng VIP."""


def build_grounded_prompt_v2(query: str, context_block: str) -> str:
    """Build prompt v2 (Sprint 3 Task 3D) với few-shot examples."""
    return f"""{SYSTEM_PROMPT_V2}

Question: {query}

Context:
{context_block}

Answer:"""


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xay dung grounded prompt v1 (Task 2D — Person 4).

    Nhu cau:
    - Tra loi tu context, cite sources, abstain neu khong biet
    - Tuong thich voi call_llm(prompt: str) cua Person 3

    Sprint 3: tao build_grounded_prompt_v2() rieng de A/B test,
    khong sua ham nay.
    """
    return f"""{SYSTEM_PROMPT_V1}

Question: {query}

Context:
{context_block}

Answer:"""


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời dựa trên prompt đã được build sẵn.

    Thứ tự ưu tiên:
      1. OpenAI (nếu có OPENAI_API_KEY)
      2. Google Gemini (nếu có GOOGLE_API_KEY)
    Nếu không có key nào → raise EnvironmentError rõ ràng.

    Args:
        prompt: Full prompt đã bao gồm system instruction + context + query.

    Returns:
        Chuỗi câu trả lời từ LLM.

    Sprint 2 (Person 3 - Task 2C):
    - temperature=0 để output ổn định, dễ đánh giá
    - max_tokens=512 đủ cho câu trả lời ngắn có citation
    - Xử lý lỗi API: rate limit, network, auth → trả về thông báo rõ ràng
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()

    # ── Option A: OpenAI ──────────────────────────────────────────────────────
    if openai_key:
        try:
            from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError

            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=512,
            )
            return response.choices[0].message.content.strip()

        except AuthenticationError:
            raise EnvironmentError("OPENAI_API_KEY không hợp lệ hoặc hết hạn.")
        except RateLimitError:
            raise RuntimeError("OpenAI rate limit — thử lại sau vài giây.")
        except APIConnectionError as e:
            raise RuntimeError(f"Không kết nối được đến OpenAI: {e}")
        except APIError as e:
            raise RuntimeError(f"OpenAI API lỗi ({e.status_code}): {e.message}")

    # ── Option B: Google Gemini ───────────────────────────────────────────────
    if google_key:
        try:
            import google.generativeai as genai
            from google.api_core.exceptions import (
                PermissionDenied, ResourceExhausted, GoogleAPICallError
            )

            genai.configure(api_key=google_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            gemini_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0,
                    max_output_tokens=512,
                ),
            )
            response = gemini_model.generate_content(prompt)
            return response.text.strip()

        except PermissionDenied:
            raise EnvironmentError("GOOGLE_API_KEY không hợp lệ hoặc không có quyền.")
        except ResourceExhausted:
            raise RuntimeError("Gemini quota đã hết — thử lại sau.")
        except GoogleAPICallError as e:
            raise RuntimeError(f"Gemini API lỗi: {e}")

    # ── Không có key nào ─────────────────────────────────────────────────────
    raise EnvironmentError(
        "Cần ít nhất một trong hai: OPENAI_API_KEY hoặc GOOGLE_API_KEY trong file .env"
    )


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    prompt_version: str = "v1",
    use_query_expansion: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "prompt_version": prompt_version,
        "use_query_expansion": use_query_expansion,
    }

    # --- Bước 0.5: Query expansion (Sprint 3 Task 3C) ---
    if use_query_expansion:
        expanded = expand_query(query)
        if verbose and len(expanded) > 1:
            print(f"[RAG] Query expanded: {expanded}")
    else:
        expanded = [query]

    # --- Bước 1: Retrieve ---
    all_candidates = []
    for q in expanded:
        if retrieval_mode == "dense":
            all_candidates.extend(retrieve_dense(q, top_k=top_k_search))
        elif retrieval_mode == "sparse":
            all_candidates.extend(retrieve_sparse(q, top_k=top_k_search))
        elif retrieval_mode == "hybrid":
            all_candidates.extend(retrieve_hybrid(q, top_k=top_k_search))
        else:
            raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    # Deduplicate by text content, keep highest score
    seen = {}
    for c in all_candidates:
        key = c["text"][:200]
        if key not in seen or c.get("score", 0) > seen[key].get("score", 0):
            seen[key] = c
    candidates = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # Sprint 2 integration guard:
    # Nếu retrieval không trả về context thì abstain ngay, không gọi LLM.
    if not candidates:
        abstain_message = "Toi khong tim thay thong tin nay trong tai lieu noi bo."
        return {
            "query": query,
            "answer": abstain_message,
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

    # --- Bước 3: Build context và prompt ---
    context_block = format_context(candidates, include_scores=True, include_metadata=True)
    # Sprint 3: Chọn prompt version
    if prompt_version == "v2":
        prompt = build_grounded_prompt_v2(query, context_block)
    else:
        prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 2: TEST FORMAT_CONTEXT (Person 2 Task 2B)
# =============================================================================

def test_format_context(verbose: bool = True) -> None:
    """
    Test format_context() function với mock retrieved chunks.

    Output: Formatted context string với citation markers.

    Task 2B Deliverable: `format_context()` function + test
    """
    print("\n" + "="*70)
    print("SPRINT 2 — Task 2B: Test format_context()")
    print("="*70)

    # Mock chunks từ retrieval
    mock_chunks = [
        {
            "text": "Khách hàng được quyền yêu cầu hoàn tiền khi đáp ứng đủ các điều kiện sau:\n- Sản phẩm bị lỗi do nhà sản xuất\n- Yêu cầu trong vòng 7 ngày làm việc\n- Đơn hàng chưa được sử dụng",
            "metadata": {
                "source": "policy/refund-v4.pdf",
                "section": "Điều 2: Điều kiện được hoàn tiền",
                "department": "CS",
                "effective_date": "2026-02-01",
            },
            "score": 0.8542,
        },
        {
            "text": "P1 tickets must be acknowledged within 15 minutes.\nResponse time: 1 hour maximum.\nResolution target: 4 hours.",
            "metadata": {
                "source": "sla_p1_2026.txt",
                "section": "SLA Response Times",
                "department": "IT",
                "effective_date": "2026-01-01",
            },
            "score": 0.7823,
        },
        {
            "text": "Access Level 3 requires approval from Department Head.\nRegular users can only access Level 1 by default.\nLevel 2 requires Team Lead approval.",
            "metadata": {
                "source": "access_control_sop.txt",
                "section": "Access Levels",
                "department": "IT",
                "effective_date": "2026-01-15",
            },
            "score": 0.6915,
        },
    ]

    print("\n--- Test 1: Full format (với scores) ---")
    context_full = format_context(mock_chunks, include_scores=True, include_metadata=True)
    print(context_full)

    print("\n\n--- Test 2: Minimal format (không scores) ---")
    context_minimal = format_context(mock_chunks, include_scores=False, include_metadata=True)
    print(context_minimal)

    print("\n\n--- Test 3: Empty chunks ---")
    context_empty = format_context([])
    print(f"Result: '{context_empty}'")

    print("\n\n--- Test 4: Integration với retrieve_dense() ---")
    print("Đang test với retrieved chunks thực tế...\n")
    
    try:
        # Thử retrieve 1 query và format context
        test_query = "Điều kiện hoàn tiền là gì?"
        retrieved_chunks = retrieve_dense(test_query, top_k=3)
        
        if retrieved_chunks:
            print(f"Query: {test_query}")
            print(f"Retrieved {len(retrieved_chunks)} chunks\n")
            
            formatted = format_context(retrieved_chunks, include_scores=True)
            print("Formatted context:")
            print("-" * 70)
            print(formatted[:800] + "..." if len(formatted) > 800 else formatted)
            print("-" * 70)
        else:
            print("⚠️  Không có chunks nào retrieved (ChromaDB chưa build?)")
            
    except Exception as e:
        print(f"⚠️  Không thể test với retrieval: {e}")

    print("\n" + "="*70)
    print("✓ Task 2B hoàn thành: format_context() hoạt động tốt")
    print("="*70)


# =============================================================================
# SPRINT 2: TEST RETRIEVE_DENSE (Person 1 Task 2A)
# =============================================================================

def test_retrieve_dense(verbose: bool = True) -> None:
    """
    Test retrieve_dense() function với các test queries.
    
    Output: Số chunk tìm được, relevance scores, metadata preview.
    
    Task 2A Deliverable: `retrieve_dense()` function + test queries
    """
    print("\n" + "="*70)
    print("SPRINT 2 — Task 2A: Test retrieve_dense()")
    print("="*70)
    
    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "Tài khoản bị khóa sau bao nhiêu lần đăng nhập sai?",
        "Escalation trong sự cố P1 diễn ra như thế nào?",
    ]
    
    print(f"\nTesting {len(test_queries)} queries với retrieve_dense():\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"[Query {i}] {query}")
        print("-" * 70)
        
        try:
            chunks = retrieve_dense(query, top_k=3, threshold=0.0)
            
            if not chunks:
                print("❌ No chunks retrieved (có thể ChromaDB chưa được build)")
            else:
                print(f"✓ Found {len(chunks)} chunks:\n")
                
                for j, chunk in enumerate(chunks, 1):
                    meta = chunk.get("metadata", {})
                    score = chunk.get("score", 0)
                    text_preview = chunk.get("text", "")[:100].replace("\n", " ")
                    
                    print(f"  [{j}] Score: {score:.4f}")
                    print(f"      Source: {meta.get('source', 'N/A')}")
                    print(f"      Section: {meta.get('section', 'N/A')}")
                    print(f"      Dept: {meta.get('department', 'N/A')}")
                    print(f"      Text: {text_preview}...")
                    print()
        
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
        
        print()


# =============================================================================
# SPRINT 2: TEST RAG ANSWER INTEGRATION (Person 5 Task 2E)
# =============================================================================

def test_rag_answer_integration(verbose: bool = True) -> None:
    """
    Test end-to-end rag_answer() theo đúng Task 2E (Person 5):
    integrate retrieval + context formatting + prompt + LLM call.

    Yêu cầu:
    - Chạy 3+ queries
    - Kiểm tra output có answer và sources
    """
    print("\n" + "="*70)
    print("SPRINT 2 — Task 2E: Test rag_answer() integration")
    print("="*70)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",
    ]

    for idx, query in enumerate(test_queries, 1):
        print(f"\n[Integration Query {idx}] {query}")
        print("-" * 70)
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=False)
            print(f"Answer: {result.get('answer', '')}")
            print(f"Sources: {result.get('sources', [])}")
            print(f"Chunks used: {len(result.get('chunks_used', []))}")
        except Exception as e:
            print(f"❌ Integration failed: {str(e)[:200]}")


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.
    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "sparse", "hybrid"]

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer'][:200]}..." if len(result.get('answer','')) > 200 else f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# SPRINT 3 TASK 3E: A/B COMPARISON (Person 5)
# =============================================================================

def ab_compare_baseline_vs_variant(
    test_questions_path: str = "data/test_questions.json",
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    So sánh Baseline (dense + prompt v1) vs Variant (hybrid + rerank + prompt v2 + query expansion)
    trên 10 test questions.

    Sprint 3 (Task 3E — Person 5):
    - Chạy cả baseline và variant config
    - Score: Context Recall, Faithfulness, Citation Accuracy (manual proxy)
    - Output: comparison table
    """
    import json

    # Load test questions
    try:
        with open(test_questions_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except FileNotFoundError:
        from pathlib import Path
        qpath = Path(__file__).parent / test_questions_path
        with open(qpath, "r", encoding="utf-8") as f:
            questions = json.load(f)

    baseline_config = {
        "retrieval_mode": "dense",
        "use_rerank": False,
        "prompt_version": "v1",
        "use_query_expansion": False,
    }
    variant_config = {
        "retrieval_mode": "hybrid",
        "use_rerank": True,
        "prompt_version": "v2",
        "use_query_expansion": True,
    }

    results = []

    if verbose:
        print("\n" + "="*80)
        print("SPRINT 3 — Task 3E: A/B Comparison — Baseline vs Variant")
        print("="*80)
        print(f"\nBaseline config: {baseline_config}")
        print(f"Variant config:  {variant_config}")
        print(f"Test questions:  {len(questions)}")
        print()

    for q in questions:
        qid = q["id"]
        query = q["question"]
        expected_sources = q.get("expected_sources", [])

        if verbose:
            print(f"\n--- [{qid}] {query} ---")

        row = {"id": qid, "question": query, "expected_sources": expected_sources}

        # --- Baseline ---
        try:
            b_result = rag_answer(query, **baseline_config, verbose=False)
            row["baseline_answer"] = b_result["answer"]
            row["baseline_sources"] = b_result["sources"]
            row["baseline_has_citation"] = "[1]" in b_result["answer"] or "[2]" in b_result["answer"]
            row["baseline_source_match"] = any(
                exp in str(b_result["sources"]) for exp in expected_sources
            ) if expected_sources else True
        except Exception as e:
            row["baseline_answer"] = f"ERROR: {e}"
            row["baseline_sources"] = []
            row["baseline_has_citation"] = False
            row["baseline_source_match"] = False

        # --- Variant ---
        try:
            v_result = rag_answer(query, **variant_config, verbose=False)
            row["variant_answer"] = v_result["answer"]
            row["variant_sources"] = v_result["sources"]
            row["variant_has_citation"] = "[1]" in v_result["answer"] or "[2]" in v_result["answer"]
            row["variant_source_match"] = any(
                exp in str(v_result["sources"]) for exp in expected_sources
            ) if expected_sources else True
        except Exception as e:
            row["variant_answer"] = f"ERROR: {e}"
            row["variant_sources"] = []
            row["variant_has_citation"] = False
            row["variant_source_match"] = False

        results.append(row)

        if verbose:
            print(f"  Baseline: {row['baseline_answer'][:120]}...")
            print(f"  Variant:  {row['variant_answer'][:120]}...")

    # --- Summary ---
    n = len(results)
    b_citation = sum(1 for r in results if r.get("baseline_has_citation"))
    v_citation = sum(1 for r in results if r.get("variant_has_citation"))
    b_source = sum(1 for r in results if r.get("baseline_source_match"))
    v_source = sum(1 for r in results if r.get("variant_source_match"))

    summary = {
        "total_questions": n,
        "baseline": {
            "citation_count": b_citation,
            "citation_rate": round(b_citation / n * 100, 1) if n else 0,
            "source_match_count": b_source,
            "source_match_rate": round(b_source / n * 100, 1) if n else 0,
        },
        "variant": {
            "citation_count": v_citation,
            "citation_rate": round(v_citation / n * 100, 1) if n else 0,
            "source_match_count": v_source,
            "source_match_rate": round(v_source / n * 100, 1) if n else 0,
        },
        "delta": {
            "citation_delta": round((v_citation - b_citation) / n * 100, 1) if n else 0,
            "source_match_delta": round((v_source - b_source) / n * 100, 1) if n else 0,
        },
        "details": results,
    }

    if verbose:
        print("\n" + "="*80)
        print("A/B COMPARISON SUMMARY")
        print("="*80)
        print(f"{'Metric':<25} {'Baseline':>12} {'Variant':>12} {'Delta':>12}")
        print("-"*65)
        print(f"{'Citation Rate':<25} {summary['baseline']['citation_rate']:>10.1f}% {summary['variant']['citation_rate']:>10.1f}% {summary['delta']['citation_delta']:>+10.1f}%")
        print(f"{'Source Match Rate':<25} {summary['baseline']['source_match_rate']:>10.1f}% {summary['variant']['source_match_rate']:>10.1f}% {summary['delta']['source_match_delta']:>+10.1f}%")
        print()

    return summary


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Sprint 2: Test format_context(), retrieve_dense(), integration
    test_format_context(verbose=True)
    test_retrieve_dense(verbose=True)
    test_rag_answer_integration(verbose=True)

    # Sprint 3: Test query expansion
    print("\n" + "="*70)
    print("SPRINT 3 — Task 3C: Test expand_query()")
    print("="*70)
    test_expansions = [
        "SLA P1",
        "Approval Matrix",
        "hoàn tiền",
        "VPN bị lỗi",
        "tài khoản bị khóa",
    ]
    for q in test_expansions:
        expanded = expand_query(q)
        print(f"  '{q}' → {expanded}")

    # Sprint 3: Compare retrieval strategies
    print("\n" + "="*70)
    print("SPRINT 3 — Task 3A/3B: Compare Strategies")
    print("="*70)
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")

    # Sprint 3 Task 3E: A/B comparison
    print("\n" + "="*70)
    print("SPRINT 3 — Task 3E: A/B Baseline vs Variant")
    print("="*70)
    try:
        summary = ab_compare_baseline_vs_variant(verbose=True)
    except Exception as e:
        print(f"A/B comparison error: {e}")

    print("\n" + "="*70)
    print("ALL SPRINT 2 + 3 TASKS COMPLETE")
    print("="*70)


