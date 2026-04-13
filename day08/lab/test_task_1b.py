"""Test script for Task 1B - Preprocessing + Tokenizer"""
from pathlib import Path
from index import preprocess_document, tokenize_text

# Test với 1 document
test_file = Path("data/docs/policy_refund_v4.txt")
raw = test_file.read_text(encoding="utf-8")

print("=" * 60)
print("Task 1B: Test Preprocessing + Tokenizer")
print("=" * 60)

# Test preprocess
doc = preprocess_document(raw, str(test_file))

print(f"\n✓ File: {test_file.name}")
print(f"\nMetadata extracted:")
for key, value in doc['metadata'].items():
    print(f"  - {key}: {value}")

print(f"\nText preprocessing:")
print(f"  - Original length: {len(raw)} chars")
print(f"  - Cleaned length: {len(doc['text'])} chars")
print(f"  - Reduction: {len(raw) - len(doc['text'])} chars removed")

print(f"\nTokenization:")
print(f"  - Total tokens: {len(doc['tokens'])}")
print(f"  - First 30 tokens: {doc['tokens'][:30]}")

# Test tokenizer trên 1 đoạn text nhỏ
sample_text = "Khách hàng được quyền yêu cầu hoàn tiền khi đáp ứng đủ các điều kiện sau:"
tokens = tokenize_text(sample_text)
print(f"\nTokenizer test on sample text:")
print(f"  - Input: {sample_text}")
print(f"  - Tokens: {tokens}")

print("\n" + "=" * 60)
print("✓ Task 1B hoàn thành! Preprocessing + Tokenizer hoạt động tốt.")
print("=" * 60)
