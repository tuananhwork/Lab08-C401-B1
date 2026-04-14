"""
index.py — Day 09: Build ChromaDB Index for Retrieval Worker
=============================================================
Mục tiêu:
  - Đọc và preprocess tài liệu từ data/docs/
  - Chunk tài liệu theo cấu trúc tự nhiên (heading/section)
  - Gắn metadata: source, section, department, effective_date, access
  - Embed và lưu vào ChromaDB collection "day09_docs"

Cách chạy:
    python index.py              # Build index
    python index.py --inspect    # Inspect existing index
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / os.getenv("CHROMA_DB_PATH", "chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "day09_docs")

CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk


# =============================================================================
# STEP 1: PREPROCESS
# =============================================================================

def normalize_text(text: str) -> str:
    """Normalize text: chuẩn hóa khoảng trắng, dấu câu, ký tự đặc biệt."""
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[^\w\s\.\,\:\;\!\?\-\(\)\[\]\/\%\€\$₫\n]', '', text)
    return text.strip()


def _infer_doc_type(source: str) -> str:
    """Infer doc_type từ source path."""
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
    Preprocess một tài liệu: extract metadata từ header, làm sạch nội dung.
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
        "doc_type": "document",
    }
    content_lines = []
    header_done = False

    for line in lines:
        if not header_done:
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or (line.isupper() and len(line) > 3):
                continue
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)
    metadata["doc_type"] = _infer_doc_type(metadata["source"])
    cleaned_text = normalize_text(cleaned_text)

    return {
        "text": cleaned_text,
        "metadata": metadata,
    }


# =============================================================================
# STEP 2: CHUNK
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk một tài liệu đã preprocess thành danh sách các chunk nhỏ.
    Split theo heading "=== Section ... ===", sau đó split theo size nếu cần.
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
    """Helper: Split text dài thành chunks với overlap."""
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
            cursor = 0
            while cursor < len(para):
                target_end = min(cursor + chunk_chars, len(para))
                split_at = para.rfind(". ", cursor, target_end)
                if split_at == -1:
                    split_at = para.rfind("\n", cursor, target_end)
                if split_at == -1 or split_at <= cursor + int(chunk_chars * 0.6):
                    split_at = target_end
                else:
                    split_at += 1

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
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.
    Ưu tiên Sentence Transformers (local), fallback OpenAI nếu có API key.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Không thể tạo embedding cho text rỗng.")

    # Option A: Sentence Transformers (local, không cần API key)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(cleaned).tolist()
    except ImportError:
        pass

    # Option B: OpenAI (cần API key)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            response = client.embeddings.create(
                input=cleaned,
                model="text-embedding-3-small",
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[WARN] OpenAI embedding failed: {e}")

    raise RuntimeError(
        "Thiếu package sentence-transformers hoặc OpenAI API key. "
        "Cài bằng: pip install sentence-transformers"
    )


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR, collection_name: str = COLLECTION_NAME) -> int:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store vào ChromaDB.

    Returns:
        Số lượng chunks đã index.
    """
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    print(f"ChromaDB path: {db_dir}")
    print(f"Collection name: {collection_name}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo ChromaDB client và collection
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    doc_files = sorted(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return 0

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        # Preprocess
        doc = preprocess_document(raw_text, str(filepath))
        # Chunk
        chunks = chunk_document(doc)

        # Embed và upsert từng chunk vào ChromaDB
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            try:
                embedding = get_embedding(chunk["text"])
                collection.upsert(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk["text"]],
                    metadatas=[chunk["metadata"]],
                )
            except Exception as e:
                print(f"⚠️ Lỗi upsert chunk {chunk_id}: {e}")
        total_chunks += len(chunks)
        print(f"    → {len(chunks)} chunks from {filepath.name}")

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")
    print(f"Collection '{collection_name}' đã được build trong ChromaDB.")
    return total_chunks


# =============================================================================
# STEP 4: INSPECT
# =============================================================================

def inspect_index(db_dir: Path = CHROMA_DB_DIR, collection_name: str = COLLECTION_NAME, n: int = 5) -> None:
    """In ra n chunk đầu tiên trong ChromaDB để kiểm tra."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection(collection_name)
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong collection '{collection_name}' ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Department: {meta.get('department', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Access: {meta.get('access', 'N/A')}")
            print(f"  Text preview: {doc[:120]}...")
            print()

        # Thống kê tổng quát
        all_results = collection.get(include=["metadatas"])
        print(f"\nTổng chunks: {len(all_results['metadatas'])}")

        departments = {}
        sources = {}
        for meta in all_results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            src = meta.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        print("\nPhân bố theo department:")
        for dept, count in sorted(departments.items()):
            print(f"  {dept}: {count} chunks")

        print("\nPhân bố theo source:")
        for src, count in sorted(sources.items()):
            print(f"  {src}: {count} chunks")

    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")
        print("Hãy chạy 'python index.py' để build index trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Build ChromaDB Index for Retrieval Worker")
    print("=" * 60)

    if "--inspect" in sys.argv:
        inspect_index()
    else:
        # Bước 1: Kiểm tra docs
        doc_files = sorted(DOCS_DIR.glob("*.txt"))
        print(f"\nTìm thấy {len(doc_files)} tài liệu:")
        for f in doc_files:
            print(f"  - {f.name}")

        # Bước 2: Build index
        print("\n--- Building Index ---")
        total = build_index()

        if total > 0:
            print("\n--- Inspecting Index ---")
            inspect_index()

        print("\n✅ Index build hoàn tất!")
        print("Test retrieval worker bằng: python workers/retrieval.py")
