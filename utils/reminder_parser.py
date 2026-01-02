"""Reminder Offset Parser for Task Reminders.

This module provides utilities for parsing and validating reminder offsets
from natural language inputs for task reminders.

Supported formats:
- Relative: "1 day before due", "30 minutes before", "1 hour after"
- Absolute: "at 9:00 AM", "at 14:30", "at 9am"
- ISO duration: "P1D", "PT30M", "PT1H"
"""

import re
import logging
from datetime import timedelta, datetime
from typing import Optional, Tuple, Dict, Any, List
from enum import Enum

logger = logging.getLogger("app")


class ReminderOffsetType(str, Enum):
    """Type of reminder offset."""
    BEFORE_DUE = "before_due"
    AFTER_CREATED = "after_created"
    ABSOLUTE = "absolute"


class ReminderParseResult:
    """Result of parsing a reminder offset."""

    def __init__(
        self,
        offset_minutes: Optional[int] = None,
        valid: bool = True,
        error_message: Optional[str] = None,
        offset_type: ReminderOffsetType = ReminderOffsetType.BEFORE_DUE,
        display_string: Optional[str] = None,
    ):
        self.offset_minutes = offset_minutes  # Positive = before due date
        self.valid = valid
        self.error_message = error_message
        self.offset_type = offset_type
        self.display_string = display_string

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "offset_minutes": self.offset_minutes,
            "valid": self.valid,
            "error_message": self.error_message,
            "offset_type": self.offset_type.value if self.offset_type else None,
            "display_string": self.display_string,
        }

    def to_db_string(self) -> str:
        """Convert to string for database storage."""
        if self.offset_minutes is None:
            return ""

        if self.offset_type == ReminderOffsetType.BEFORE_DUE:
            return f"-{self.offset_minutes}m"
        elif self.offset_type == ReminderOffsetType.AFTER_CREATED:
            return f"+{self.offset_minutes}m"
        else:
            return f"{self.offset_minutes}m"

    @classmethod
    def from_db_string(cls, db_string: str) -> "ReminderParseResult":
        """Reconstruct from database string."""
        if not db_string:
            return cls(valid=False, error_message="Empty reminder string")

        prefix = db_string[0]
        try:
            minutes = int(db_string[1:-1])  # Remove prefix and 'm'
        except ValueError:
            return cls(valid=False, error_message=f"Invalid reminder format: {db_string}")

        if prefix == "-":
            return cls(
                offset_minutes=minutes,
                valid=True,
                offset_type=ReminderOffsetType.BEFORE_DUE,
                display_string=cls._format_minutes(minutes, before=True),
            )
        elif prefix == "+":
            return cls(
                offset_minutes=minutes,
                valid=True,
                offset_type=ReminderOffsetType.AFTER_CREATED,
                display_string=cls._format_minutes(minutes, before=False),
            )
        else:
            return cls(
                offset_minutes=minutes,
                valid=True,
                offset_type=ReminderOffsetType.ABSOLUTE,
                display_string=cls._format_minutes(minutes, before=False),
            )

    @staticmethod
    def _format_minutes(minutes: int, before: bool = True) -> str:
        """Format minutes to human-readable string."""
        if minutes < 0:
            minutes = abs(minutes)

        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} {'before' if before else 'after'}"
        elif minutes < 1440:  # 24 hours
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours} hour{'s' if hours != 1 else ''} {'before' if before else 'after'}"
            return f"{hours}h {mins}m {'before' if before else 'after'}"
        else:
            days = minutes // 1440
            hours = (minutes % 1440) // 60
            if hours == 0:
                return f"{days} day{'s' if days != 1 else ''} {'before' if before else 'after'}"
            return f"{days}d {hours}h {'before' if before else 'after'}"


# Pattern definitions
BEFORE_PATTERNS = [
    r"(\d+)\s*(?:minute|min|m)\s*before",
    r"(\d+)\s*(?:hour|hr|h)\s*before",
    r"(\d+)\s*(?:day|d)\s*before",
    r"(\d+)\s*(?:minute|min|m)\s*prior",
    r"(\d+)\s*(?:hour|hr|h)\s*prior",
    r"(\d+)\s*(?:day|d)\s*prior",
    r"(\d+)\s*(?:minute|min|m)\s*earlier",
    r"(\d+)\s*(?:hour|hr|h)\s*earlier",
    r"(\d+)\s*(?:day|d)\s*earlier",
    r"(\d+)\s*(?:minute|min|m)\s*from now",
    r"(\d+)\s*(?:hour|hr|h)\s*from now",
    r"(\d+)\s*(?:day|d)\s*from now",
]

