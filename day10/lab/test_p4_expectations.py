"""
Test P4 expectations — Sprint 2 validation.

Thử nghiệm halt/warn logic cho E7 và E8 (mới).
"""

from quality.expectations import run_expectations


def test_e7_effective_date_in_valid_range_ok():
    """E7 pass: tất cả effective_date trong 2024-2027."""
    cleaned = [
        {
            "chunk_id": "c1",
            "doc_id": "policy_refund_v4",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
        {
            "chunk_id": "c2",
            "doc_id": "hr_leave_policy",
            "chunk_text": "text2",
            "effective_date": "2024-01-01",
            "exported_at": "2026-04-10T08:00:00",
        },
    ]
    results, halt = run_expectations(cleaned)
    e7 = [r for r in results if r.name == "effective_date_in_valid_range"][0]
    assert e7.passed, f"E7 should pass: {e7.detail}"
    assert not halt or any(not r.passed and r.severity == "halt" for r in results if r.name != "effective_date_in_valid_range")


def test_e7_effective_date_in_valid_range_future():
    """E7 fail (halt): effective_date tương lai 2028."""
    cleaned = [
        {
            "chunk_id": "c1",
            "doc_id": "policy_refund_v4",
            "chunk_text": "text",
            "effective_date": "2028-02-01",  # tương lai
            "exported_at": "2026-04-10T08:00:00",
        },
    ]
    results, halt = run_expectations(cleaned)
    e7 = [r for r in results if r.name == "effective_date_in_valid_range"][0]
    assert not e7.passed, f"E7 should fail for future date: {e7.detail}"
    assert e7.severity == "halt"
    assert halt, "halt should be True"


def test_e7_effective_date_in_valid_range_past():
    """E7 fail (halt): effective_date quá xa 2023."""
    cleaned = [
        {
            "chunk_id": "c1",
            "doc_id": "hr_leave_policy",
            "chunk_text": "text",
            "effective_date": "2023-12-31",  # quá xa
            "exported_at": "2026-04-10T08:00:00",
        },
    ]
    results, halt = run_expectations(cleaned)
    e7 = [r for r in results if r.name == "effective_date_in_valid_range"][0]
    assert not e7.passed, f"E7 should fail for past date: {e7.detail}"
    assert e7.severity == "halt"
    assert halt, "halt should be True"


def test_e8_doc_id_distribution_balanced_ok():
    """E8 pass: tất cả 4 doc_ids có ≥1 chunk."""
    cleaned = [
        {
            "chunk_id": "c1",
            "doc_id": "policy_refund_v4",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
        {
            "chunk_id": "c2",
            "doc_id": "sla_p1_2026",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
        {
            "chunk_id": "c3",
            "doc_id": "it_helpdesk_faq",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
        {
            "chunk_id": "c4",
            "doc_id": "hr_leave_policy",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
    ]
    results, halt = run_expectations(cleaned)
    e8 = [r for r in results if r.name == "doc_id_distribution_balanced"][0]
    assert e8.passed, f"E8 should pass: {e8.detail}"
    assert e8.severity == "warn"
    assert not halt or any(not r.passed and r.severity == "halt" for r in results if r.name != "doc_id_distribution_balanced")


def test_e8_doc_id_distribution_missing_one():
    """E8 fail (warn): thiếu policy_refund_v4."""
    cleaned = [
        {
            "chunk_id": "c2",
            "doc_id": "sla_p1_2026",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
        {
            "chunk_id": "c3",
            "doc_id": "it_helpdesk_faq",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
        {
            "chunk_id": "c4",
            "doc_id": "hr_leave_policy",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
    ]
    results, halt = run_expectations(cleaned)
    e8 = [r for r in results if r.name == "doc_id_distribution_balanced"][0]
    assert not e8.passed, f"E8 should fail: {e8.detail}"
    assert e8.severity == "warn", f"E8 should be warn, not halt"
    assert "policy_refund_v4" in e8.detail, f"Detail should mention policy_refund_v4: {e8.detail}"
    # warn không trigger halt
    assert not halt or any(not r.passed and r.severity == "halt" for r in results if r.name != "doc_id_distribution_balanced")


def test_e8_doc_id_distribution_missing_multiple():
    """E8 fail (warn): thiếu [policy_refund_v4, sla_p1_2026]."""
    cleaned = [
        {
            "chunk_id": "c3",
            "doc_id": "it_helpdesk_faq",
            "chunk_text": "text",
            "effective_date": "2026-02-01",
            "exported_at": "2026-04-10T08:00:00",
        },
    ]
    results, halt = run_expectations(cleaned)
    e8 = [r for r in results if r.name == "doc_id_distribution_balanced"][0]
    assert not e8.passed, f"E8 should fail: {e8.detail}"
    assert e8.severity == "warn"


if __name__ == "__main__":
    test_e7_effective_date_in_valid_range_ok()
    print("✓ test_e7_effective_date_in_valid_range_ok")

    test_e7_effective_date_in_valid_range_future()
    print("✓ test_e7_effective_date_in_valid_range_future")

    test_e7_effective_date_in_valid_range_past()
    print("✓ test_e7_effective_date_in_valid_range_past")

    test_e8_doc_id_distribution_balanced_ok()
    print("✓ test_e8_doc_id_distribution_balanced_ok")

    test_e8_doc_id_distribution_missing_one()
    print("✓ test_e8_doc_id_distribution_missing_one")

    test_e8_doc_id_distribution_missing_multiple()
    print("✓ test_e8_doc_id_distribution_missing_multiple")

    print("\nAll P4 expectation tests passed! ✓")
