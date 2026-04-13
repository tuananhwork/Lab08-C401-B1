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
        client = chromadb.PersistentClient(path=str(os.getenv("CHROMA_DB_DIR", "chroma_db")))
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

    TODO Sprint 3 (nếu chọn hybrid):
    1. Cài rank_bm25: pip install rank-bm25
    2. Load tất cả chunks từ ChromaDB (hoặc rebuild từ docs)
    3. Tokenize và tạo BM25Index
    4. Query và trả về top_k kết quả

    Gợi ý:
        from rank_bm25 import BM25Okapi
        corpus = [chunk["text"] for chunk in all_chunks]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    """
    # TODO Sprint 3: Implement BM25 search
    # Tạm thời return empty list
    print("[retrieve_sparse] Chưa implement — Sprint 3")
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

    Mạnh ở: giữ được cả nghĩa (dense) lẫn keyword chính xác (sparse)
    Phù hợp khi: corpus lẫn lộn ngôn ngữ tự nhiên và tên riêng/mã lỗi/điều khoản

    Args:
        dense_weight: Trọng số cho dense score (0-1)
        sparse_weight: Trọng số cho sparse score (0-1)

    TODO Sprint 3 (nếu chọn hybrid):
    1. Chạy retrieve_dense() → dense_results
    2. Chạy retrieve_sparse() → sparse_results
    3. Merge bằng RRF:
       RRF_score(doc) = dense_weight * (1 / (60 + dense_rank)) +
                        sparse_weight * (1 / (60 + sparse_rank))
       60 là hằng số RRF tiêu chuẩn
    4. Sort theo RRF score giảm dần, trả về top_k

    Khi nào dùng hybrid (từ slide):
    - Corpus có cả câu tự nhiên VÀ tên riêng, mã lỗi, điều khoản
    - Query như "Approval Matrix" khi doc đổi tên thành "Access Control SOP"
    """
    # TODO Sprint 3: Implement hybrid RRF
    # Tạm thời fallback về dense
    print("[retrieve_hybrid] Chưa implement RRF — fallback về dense")
    return retrieve_dense(query, top_k)


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder.

    Cross-encoder: chấm lại "chunk nào thực sự trả lời câu hỏi này?"
    MMR (Maximal Marginal Relevance): giữ relevance nhưng giảm trùng lặp

    Funnel logic (từ slide):
      Search rộng (top-20) → Rerank (top-6) → Select (top-3)

    TODO Sprint 3 (nếu chọn rerank):
    Option A — Cross-encoder:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [[query, chunk["text"]] for chunk in candidates]
        scores = model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in ranked[:top_k]]

    Option B — Rerank bằng LLM (đơn giản hơn nhưng tốn token):
        Gửi list chunks cho LLM, yêu cầu chọn top_k relevant nhất

    Khi nào dùng rerank:
    - Dense/hybrid trả về nhiều chunk nhưng có noise
    - Muốn chắc chắn chỉ 3-5 chunk tốt nhất vào prompt
    """
    # TODO Sprint 3: Implement rerank
    # Tạm thời trả về top_k đầu tiên (không rerank)
    return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries
      - "hyde": Sinh câu trả lời giả (hypothetical document) để embed thay query

    TODO Sprint 3 (nếu chọn query transformation):
    Gọi LLM với prompt phù hợp với từng strategy.

    Ví dụ expansion prompt:
        "Given the query: '{query}'
         Generate 2-3 alternative phrasings or related terms in Vietnamese.
         Output as JSON array of strings."

    Ví dụ decomposition:
        "Break down this complex query into 2-3 simpler sub-queries: '{query}'
         Output as JSON array."

    Khi nào dùng:
    - Expansion: query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    - Decomposition: query hỏi nhiều thứ một lúc
    - HyDE: query mơ hồ, search theo nghĩa không hiệu quả
    """
    # TODO Sprint 3: Implement query transformation
    # Tạm thời trả về query gốc
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
# Thay đổi ở Sprint 3 Task 3D sẽ tạo SYSTEM_PROMPT_V2 riêng, không sửa biến này.
SYSTEM_PROMPT_V1 = """You are a helpful enterprise internal assistant.
Answer employee questions using ONLY the retrieved documents listed in the context.

Rules:
1. EVIDENCE ONLY: Use only information explicitly stated in the context. Do not add external knowledge or make assumptions.
2. CITATION (mandatory): After every factual claim, cite the source number in brackets, e.g. [1] or [1][2]. Never make a claim without a citation.
3. ABSTAIN: If the context does not contain enough information, respond exactly: "Toi khong tim thay thong tin nay trong tai lieu noi bo."
4. LANGUAGE: Reply in the same language as the question (Vietnamese question → Vietnamese answer).
5. CONCISE: 1–5 sentences max, or a short bullet list when listing multiple items."""


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
    }

    # --- Bước 1: Retrieve ---
    if retrieval_mode == "dense":
        candidates = retrieve_dense(query, top_k=top_k_search)
    elif retrieval_mode == "sparse":
        candidates = retrieve_sparse(query, top_k=top_k_search)
    elif retrieval_mode == "hybrid":
        candidates = retrieve_hybrid(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

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

    # --- Bước 3: Build context và prompt ---
    context_block = format_context(candidates, include_scores=True, include_metadata=True)
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
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid"]  # Thêm "sparse" sau khi implement

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Sprint 2 Task 2B: Test format_context()
    test_format_context(verbose=True)

    # Sprint 2 Task 2A: Test retrieve_dense()
    test_retrieve_dense(verbose=True)

    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("""
Sprint 2 Task 2B Deliverables:
  ✓ format_context() function implemented and tested
  ✓ Citation markers [1], [2], ... cho mỗi chunk
  ✓ Metadata display (source, section, score)
  ✓ Test với mock chunks và real retrieved chunks

To proceed to Task 2C (call_llm):
  - Person 3 sẽ implement LLM call function
  - Cần OPENAI_API_KEY hoặc GOOGLE_API_KEY

Dependencies:
  - Đảm bảo ChromaDB index đã được build từ Sprint 1
  - Đảm bảo index.py's get_embedding() đã implement
  - CHROMA_DB_DIR environment variable hoặc $PWD/chroma_db
""")

