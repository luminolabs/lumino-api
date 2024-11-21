from datetime import date, datetime

import pytest

from app.core.common import parse_date, parse_datetime, sanitize_filename
from app.core.exceptions import BadRequestError


def test_parse_date_valid():
    """Test parsing valid date strings."""
    # Test valid date
    assert parse_date("2024-01-01") == date(2024, 1, 1)

    # Test edge cases
    assert parse_date("2024-12-31") == date(2024, 12, 31)
    assert parse_date("2024-01-01") == date(2024, 1, 1)


def test_parse_date_invalid():
    """Test parsing invalid date strings."""
    # Test invalid formats
    with pytest.raises(BadRequestError):
        parse_date("01-01-2024")

    with pytest.raises(BadRequestError):
        parse_date("2024/01/01")

    with pytest.raises(BadRequestError):
        parse_date("not a date")


def test_parse_date_none():
    """Test parsing None value."""
    assert parse_date(None) is None


def test_parse_datetime_valid():
    """Test parsing valid datetime strings."""
    # Test valid datetime
    assert parse_datetime("2024-01-01T12:00:00Z") == datetime(2024, 1, 1, 12, 0, 0)

    # Test edge cases
    assert parse_datetime("2024-12-31T23:59:59Z") == datetime(2024, 12, 31, 23, 59, 59)
    assert parse_datetime("2024-01-01T00:00:00Z") == datetime(2024, 1, 1, 0, 0, 0)


def test_parse_datetime_invalid():
    """Test parsing invalid datetime strings."""
    # Test invalid formats
    with pytest.raises(BadRequestError):
        parse_datetime("2024-01-01")

    with pytest.raises(BadRequestError):
        parse_datetime("2024-01-01 12:00:00")

    with pytest.raises(BadRequestError):
        parse_datetime("not a datetime")


def test_parse_datetime_none():
    """Test parsing None value."""
    assert parse_datetime(None) is None


def test_sanitize_filename_valid():
    """Test sanitizing valid filenames."""
    # Test basic sanitization
    assert sanitize_filename("test.txt") == "test.txt"
    assert sanitize_filename("Test File.txt") == "test_file.txt"
    assert sanitize_filename("test-file.txt") == "test-file.txt"

    # Test special characters
    assert sanitize_filename("test@#$%^&*.txt") == "test.txt"
    assert sanitize_filename("test__file.txt") == "test_file.txt"

    # Test file extensions
    assert sanitize_filename("test.JSON") == "test.json"
    assert sanitize_filename("test.TXT") == "test.txt"


def test_sanitize_filename_invalid():
    """Test sanitizing invalid filenames."""
    # Test empty filename
    with pytest.raises(BadRequestError):
        sanitize_filename("")

    # Test filename with only special characters
    with pytest.raises(BadRequestError):
        sanitize_filename("@#$%^&*")

    # Test filename that's too long
    with pytest.raises(BadRequestError):
        sanitize_filename("a" * 256)


def test_sanitize_filename_edge_cases():
    """Test sanitizing edge case filenames."""
    # Test leading/trailing spaces and special characters
    assert sanitize_filename(" test.txt ") == "test.txt"
    assert sanitize_filename("___test___.txt") == "test.txt"

    # Test multiple consecutive special characters
    assert sanitize_filename("test---file.txt") == "test_file.txt"
    assert sanitize_filename("test___file.txt") == "test_file.txt"

    # Test mixed case and special characters
    assert sanitize_filename("Test@#File.txt") == "test_file.txt"
