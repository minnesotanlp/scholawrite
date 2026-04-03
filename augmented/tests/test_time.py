# Tests for scholawrite.time module.
from datetime import datetime

import pytest

from scholawrite.time import (
    normalize_timestamp,
    normalize_timestamp_ms,
    parse_iso_timestamp,
    compute_deltas,
)


class TestNormalizeTimestampMs:
    """Tests for normalize_timestamp_ms function."""

    def test_converts_unix_ms_to_iso(self) -> None:
        # 2023-11-07T18:06:39.755Z in Unix ms
        ts_ms = 1699380399755
        result = normalize_timestamp_ms(ts_ms)
        assert result == "2023-11-07T18:06:39.755000+00:00"

    def test_returns_none_for_none_input(self) -> None:
        assert normalize_timestamp_ms(None) is None

    def test_handles_epoch_zero(self) -> None:
        result = normalize_timestamp_ms(0)
        assert result == "1970-01-01T00:00:00+00:00"

    def test_handles_large_timestamps(self) -> None:
        # Year 2050: 2524608000000 ms
        ts_ms = 2524608000000
        result = normalize_timestamp_ms(ts_ms)
        assert result is not None
        assert "2050" in result


class TestNormalizeTimestamp:
    """Tests for normalize_timestamp function (polymorphic)."""

    def test_accepts_int_unix_ms(self) -> None:
        result = normalize_timestamp(1699380399755)
        assert result == "2023-11-07T18:06:39.755000+00:00"

    def test_accepts_iso_string(self) -> None:
        iso_str = "2023-11-07T18:06:39.755000+00:00"
        result = normalize_timestamp(iso_str)
        assert result == iso_str

    def test_returns_none_for_none(self) -> None:
        assert normalize_timestamp(None) is None

    def test_returns_none_for_invalid_iso_string(self) -> None:
        result = normalize_timestamp("not a timestamp")
        assert result is None


class TestParseIsoTimestamp:
    """Tests for parse_iso_timestamp function."""

    def test_parses_iso_with_timezone(self) -> None:
        ts = "2023-11-07T18:06:39.755000+00:00"
        result = parse_iso_timestamp(ts)
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 11
        assert result.day == 7
        assert result.tzinfo is not None

    def test_raises_for_invalid_format(self) -> None:
        with pytest.raises(ValueError):
            parse_iso_timestamp("invalid")


class TestComputeDeltas:
    """Tests for compute_deltas function."""

    def test_returns_empty_for_empty_input(self) -> None:
        assert compute_deltas([]) == []

    def test_first_delta_is_none(self) -> None:
        result = compute_deltas(["2023-01-01T00:00:00+00:00"])
        assert result == [None]

    def test_computes_correct_deltas(self) -> None:
        timestamps = [
            "2023-01-01T00:00:00+00:00",
            "2023-01-01T00:00:10+00:00",  # +10 seconds
            "2023-01-01T00:01:00+00:00",  # +50 seconds
        ]
        result = compute_deltas(timestamps)
        assert result[0] is None
        assert result[1] == 10.0
        assert result[2] == 50.0

    def test_handles_none_timestamps(self) -> None:
        timestamps = [
            "2023-01-01T00:00:00+00:00",
            None,
            "2023-01-01T00:00:30+00:00",
        ]
        result = compute_deltas(timestamps)
        assert result[0] is None
        assert result[1] is None  # None because prev is valid but curr is None
        assert result[2] is None  # None because prev is None

    def test_handles_all_none(self) -> None:
        result = compute_deltas([None, None, None])
        assert result == [None, None, None]

    def test_handles_negative_deltas(self) -> None:
        """Negative deltas can occur with out-of-order timestamps."""
        timestamps = [
            "2023-01-01T00:01:00+00:00",
            "2023-01-01T00:00:00+00:00",  # Earlier than first
        ]
        result = compute_deltas(timestamps)
        assert result[0] is None
        assert result[1] == -60.0  # Negative delta


class TestEdgeCases:
    """Edge case tests for time module."""

    def test_normalize_timestamp_with_negative_ms(self) -> None:
        """Negative timestamps (before epoch) should work."""
        # 1969-12-31T23:59:59 (-1000 ms before epoch)
        result = normalize_timestamp_ms(-1000)
        assert result is not None
        assert "1969" in result

    def test_normalize_timestamp_with_fractional_seconds(self) -> None:
        """Timestamps with milliseconds should preserve precision."""
        ts_ms = 1699380399755  # Has .755 seconds
        result = normalize_timestamp_ms(ts_ms)
        assert ".755" in result

    def test_parse_iso_without_timezone(self) -> None:
        """ISO timestamps without timezone should still parse."""
        ts = "2023-11-07T18:06:39"
        result = parse_iso_timestamp(ts)
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_normalize_timestamp_preserves_timezone(self) -> None:
        """Normalization should preserve UTC timezone info."""
        result = normalize_timestamp_ms(0)
        assert "+00:00" in result
