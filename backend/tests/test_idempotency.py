"""Tests for the hardened idempotency / deduplication logic."""

from __future__ import annotations

import pytest

from src.logic.idempotency import (
    RowValidationError,
    canonicalize_row,
    compute_dedup_key,
    count_meaningful_fields,
    is_auto_generated,
)


def test_native_id_used_verbatim():
    key, is_native = compute_dedup_key({"a": "1", "b": "2"}, scope="acct-1", native_id="TXN-99")
    assert is_native is True
    assert key == "TXN-99"
    assert is_auto_generated(key) is False


def test_native_id_whitespace_falls_back_to_hash():
    key, is_native = compute_dedup_key({"a": "1", "b": "2"}, scope="acct-1", native_id="   ")
    assert is_native is False
    assert is_auto_generated(key) is True


def test_auto_key_is_deterministic():
    row = {"Action": "Market buy", "Total": "150.0", "Time": "2025-01-01"}
    key1, _ = compute_dedup_key(row, scope="acct-1")
    key2, _ = compute_dedup_key(dict(reversed(list(row.items()))), scope="acct-1")
    assert key1 == key2  # order-independent


def test_auto_key_scope_salts_the_hash():
    row = {"Action": "Market buy", "Total": "150.0"}
    key_a, _ = compute_dedup_key(row, scope="acct-1")
    key_b, _ = compute_dedup_key(row, scope="acct-2")
    assert key_a != key_b


def test_auto_key_ignores_cosmetic_whitespace_and_blanks():
    row1 = {"Action": "Market buy", "Total": "150.0", "Notes": ""}
    row2 = {"Action": "  Market   buy ", "Total": "150.0"}
    assert compute_dedup_key(row1, scope="s")[0] == compute_dedup_key(row2, scope="s")[0]


def test_distinct_rows_produce_distinct_keys():
    row1 = {"Action": "Market buy", "Total": "150.0", "Time": "2025-01-01"}
    row2 = {"Action": "Market buy", "Total": "151.0", "Time": "2025-01-01"}
    assert compute_dedup_key(row1, scope="s")[0] != compute_dedup_key(row2, scope="s")[0]


def test_corrupted_single_field_row_rejected():
    with pytest.raises(RowValidationError):
        compute_dedup_key({"only": "one"}, scope="s")


def test_empty_row_rejected():
    with pytest.raises(RowValidationError):
        compute_dedup_key({"a": "", "b": None}, scope="s")


def test_count_meaningful_fields():
    assert count_meaningful_fields({"a": "1", "b": "", "c": None, "d": "  x "}) == 2


def test_canonicalize_row_stable_form():
    assert canonicalize_row({"b": "2", "a": "1"}) == "a=1\x1fb=2"
