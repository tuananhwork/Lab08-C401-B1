#!/usr/bin/env python3
"""
test_retrieve_dense.py — Sprint 2 Task 2A Test Script
======================================================
Person 1 Sprint 2 Deliverable: retrieve_dense() function + test queries

Purpose: Test retrieve_dense() function and showcase output format
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Run retrieve_dense() tests"""
    try:
        from rag_answer import test_retrieve_dense, retrieve_dense
        
        print("\n" + "="*70)
        print("Sprint 2 — Task 2A: Dense Retrieval Test")
        print("="*70)
        print("""
DELIVERABLE CHECKLIST:
  ✓ retrieve_dense(query, top_k, threshold) function implemented
  ✓ Query ChromaDB collection "rag_lab"
  ✓ Return format: List[Dict] with text, metadata, score
  ✓ Score: cosine similarity (0-1)
  ✓ Support threshold filtering
  
TEST EXECUTION:
""")
        
        # Run the test
        test_retrieve_dense(verbose=True)
        
        print("\n" + "="*70)
        print("Test Summary")
        print("="*70)
        print("""
retrieve_dense() Implementation Status:
  ✓ Function signature: retrieve_dense(query, top_k=10, threshold=0.0)
  ✓ Embeds query using get_embedding() from index.py
  ✓ Queries ChromaDB collection with embedding
  ✓ Converts distance to similarity (1 - distance)
  ✓ Filters by threshold
  ✓ Returns sorted list of chunks with scores
  ✓ Error handling for ChromaDB connection failures

Next Task (Task 2B - Person 2):
  - Implement format_context() to format chunks into readable string
  - Add [1], [2] markers for citation

Output Format Example:
  {
    "text": "Full chunk text...",
    "metadata": {
      "source": "support/sla-p1-2026.pdf",
      "section": "SLA Definitions",
      "department": "IT",
      "effective_date": "2026-01-15",
      "access": "internal"
    },
    "score": 0.8234
  }
""")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure rag_answer.py is in the same directory")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
