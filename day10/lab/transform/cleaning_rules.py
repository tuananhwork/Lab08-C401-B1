"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).

P2 — Rule 1: BOM / control character detection → quarantine
P2 — Rule 2: Whitespace collapse + min length check → quarantine if < 20 chars
P3 — Rule 3+: Validate exported_at, quarantine if future date
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _normalize_exported_at(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_datetime, error_reason).
    iso_datetime rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "missing_exported_at"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return "", "invalid_exported_at_format"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat(), ""


def _has_control_characters(text: str) -> bool:
    """
    P2 — Rule 1 helper: Check for BOM or control characters.
    Returns True if text contains BOM (\ufeff) or control chars (excluding normal whitespace).
    """
    if "\ufeff" in text:
        return True
    # Check for control characters (ASCII 0-31, 127) excluding common whitespace
    for ch in text:
        code = ord(ch)
        if code == 127:  # DEL
            return True
        if code < 32 and ch not in ("\n", "\r", "\t"):
            return True
    return False


def _collapse_whitespace(text: str) -> tuple[str, bool]:
    """
    P2 — Rule 2 helper: Collapse multiple spaces into one.
    Returns (cleaned_text, was_modified).
    """
    original = text
    # Replace multiple spaces/tabs with single space
    cleaned = re.sub(r"[ \t]+", " ", text)
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    return cleaned, cleaned != original


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.

    P2 — Rule 1: BOM / control char → quarantine
    P2 — Rule 2: Whitespace collapse + quarantine if < 20 chars after normalize
    P3 — Rule 3: Validate exported_at format / future date → quarantine
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    # P2/P3 metric tracking
    metrics = {
        "rule1_bom_control_quarantine": 0,
        "rule2_whitespace_collapsed": 0,
        "rule2_short_text_quarantine": 0,
        "rule3_exported_at_invalid_quarantine": 0,
        "rule3_exported_at_future_quarantine": 0,
    }

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # P2 — Rule 1: Check for BOM / control characters
        if _has_control_characters(text):
            metrics["rule1_bom_control_quarantine"] += 1
            quarantine.append({**raw, "reason": "bom_or_control_characters_detected"})
            continue

        # P2 — Rule 2: Whitespace collapse
        collapsed_text, was_collapsed = _collapse_whitespace(text)
        if was_collapsed:
            metrics["rule2_whitespace_collapsed"] += 1

        # P2 — Rule 2: Check minimum length after collapse
        if len(collapsed_text) < 20:
            metrics["rule2_short_text_quarantine"] += 1
            quarantine.append({
                **raw,
                "reason": "chunk_too_short_after_whitespace_normalize",
                "collapsed_length": len(collapsed_text),
            })
            continue

        # P3 — Validate exported_at and quarantine future or invalid timestamps
        exp_norm, exp_err = _normalize_exported_at(exported_at)
        if exp_err == "missing_exported_at":
            metrics["rule3_exported_at_invalid_quarantine"] += 1
            quarantine.append({**raw, "reason": exp_err})
            continue
        if exp_err == "invalid_exported_at_format":
            metrics["rule3_exported_at_invalid_quarantine"] += 1
            quarantine.append({**raw, "reason": exp_err, "exported_at_raw": exported_at})
            continue
        if datetime.fromisoformat(exp_norm) > datetime.now(timezone.utc):
            metrics["rule3_exported_at_future_quarantine"] += 1
            quarantine.append({
                **raw,
                "reason": "future_exported_at",
                "exported_at_normalized": exp_norm,
            })
            continue

        key = _norm_text(collapsed_text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = collapsed_text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exp_norm or "",
            }
        )

    # Log metric_impact for P2/P3 rules
    if any(v > 0 for v in metrics.values()):
        print(f"[P2/P3 Metric Impact] {metrics}")

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
