"""
index.py — Sprint 1: Build RAG Index
====================================
Mục tiêu Sprint 1 (60 phút):
  - Đọc và preprocess tài liệu từ data/docs/
  - Chunk tài liệu theo cấu trúc tự nhiên (heading/section)
  - Gắn metadata: source, section, department, effective_date, access
  - Embed và lưu vào vector store (ChromaDB)

Definition of Done Sprint 1:
  ✓ Script chạy được và index đủ docs
  ✓ Có ít nhất 3 metadata fields hữu ích cho retrieval
  ✓ Có thể kiểm tra chunk bằng list_chunks()
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# TODO Sprint 1: Điều chỉnh chunk size và overlap theo quyết định của nhóm
# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk


# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text: chuẩn hóa khoảng trắng, dấu câu, ký tự đặc biệt.
    
    Args:
        text: Text cần normalize
        
    Returns:
        Text đã được chuẩn hóa
    """
    # Chuẩn hóa khoảng trắng: xóa khoảng trắng thừa ở đầu/cuối dòng
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
    
    # Chuẩn hóa khoảng trắng giữa các từ: nhiều space → 1 space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Chuẩn hóa số dòng trống liên tiếp: max 2 dòng trống
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Xóa ký tự đặc biệt không cần thiết (giữ lại chữ cái, số, dấu câu tiếng Việt)
    # Giữ lại: a-z, A-Z, 0-9, chữ tiếng Việt có dấu, dấu câu cơ bản
    text = re.sub(r'[^\w\s\.\,\:\;\!\?\-\(\)\[\]\/\%\€\$₫\n]', '', text)
    
    return text.strip()


def tokenize_text(text: str) -> List[str]:
    """
    Tokenize text thành danh sách các token (words).
    Hỗ trợ tiếng Việt: tách theo khoảng trắng nhưng giữ nguyên từ ghép có dấu.
    
    Args:
        text: Text cần tokenize
        
    Returns:
        List các tokens
    """
    # Lowercase để normalize
    text_lower = text.lower()
    
    # Tách theo whitespace và lọc tokens rỗng
    tokens = text_lower.split()
    
    # Xóa punctuation ở đầu/cuối mỗi token
    tokens = [token.strip('.,;:!?"\'()[]{}') for token in tokens]
    
    # Lọc tokens rỗng sau khi strip
    tokens = [token for token in tokens if token]
    
    return tokens


def _infer_doc_type(source: str) -> str:
    """Infer doc_type từ source path (Task 1D — Person 4)."""
    s = source.lower()
    if "sop" in s:
        return "sop"
    if "faq" in s:
        return "faq"
    if "sla" in s:
        return "sla"
    if "policy" in s or "leave" in s or "refund" in s:
        return "policy"
    return "document"


def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess một tài liệu: extract metadata từ header, làm sạch và tokenize nội dung.

    Args:
        raw_text: Toàn bộ nội dung file text
        filepath: Đường dẫn file để làm source mặc định

    Returns:
        Dict chứa:
          - "text": nội dung đã clean
          - "metadata": dict với source, department, effective_date, access
          - "tokens": danh sách tokens (cho debugging/analysis)

    Sprint 1 (Person 2 - Task 1B):
    - Extract metadata từ dòng đầu file (Source, Department, Effective Date, Access)
    - Bỏ các dòng header metadata khỏi nội dung chính
    - Normalize khoảng trắng, xóa ký tự rác
    - Tokenize text thành words
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
        "doc_type": "document",   # Task 1D: infer sau khi parse source
    }
    content_lines = []
    header_done = False

    for line in lines:
        if not header_done:
            # Parse metadata từ các dòng "Key: Value"
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                # Gặp section heading đầu tiên → kết thúc header
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or (line.isupper() and len(line) > 3):
                # Dòng tên tài liệu (toàn chữ hoa) hoặc dòng trống
                continue
        else:
            content_lines.append(line)

    # Join và clean text
    cleaned_text = "\n".join(content_lines)

    # Task 1D: gán doc_type sau khi source đã được parse từ header
    metadata["doc_type"] = _infer_doc_type(metadata["source"])
    
    # Normalize text
    cleaned_text = normalize_text(cleaned_text)

    # Tokenize cho mục đích analysis
    tokens = tokenize_text(cleaned_text)

    return {
        "text": cleaned_text,
        "metadata": metadata,
        "tokens": tokens,
    }


