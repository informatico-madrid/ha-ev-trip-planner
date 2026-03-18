"""Tests for trip ID generation.

This module contains comprehensive tests for recurrent and punctual trip ID generation.
"""

import pytest
from datetime import date, datetime

from custom_components.ev_trip_planner.utils import (
    generate_trip_id,
    is_valid_trip_id,
    generate_random_suffix,
)


class TestRecurrentTripIds:
    """Tests for recurrent trip ID generation.

    Format: rec_{day}_{random}
    Example: rec_lun_abc123
    """

    def test_recurrent_spanish_monday(self):
        """Test recurrent trip ID with Spanish Monday."""
        trip_id = generate_trip_id("recurrente", "lunes")
        assert trip_id.startswith("rec_lun_")
        # Format: rec (3) + _ (1) + lun (3) + _ (1) + suffix (6) = 14
        assert len(trip_id) == 14

    def test_recurrent_spanish_tuesday(self):
        """Test recurrent trip ID with Spanish Tuesday."""
        trip_id = generate_trip_id("recurrente", "martes")
        assert trip_id.startswith("rec_mar_")

    def test_recurrent_spanish_wednesday(self):
        """Test recurrent trip ID with Spanish Wednesday."""
        trip_id = generate_trip_id("recurrente", "miercoles")
        assert trip_id.startswith("rec_mie_")

    def test_recurrent_spanish_thursday(self):
        """Test recurrent trip ID with Spanish Thursday."""
        trip_id = generate_trip_id("recurrente", "jueves")
        assert trip_id.startswith("rec_jue_")

    def test_recurrent_spanish_friday(self):
        """Test recurrent trip ID with Spanish Friday."""
        trip_id = generate_trip_id("recurrente", "viernes")
        assert trip_id.startswith("rec_vie_")

    def test_recurrent_spanish_saturday(self):
        """Test recurrent trip ID with Spanish Saturday."""
        trip_id = generate_trip_id("recurrente", "sabado")
        assert trip_id.startswith("rec_sab_")

    def test_recurrent_spanish_sunday(self):
        """Test recurrent trip ID with Spanish Sunday."""
        trip_id = generate_trip_id("recurrente", "domingo")
        assert trip_id.startswith("rec_dom_")

    def test_recurrent_english_monday(self):
        """Test recurrent trip ID with English Monday."""
        trip_id = generate_trip_id("recurrente", "monday")
        assert trip_id.startswith("rec_lun_")

    def test_recurrent_english_tuesday(self):
        """Test recurrent trip ID with English Tuesday."""
        trip_id = generate_trip_id("recurrente", "tuesday")
        assert trip_id.startswith("rec_mar_")

    def test_recurrent_english_wednesday(self):
        """Test recurrent trip ID with English Wednesday."""
        trip_id = generate_trip_id("recurrente", "wednesday")
        assert trip_id.startswith("rec_mie_")

    def test_recurrent_english_thursday(self):
        """Test recurrent trip ID with English Thursday."""
        trip_id = generate_trip_id("recurrente", "thursday")
        assert trip_id.startswith("rec_jue_")

    def test_recurrent_english_friday(self):
        """Test recurrent trip ID with English Friday."""
        trip_id = generate_trip_id("recurrente", "friday")
        assert trip_id.startswith("rec_vie_")

    def test_recurrent_english_saturday(self):
        """Test recurrent trip ID with English Saturday."""
        trip_id = generate_trip_id("recurrente", "saturday")
        assert trip_id.startswith("rec_sab_")

    def test_recurrent_english_sunday(self):
        """Test recurrent trip ID with English Sunday."""
        trip_id = generate_trip_id("recurrente", "sunday")
        assert trip_id.startswith("rec_dom_")

    def test_recurrent_unknown_day_fallback(self):
        """Test recurrent trip ID with unknown day uses fallback."""
        trip_id = generate_trip_id("recurrente", "randomday")
        assert trip_id.startswith("rec_ran_")

    def test_recurrent_case_insensitive(self):
        """Test recurrent trip ID is case insensitive."""
        trip_id = generate_trip_id("recurrente", "LUNES")
        assert trip_id.startswith("rec_lun_")

    def test_recurrent_none_uses_default(self):
        """Test recurrent trip ID with None uses default (lunes)."""
        trip_id = generate_trip_id("recurrente", None)
        assert trip_id.startswith("rec_lun_")

    def test_recurrent_random_suffix_unique(self):
        """Test that random suffix is unique for different calls."""
        ids = [generate_trip_id("recurrente", "lunes") for _ in range(100)]
        assert len(set(ids)) == 100

    def test_recurrent_random_suffix_length(self):
        """Test that random suffix is exactly 6 characters."""
        trip_id = generate_trip_id("recurrente", "lunes")
        suffix = trip_id.split("_")[2]
        assert len(suffix) == 6

    def test_recurrent_random_suffix_alphanumeric(self):
        """Test that random suffix is alphanumeric lowercase."""
        trip_id = generate_trip_id("recurrente", "lunes")
        suffix = trip_id.split("_")[2]
        assert suffix.isalnum()
        assert suffix.islower()


