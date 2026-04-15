from datetime import datetime, timedelta, timezone

from transform.cleaning_rules import clean_rows


def test_exported_at_invalid_format_quarantines():
    rows = [
        {
            "doc_id": "policy_refund_v4",
            "chunk_text": "This is a valid chunk text with enough length.",
            "effective_date": "2026-04-01",
            "exported_at": "April 1 2026",
        }
    ]

    cleaned, quarantine = clean_rows(rows)

    assert len(cleaned) == 0
    assert len(quarantine) == 1
    assert quarantine[0]["reason"] == "invalid_exported_at_format"
    assert quarantine[0]["exported_at_raw"] == "April 1 2026"


def test_exported_at_future_date_quarantines():
    future = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    rows = [
        {
            "doc_id": "policy_refund_v4",
            "chunk_text": "This is a valid chunk text with enough length.",
            "effective_date": "2026-04-01",
            "exported_at": future,
        }
    ]

    cleaned, quarantine = clean_rows(rows)

    assert len(cleaned) == 0
    assert len(quarantine) == 1
    assert quarantine[0]["reason"] == "future_exported_at"
    assert quarantine[0]["exported_at_normalized"] == future


def test_empty_exported_at_is_allowed():
    rows = [
        {
            "doc_id": "policy_refund_v4",
            "chunk_text": "This is a valid chunk text with enough length.",
            "effective_date": "2026-04-01",
            "exported_at": "",
        }
    ]

    cleaned, quarantine = clean_rows(rows)

    assert len(cleaned) == 1
    assert len(quarantine) == 0
    assert cleaned[0]["exported_at"] == ""
