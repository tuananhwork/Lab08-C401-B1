"""
Test P3 cleaning rule: validate exported_at values in raw rows.
"""

from transform.cleaning_rules import clean_rows


def make_row(exported_at: str, effective_date: str = "2026-04-01"):
    return {
        "doc_id": "policy_refund_v4",
        "chunk_text": "Valid rule text with enough length.",
        "effective_date": effective_date,
        "exported_at": exported_at,
    }


def test_p3_exported_at_valid_passes():
    cleaned, quarantine = clean_rows([make_row("2026-04-10T08:00:00")])
    assert len(cleaned) == 1, "Valid exported_at should remain in cleaned output"
    assert len(quarantine) == 0, "There should be no quarantine for valid exported_at"
    assert cleaned[0]["exported_at"].endswith("+00:00"), "exported_at should be normalized to UTC"


def test_p3_exported_at_missing_quarantines():
    cleaned, quarantine = clean_rows([make_row("")])
    assert len(cleaned) == 0
    assert len(quarantine) == 1
    assert quarantine[0]["reason"] == "missing_exported_at"


def test_p3_exported_at_invalid_format_quarantines():
    cleaned, quarantine = clean_rows([make_row("10/04/2026")])
    assert len(cleaned) == 0
    assert len(quarantine) == 1
    assert quarantine[0]["reason"] == "invalid_exported_at_format"


def test_p3_exported_at_future_quarantines():
    cleaned, quarantine = clean_rows([make_row("2099-01-01T00:00:00")])
    assert len(cleaned) == 0
    assert len(quarantine) == 1
    assert quarantine[0]["reason"] == "future_exported_at"