AFTER_PATTERNS = [
    r"(\d+)\s*(?:minute|min|m)\s*after",
    r"(\d+)\s*(?:hour|hr|h)\s*after",
    r"(\d+)\s*(?:day|d)\s*after",
    r"(\d+)\s*(?:minute|min|m)\s*later",
    r"(\d+)\s*(?:hour|hr|h)\s*later",
    r"(\d+)\s*(?:day|d)\s*later",
]

ISO_DURATION_PATTERNS = [
    r"PT(\d+)M",      # 30M = 30 minutes
    r"PT(\d+)H",      # 1H = 1 hour
    r"P(\d+)D",       # 1D = 1 day
    r"PT(\d+)H(\d+)M", # 1H30M = 1 hour 30 minutes
    r"P(\d+)DT(\d+)H(\d+)M", # 1DT2H30M = 1 day 2 hours 30 minutes
]

# Valid offset range (in minutes)
MIN_OFFSET_MINUTES = 5  # At least 5 minutes before
MAX_OFFSET_MINUTES = 10080  # At most 7 days before


def parse_reminder_offset(input_text: str) -> ReminderParseResult:
    """Parse a natural language reminder offset.

    Args:
        input_text: Natural language reminder specification

    Returns:
        ReminderParseResult with parsed offset and validation status
    """
    if not input_text:
        return ReminderParseResult(
            valid=False,
            error_message="Empty reminder offset"
        )

    # Normalize input
    normalized = input_text.lower().strip()

    # Try "before" patterns
    for pattern in BEFORE_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            value = int(match.group(1))
            offset_minutes = _convert_to_minutes(value, pattern)
            if offset_minutes is None:
                continue

            # Validate range
            if offset_minutes < MIN_OFFSET_MINUTES or offset_minutes > MAX_OFFSET_MINUTES:
                return ReminderParseResult(
                    valid=False,
                    error_message=f"Reminder must be between {MIN_OFFSET_MINUTES} minutes and {MAX_OFFSET_MINUTES // 1440} days before due date"
                )

            display = ReminderParseResult._format_minutes(offset_minutes, before=True)
            return ReminderParseResult(
                offset_minutes=offset_minutes,
                valid=True,
                offset_type=ReminderOffsetType.BEFORE_DUE,
                display_string=display,
            )

    # Try "after" patterns
    for pattern in AFTER_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            value = int(match.group(1))
            offset_minutes = _convert_to_minutes(value, pattern)
            if offset_minutes is None:
                continue

            display = ReminderParseResult._format_minutes(offset_minutes, before=False)
            return ReminderParseResult(
                offset_minutes=offset_minutes,
                valid=True,
                offset_type=ReminderOffsetType.AFTER_CREATED,
                display_string=display,
            )

    # Try ISO duration patterns
    for pattern in ISO_DURATION_PATTERNS:
        match = re.match(pattern, normalized)
        if match:
            offset_minutes = _parse_iso_duration(match, pattern)
            if offset_minutes is None:
                continue

            display = ReminderParseResult._format_minutes(offset_minutes, before=True)
            return ReminderParseResult(
                offset_minutes=offset_minutes,
                valid=True,
                offset_type=ReminderOffsetType.BEFORE_DUE,
                display_string=display,
            )

    # Try common shorthand patterns
    shorthand_result = _try_shorthand(normalized)
    if shorthand_result:
        return shorthand_result

    # No match found
    logger.warning(f"No reminder pattern matched: {input_text}")
    return ReminderParseResult(
        valid=False,
        error_message=f"Could not parse reminder offset: '{input_text}'. Try formats like '30 minutes before', '1 hour', '1 day before'"
    )


