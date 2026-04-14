"""
run_retrieval_tests.py — Test Runner cho P2 Retrieval Worker
=============================================================
Chạy tất cả tests cho retrieval worker, bao gồm cả unit và integration tests.

Cách chạy:
    python run_retrieval_tests.py              # Chạy unit tests (không cần ChromaDB)
    python run_retrieval_tests.py --all        # Chạy cả unit + integration tests
    python run_retrieval_tests.py --verbose    # Verbose output
"""

import sys
import subprocess
from pathlib import Path


def run_tests(verbose: bool = False, all_tests: bool = False):
    """Chạy pytest với các options phù hợp."""
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_retrieval_worker.py",
    ]

    if not all_tests:
        # Chỉ chạy unit tests (bỏ qua integration tests)
        cmd.extend(["-m", "not integration"])

    if verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.extend(["-v"])

    # Thêm color output nếu terminal hỗ trợ
    cmd.extend(["--color=yes"])

    print("=" * 60)
    print("P2 Retrieval Worker — Test Suite")
    print("=" * 60)

    if not all_tests:
        print("\n📋 Running UNIT TESTS only (no ChromaDB required)")
        print("   Để chạy integration tests: python run_retrieval_tests.py --all\n")
    else:
        print("\n🔬 Running ALL TESTS (unit + integration)")
        print("   ⚠️  Integration tests require ChromaDB index.\n")
        print("   Nếu chưa có index, chạy: python index.py\n")

    print("Running: " + " ".join(cmd) + "\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Check output above.")
    print("=" * 60)

    return result.returncode


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    all_tests = "--all" in sys.argv

    exit_code = run_tests(verbose=verbose, all_tests=all_tests)
    sys.exit(exit_code)
