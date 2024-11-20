import re
from datetime import date, datetime

from app.core.exceptions import BadRequestError


def parse_date(date_str: str) -> date | None:
    """
    Parse a date string in the format YYYY-MM-DD.

    Args:
        date_str (str): The date string to parse.
    Returns:
        date: The parsed date.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise BadRequestError(f"Invalid date format, use YYYY-MM-DD. Example: 2022-12-29; got: {date_str}")


def parse_datetime(datetime_str: str) -> datetime | None:
    """
    Parse a datetime string in the format %Y-%m-%dT%H:%M:%SZ.

    Args:
        datetime_str (str): The datetime string to parse.
    Returns:
        datetime: The parsed datetime.
    """
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise BadRequestError(f"Invalid datetime format, use %Y-%m-%dT%H:%M:%SZ. "
                              f"Example: 2022-12-29T12:00:00Z; got: {datetime_str}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize the filename to use only lowercase letters, numbers, hyphens, and underscores.

    Args:
        filename (str): The original filename.

    Returns:
        str: The sanitized filename.

    Raises:
        BadRequestError: If the filename cannot be sanitized to a valid format.
    """
    if not filename:
        raise BadRequestError("Filename cannot be empty")

    # Get file extension if it exists
    parts = filename.rsplit('.', 1)
    name = parts[0]
    extension = f".{parts[1].lower()}" if len(parts) > 1 else ""

    # Convert to lowercase
    sanitized = name.lower()

    # Replace spaces and other special characters with underscore
    sanitized = re.sub(r'[^a-z0-9-]', '_', sanitized)

    # Remove consecutive underscores/hyphens
    sanitized = re.sub(r'[-_]{2,}', '_', sanitized)

    # Remove leading/trailing underscores/hyphens
    sanitized = sanitized.strip('_-')

    # Recombine with extension
    result = sanitized + extension

    # Check if we have a valid filename
    if not sanitized:
        raise BadRequestError(
            f"Filename must contain at least one letter or number; got: {filename}"
        )

    if len(result) > 255:
        raise BadRequestError(
            f"Filename is too long (max 255 characters); got {len(result)} characters"
        )

    return result