# =============================================================================
# STEP 2: CHUNK
# Chia tài liệu thành các đoạn nhỏ theo cấu trúc tự nhiên
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk một tài liệu đã preprocess thành danh sách các chunk nhỏ.

    Args:
        doc: Dict với "text" và "metadata" (output của preprocess_document)

    Returns:
        List các Dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata gốc + "section" của chunk đó

    TODO Sprint 1:
    1. Split theo heading "=== Section ... ===" hoặc "=== Phần ... ===" trước
    2. Nếu section quá dài (> CHUNK_SIZE * 4 ký tự), split tiếp theo paragraph
    3. Thêm overlap: lấy đoạn cuối của chunk trước vào đầu chunk tiếp theo
    4. Mỗi chunk PHẢI giữ metadata đầy đủ từ tài liệu gốc

    Gợi ý: Ưu tiên cắt tại ranh giới tự nhiên (section, paragraph)
    thay vì cắt theo token count cứng.
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    heading_pattern = re.compile(r"^===\s*(.+?)\s*===\s*$")
    current_section = "General"
    buffer_lines: List[str] = []

    for line in text.splitlines():
        heading_match = heading_pattern.match(line.strip())
        if heading_match:
            if buffer_lines:
                section_text = "\n".join(buffer_lines).strip()
                if section_text:
                    chunks.extend(
                        _split_by_size(
                            section_text,
                            base_metadata=base_metadata,
                            section=current_section,
                        )
                    )
            current_section = heading_match.group(1).strip() or "General"
            buffer_lines = []
            continue

        buffer_lines.append(line)

    if buffer_lines:
        section_text = "\n".join(buffer_lines).strip()
        if section_text:
            chunks.extend(
                _split_by_size(
                    section_text,
                    base_metadata=base_metadata,
                    section=current_section,
                )
            )

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Helper: Split text dài thành chunks với overlap.

    TODO Sprint 1:
    Hiện tại dùng split đơn giản theo ký tự.
    Cải thiện: split theo paragraph (\n\n) trước, rồi mới ghép đến khi đủ size.
    """
    normalized = text.strip()
    if not normalized:
        return []

    if len(normalized) <= chunk_chars:
        return [{
            "text": normalized,
            "metadata": {**base_metadata, "section": section},
        }]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", normalized) if p.strip()]
    if not paragraphs:
        paragraphs = [normalized]

    chunks_text: List[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_chars:
            # Cắt paragraph quá dài theo ranh giới tự nhiên gần nhất.
            cursor = 0
            while cursor < len(para):
                target_end = min(cursor + chunk_chars, len(para))
                split_at = para.rfind(". ", cursor, target_end)
                if split_at == -1:
                    split_at = para.rfind("\n", cursor, target_end)
                if split_at == -1 or split_at <= cursor + int(chunk_chars * 0.6):
                    split_at = target_end
                else:
                    split_at += 1  # include punctuation

                part = para[cursor:split_at].strip()
                if part:
                    if current and len(current) + 2 + len(part) <= chunk_chars:
                        current = f"{current}\n\n{part}"
                    else:
                        if current:
                            chunks_text.append(current)
                        current = part
                cursor = split_at
            continue

        candidate = para if not current else f"{current}\n\n{para}"
        if len(candidate) <= chunk_chars:
            current = candidate
        else:
            if current:
                chunks_text.append(current)
            current = para

    if current:
        chunks_text.append(current)

    if len(chunks_text) <= 1:
        return [{
            "text": chunks_text[0],
            "metadata": {**base_metadata, "section": section},
        }]

    overlap_ready: List[Dict[str, Any]] = []
    previous_text = ""
    for chunk_text in chunks_text:
        chunk_text = chunk_text.strip()
        if previous_text:
            tail = previous_text[-overlap_chars:].strip()
            if tail and not chunk_text.startswith(tail):
                merged = f"{tail}\n\n{chunk_text}".strip()
                if len(merged) > int(chunk_chars * 1.25):
                    merged = merged[-int(chunk_chars * 1.25):].strip()
                chunk_text = merged

        overlap_ready.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })
        previous_text = chunk_text

    return overlap_ready


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.

    TODO Sprint 1:
    Chọn một trong hai:

    Option A — OpenAI Embeddings (cần OPENAI_API_KEY):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    Option B — Sentence Transformers (chạy local, không cần API key):
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return model.encode(text).tolist()
    """
    raise NotImplementedError(
        "TODO: Implement get_embedding().\n"
        "Chọn Option A (OpenAI) hoặc Option B (Sentence Transformers) trong TODO comment."
    )


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.

    TODO Sprint 1:
    1. Cài thư viện: pip install chromadb
    2. Khởi tạo ChromaDB client và collection
    3. Với mỗi file trong docs_dir:
       a. Đọc nội dung
       b. Gọi preprocess_document()
       c. Gọi chunk_document()
       d. Với mỗi chunk: gọi get_embedding() và upsert vào ChromaDB
    4. In số lượng chunk đã index

    Gợi ý khởi tạo ChromaDB:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_or_create_collection(
            name="rag_lab",
            metadata={"hnsw:space": "cosine"}
        )
    """
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # TODO: Khởi tạo ChromaDB
    # client = chromadb.PersistentClient(path=str(db_dir))
    # collection = client.get_or_create_collection(...)

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        # TODO: Gọi preprocess_document
        # doc = preprocess_document(raw_text, str(filepath))

        # TODO: Gọi chunk_document
        # chunks = chunk_document(doc)

        # TODO: Embed và lưu từng chunk vào ChromaDB
        # for i, chunk in enumerate(chunks):
        #     chunk_id = f"{filepath.stem}_{i}"
        #     embedding = get_embedding(chunk["text"])
        #     collection.upsert(
        #         ids=[chunk_id],
        #         embeddings=[embedding],
        #         documents=[chunk["text"]],
        #         metadatas=[chunk["metadata"]],
        #     )
        # total_chunks += len(chunks)

        # Placeholder để code không lỗi khi chưa implement
        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)
        print(f"    → {len(chunks)} chunks (embedding chưa implement)")
        total_chunks += len(chunks)

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")
    print("Lưu ý: Embedding chưa được implement. Xem TODO trong get_embedding() và build_index().")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong ChromaDB để kiểm tra chất lượng index.

    TODO Sprint 1:
    Implement sau khi hoàn thành build_index().
    Kiểm tra:
    - Chunk có giữ đủ metadata không? (source, section, effective_date)
    - Chunk có bị cắt giữa điều khoản không?
    - Metadata effective_date có đúng không?
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Text preview: {doc[:120]}...")
            print()
    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")
        print("Hãy chạy build_index() trước.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Kiểm tra phân phối metadata trong toàn bộ index.

    Checklist Sprint 1:
    - Mọi chunk đều có source?
    - Có bao nhiêu chunk từ mỗi department?
    - Chunk nào thiếu effective_date?

    TODO: Implement sau khi build_index() hoàn thành.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        print(f"\nTổng chunks: {len(results['metadatas'])}")

        # TODO: Phân tích metadata
        # Đếm theo department, kiểm tra effective_date missing, v.v.
        departments = {}
        missing_date = 0
        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phân bố theo department:")
        for dept, count in departments.items():
            print(f"  {dept}: {count} chunks")
        print(f"Chunks thiếu effective_date: {missing_date}")

    except Exception as e:
        print(f"Lỗi: {e}. Hãy chạy build_index() trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    # Bước 1: Kiểm tra docs
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\nTìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name}")

    # Bước 2: Test preprocess và chunking với 1 document (Task 1B)
    print("\n--- Test preprocess + chunking (Task 1B) ---")
    test_file = doc_files[0] if doc_files else None
    
    if test_file:
        raw = test_file.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(test_file))
        chunks = chunk_document(doc)
        
        print(f"\nFile: {test_file.name}")
        print(f"  Metadata:")
        print(f"    - Source: {doc['metadata']['source']}")
        print(f"    - Department: {doc['metadata']['department']}")
        print(f"    - Effective Date: {doc['metadata']['effective_date']}")
        print(f"    - Access: {doc['metadata']['access']}")
        print(f"  Token count: {len(doc['tokens'])}")
        print(f"  Sample tokens (first 20): {doc['tokens'][:20]}")
        print(f"  Số chunks: {len(chunks)}")
        
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  [Chunk {i+1}] Section: {chunk['metadata']['section']}")
            print(f"  Text preview: {chunk['text'][:150]}...")
            chunk_tokens = tokenize_text(chunk['text'])
            print(f"  Token count: {len(chunk_tokens)}")

    # Bước 3: Build index (yêu cầu implement get_embedding)
    print("\n--- Build Full Index ---")
    print("Lưu ý: Cần implement get_embedding() trước khi chạy bước này!")
    # Uncomment dòng dưới sau khi implement get_embedding():
    # build_index()

    # Bước 4: Kiểm tra index
    # Uncomment sau khi build_index() thành công:
    # list_chunks()
    # inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn thành!")
    print("Việc cần làm:")
    print("  1. Implement get_embedding() - chọn OpenAI hoặc Sentence Transformers")
    print("  2. Implement phần TODO trong build_index()")
    print("  3. Chạy build_index() và kiểm tra với list_chunks()")
    print("  4. Nếu chunking chưa tốt: cải thiện _split_by_size() để split theo paragraph")