class TestPunctualTripIds:
    """Tests for punctual trip ID generation.

    Format: pun_{date}_{random}
    Example: pun_20251119_abc123
    """

    def test_punctual_ymd_string(self):
        """Test punctual trip ID with YYYYMMDD string."""
        trip_id = generate_trip_id("punctual", "20251119")
        assert trip_id.startswith("pun_20251119_")

    def test_punctual_date_object(self):
        """Test punctual trip ID with date object."""
        trip_id = generate_trip_id("punctual", date(2025, 11, 19))
        assert trip_id.startswith("pun_20251119_")

    def test_punctual_iso_date_string(self):
        """Test punctual trip ID with ISO format date string."""
        trip_id = generate_trip_id("punctual", "2025-11-19")
        assert trip_id.startswith("pun_20251119_")

    def test_punctual_slash_date_string(self):
        """Test punctual trip ID with slash format date string."""
        trip_id = generate_trip_id("punctual", "2025/11/19")
        assert trip_id.startswith("pun_20251119_")

    def test_punctual_none_uses_today(self):
        """Test punctual trip ID with None uses today's date."""
        trip_id = generate_trip_id("punctual", None)
        today = datetime.now().strftime("%Y%m%d")
        assert trip_id.startswith(f"pun_{today}_")

    def test_punctual_different_dates(self):
        """Test punctual trip ID with different dates."""
        trip_id1 = generate_trip_id("punctual", "20250101")
        trip_id2 = generate_trip_id("punctual", "20251231")
        assert "20250101" in trip_id1
        assert "20251231" in trip_id2

    def test_punctual_random_suffix_unique(self):
        """Test that random suffix is unique for different calls."""
        ids = [generate_trip_id("punctual", "20251119") for _ in range(100)]
        assert len(set(ids)) == 100

    def test_punctual_random_suffix_length(self):
        """Test that random suffix is exactly 6 characters."""
        trip_id = generate_trip_id("punctual", "20251119")
        suffix = trip_id.split("_")[2]
        assert len(suffix) == 6

    def test_punctual_random_suffix_alphanumeric(self):
        """Test that random suffix is alphanumeric lowercase."""
        trip_id = generate_trip_id("punctual", "20251119")
        suffix = trip_id.split("_")[2]
        assert suffix.isalnum()
        assert suffix.islower()


class TestTripIdValidation:
    """Tests for trip ID validation with is_valid_trip_id."""

    def test_validate_valid_rec_trip_id(self):
        """Test validation of valid recurrent trip ID."""
        assert is_valid_trip_id("rec_lun_abc123") is True

    def test_validate_valid_pun_trip_id(self):
        """Test validation of valid punctual trip ID."""
        assert is_valid_trip_id("pun_20251119_abc123") is True

    def test_validate_empty_string(self):
        """Test validation of empty string."""
        assert is_valid_trip_id("") is False

    def test_validate_none(self):
        """Test validation of None."""
        assert is_valid_trip_id(None) is False

    def test_validate_rec_short_suffix(self):
        """Test validation of recurrent ID with short suffix."""
        assert is_valid_trip_id("rec_lun_ab") is False

    def test_validate_pun_short_suffix(self):
        """Test validation of punctual ID with short suffix."""
        assert is_valid_trip_id("pun_20251119_ab") is False

    def test_validate_pun_wrong_date_length(self):
        """Test validation of punctual ID with wrong date length."""
        assert is_valid_trip_id("pun_2025111_abc123") is False

    def test_validate_wrong_format(self):
        """Test validation of wrong format."""
        assert is_valid_trip_id("invalid_format") is False

    def test_validate_too_many_parts(self):
        """Test validation of too many parts."""
        assert is_valid_trip_id("rec_lun_abc_123") is False


class TestTripIdEdgeCases:
    """Tests for edge cases in trip ID generation."""

    def test_unknown_trip_type_fallback(self):
        """Test unknown trip type returns fallback format."""
        trip_id = generate_trip_id("unknown_type", None)
        assert trip_id.startswith("trip_")

    def test_recurrent_single_letter_day(self):
        """Test with single letter day input."""
        trip_id = generate_trip_id("recurrente", "x")
        assert trip_id.startswith("rec_x")

    def test_punctual_datetime_object(self):
        """Test with datetime object (should work like date)."""
        trip_id = generate_trip_id("punctual", datetime(2025, 11, 19, 14, 30))
        assert trip_id.startswith("pun_20251119_")