def _convert_to_minutes(value: int, pattern: str) -> Optional[int]:
    """Convert a value to minutes based on the pattern type."""
    if "minute" in pattern or re.match(r".*\dm\b", pattern):
        return value
    elif "hour" in pattern or re.match(r".*\dh\b", pattern):
        return value * 60
    elif "day" in pattern or re.match(r".*\dd\b", pattern):
        return value * 1440
    return None


def _parse_iso_duration(match, pattern: str) -> Optional[int]:
    """Parse ISO 8601 duration format."""
    try:
        if pattern == r"PT(\d+)M":
            return int(match.group(1))
        elif pattern == r"PT(\d+)H":
            return int(match.group(1)) * 60
        elif pattern == r"P(\d+)D":
            return int(match.group(1)) * 1440
        elif pattern == r"PT(\d+)H(\d+)M":
            return int(match.group(1)) * 60 + int(match.group(2))
        elif pattern == r"P(\d+)DT(\d+)H(\d+)M":
            return int(match.group(1)) * 1440 + int(match.group(2)) * 60 + int(match.group(3))
    except (ValueError, IndexError):
        pass
    return None


def _try_shorthand(normalized: str) -> Optional[ReminderParseResult]:
    """Try common shorthand patterns."""
    shorthand_map = {
        "5m": 5,
        "10m": 10,
        "15m": 15,
        "30m": 30,
        "45m": 45,
        "1h": 60,
        "2h": 120,
        "3h": 180,
        "6h": 360,
        "12h": 720,
        "1d": 1440,
        "2d": 2880,
        "3d": 4320,
        "1w": 10080,
    }

    if normalized in shorthand_map:
        minutes = shorthand_map[normalized]
        display = ReminderParseResult._format_minutes(minutes, before=True)
        return ReminderParseResult(
            offset_minutes=minutes,
            valid=True,
            offset_type=ReminderOffsetType.BEFORE_DUE,
            display_string=display,
        )

    return None


def calculate_scheduled_time(
    due_date: datetime,
    offset_minutes: int,
    offset_type: ReminderOffsetType = ReminderOffsetType.BEFORE_DUE,
) -> Optional[datetime]:
    """Calculate the scheduled time for a reminder.

    Args:
        due_date: Task due date
        offset_minutes: Offset in minutes (positive = before due)
        offset_type: Type of offset

    Returns:
        Scheduled datetime for the reminder, or None if invalid
    """
    if not due_date:
        return None

    if offset_type == ReminderOffsetType.BEFORE_DUE:
        return due_date - timedelta(minutes=offset_minutes)
    elif offset_type == ReminderOffsetType.AFTER_CREATED:
        return due_date + timedelta(minutes=offset_minutes)
    else:
        # Absolute time - offset_minutes is from epoch, not useful here
        return None


def get_common_reminder_options() -> List[Dict[str, str]]:
    """Get common reminder options for UI dropdowns.

    Returns:
        List of dictionaries with label and value keys
    """
    return [
        {"label": "5 minutes before", "value": "5m"},
        {"label": "15 minutes before", "value": "15m"},
        {"label": "30 minutes before", "value": "30m"},
        {"label": "1 hour before", "value": "1h"},
        {"label": "2 hours before", "value": "2h"},
        {"label": "6 hours before", "value": "6h"},
        {"label": "12 hours before", "value": "12h"},
        {"label": "1 day before", "value": "1d"},
        {"label": "2 days before", "value": "2d"},
        {"label": "1 week before", "value": "1w"},
    ]


def validate_reminder_offset(
    offset_minutes: int,
    due_date: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """Validate that a reminder offset is valid.

    Args:
        offset_minutes: Offset in minutes
        due_date: Optional due date to validate against

    Returns:
        Tuple of (is_valid, error_message)
    """
    if offset_minutes < MIN_OFFSET_MINUTES:
        return False, f"Reminder must be at least {MIN_OFFSET_MINUTES} minutes before"
    if offset_minutes > MAX_OFFSET_MINUTES:
        return False, f"Reminder must be at most {MAX_OFFSET_MINUTES // 1440} days before"

    if due_date:
        scheduled_time = calculate_scheduled_time(due_date, offset_minutes)
        if scheduled_time and scheduled_time <= datetime.now(due_date.tzinfo):
            return False, "Reminder time must be in the future"

    return True, None
