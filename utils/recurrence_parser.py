"""Recurrence Pattern Parser for Task Scheduling.

This module provides utilities for parsing and validating recurrence patterns
from natural language inputs for recurring tasks.

Supported patterns:
- Daily: "daily", "every day", "each day"
- Weekly: "weekly", "every week", "monday", "tuesday", etc.
- Monthly: "monthly", "every month", "1st", "15th", "last day"
"""

import re
import logging
from datetime import datetime, time
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum

logger = logging.getLogger("app")


class RecurrenceFrequency(str, Enum):
    """Recurrence frequency types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NONE = "none"


class DayOfWeek(int, Enum):
    """Day of week enum for weekly recurrence."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


# Pattern mappings
WEEKDAY_MAP = {
    "monday": DayOfWeek.MONDAY,
    "mon": DayOfWeek.MONDAY,
    "tuesday": DayOfWeek.TUESDAY,
    "tue": DayOfWeek.TUESDAY,
    "wednesday": DayOfWeek.WEDNESDAY,
    "wed": DayOfWeek.WEDNESDAY,
    "thursday": DayOfWeek.THURSDAY,
    "thu": DayOfWeek.THURSDAY,
    "friday": DayOfWeek.FRIDAY,
    "fri": DayOfWeek.FRIDAY,
    "saturday": DayOfWeek.SATURDAY,
    "sat": DayOfWeek.SATURDAY,
    "sunday": DayOfWeek.SUNDAY,
    "sun": DayOfWeek.SUNDAY,
}

DAILY_PATTERNS = [
    r"^daily$",
    r"^every\s*day$",
    r"^each\s*day$",
    r"^everyday$",
]

WEEKLY_PATTERNS = [
    r"^weekly$",
    r"^every\s*week$",
    r"^each\s*week$",
    r"^every\s*(\w+)$",  # e.g., "every monday"
    r"^on\s+(\w+)$",  # e.g., "on monday"
    r"^(\w+)$",  # e.g., "monday"
]

MONTHLY_PATTERNS = [
    r"^monthly$",
    r"^every\s*month$",
    r"^each\s*month$",
    r"^day\s*(\d{1,2})$",  # e.g., "day 15"
    r"^(\d{1,2})(st|nd|rd|th)?$",  # e.g., "15", "15th"
    r"^last\s*day$",
    r"^end\s*of\s*month$",
]


class RecurrenceParseResult:
    """Result of parsing a recurrence pattern."""

    def __init__(
        self,
        frequency: RecurrenceFrequency,
        valid: bool = True,
        error_message: Optional[str] = None,
        day_of_week: Optional[DayOfWeek] = None,
        day_of_month: Optional[int] = None,
        interval: int = 1,
    ):
        self.frequency = frequency
        self.valid = valid
        self.error_message = error_message
        self.day_of_week = day_of_week
        self.day_of_month = day_of_month
        self.interval = interval

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "frequency": self.frequency.value if self.frequency else None,
            "valid": self.valid,
            "error_message": self.error_message,
            "day_of_week": self.day_of_week.value if self.day_of_week else None,
            "day_of_month": self.day_of_month,
            "interval": self.interval,
        }

    def to_pattern_string(self) -> str:
        """Convert to a pattern string for database storage."""
        if self.frequency == RecurrenceFrequency.DAILY:
            return "daily"
        elif self.frequency == RecurrenceFrequency.WEEKLY:
            if self.day_of_week is not None:
                day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                return f"weekly:{day_names[self.day_of_week.value]}"
            return "weekly"
        elif self.frequency == RecurrenceFrequency.MONTHLY:
            if self.day_of_month:
                return f"monthly:{self.day_of_month}"
            return "monthly"
        return "none"

    @classmethod
    def from_pattern_string(cls, pattern: str) -> "RecurrenceParseResult":
        """Reconstruct from a stored pattern string."""
        if pattern == "none":
            return cls(frequency=RecurrenceFrequency.NONE, valid=True)

        if pattern == "daily":
            return cls(frequency=RecurrenceFrequency.DAILY, valid=True)

        if pattern == "weekly":
            return cls(frequency=RecurrenceFrequency.WEEKLY, valid=True)

        if pattern.startswith("weekly:"):
            day_name = pattern.split(":")[1].lower()
            if day_name in WEEKDAY_MAP:
                return cls(
                    frequency=RecurrenceFrequency.WEEKLY,
                    valid=True,
                    day_of_week=WEEKDAY_MAP[day_name],
                )

        if pattern.startswith("monthly:"):
            try:
                day = int(pattern.split(":")[1])
                return cls(
                    frequency=RecurrenceFrequency.MONTHLY,
                    valid=True,
                    day_of_month=day,
                )
            except (ValueError, IndexError):
                pass

        return cls(
            frequency=RecurrenceFrequency.NONE,
            valid=False,
            error_message=f"Unknown pattern: {pattern}",
        )


def parse_recurrence_pattern(input_text: str) -> RecurrenceParseResult:
    """Parse a natural language recurrence pattern.

    Args:
        input_text: Natural language recurrence specification

    Returns:
        RecurrenceParseResult with parsed frequency and validation status
    """
    if not input_text:
        return RecurrenceParseResult(
            frequency=RecurrenceFrequency.NONE,
            valid=False,
            error_message="Empty recurrence pattern",
        )

    # Normalize input
    normalized = input_text.lower().strip()

    # Try to match daily patterns
    for pattern in DAILY_PATTERNS:
        if re.match(pattern, normalized):
            logger.debug(f"Matched daily pattern: {input_text}")
            return RecurrenceParseResult(frequency=RecurrenceFrequency.DAILY)

    # Try to match weekly patterns
    for pattern in WEEKLY_PATTERNS:
        match = re.match(pattern, normalized)
        if match:
            # Check if it's a specific day of week
            if match.lastindex and match.lastindex >= 1:
                captured = match.group(1)
                if captured in WEEKDAY_MAP:
                    logger.debug(f"Matched weekly pattern with day: {input_text}")
                    return RecurrenceParseResult(
                        frequency=RecurrenceFrequency.WEEKLY,
                        day_of_week=WEEKDAY_MAP[captured],
                    )

            # Plain "weekly" or similar
            if captured in ["weekly", "week"]:
                logger.debug(f"Matched weekly pattern: {input_text}")
                return RecurrenceParseResult(frequency=RecurrenceFrequency.WEEKLY)

    # Try to match monthly patterns
    for pattern in MONTHLY_PATTERNS:
        match = re.match(pattern, normalized)
        if match:
            if match.lastindex and match.lastindex >= 1:
                # Try to extract day number
                try:
                    day = int(match.group(1))
                    if 1 <= day <= 31:
                        logger.debug(f"Matched monthly pattern with day: {input_text}")
                        return RecurrenceParseResult(
                            frequency=RecurrenceFrequency.MONTHLY,
                            day_of_month=day,
                        )
                except ValueError:
                    pass

                # Check for "last day" or "end of month"
                if match.group(1) in ["last", "end"]:
                    logger.debug(f"Matched monthly pattern (end of month): {input_text}")
                    return RecurrenceParseResult(
                        frequency=RecurrenceFrequency.MONTHLY,
                        day_of_month=0,  # 0 means last day of month
                    )

            # Plain "monthly"
            if match.group(1) in ["monthly", "month"]:
                logger.debug(f"Matched monthly pattern: {input_text}")
                return RecurrenceParseResult(frequency=RecurrenceFrequency.MONTHLY)

    # No match found
    logger.warning(f"No recurrence pattern matched: {input_text}")
    return RecurrenceParseResult(
        frequency=RecurrenceFrequency.NONE,
        valid=False,
        error_message=f"Could not parse recurrence pattern: '{input_text}'",
    )


def normalize_recurrence_input(input_text: str) -> Tuple[RecurrenceFrequency, Optional[str]]:
    """Normalize and return the recurrence type from input text.

    Args:
        input_text: User input for recurrence

    Returns:
        Tuple of (RecurrenceFrequency, pattern_details)
    """
    result = parse_recurrence_pattern(input_text)

    if not result.valid:
        return RecurrenceFrequency.NONE, None

    return result.frequency, result.to_pattern_string()


def get_common_recurrence_options() -> List[Dict[str, str]]:
    """Get common recurrence options for UI dropdowns.

    Returns:
        List of dictionaries with label and value keys
    """
    return [
        {"label": "Does not repeat", "value": "none"},
        {"label": "Daily", "value": "daily"},
        {"label": "Weekly", "value": "weekly"},
        {"label": "Monthly", "value": "monthly"},
        {"label": "Every Monday", "value": "weekly:monday"},
        {"label": "Every Friday", "value": "weekly:friday"},
        {"label": "1st of every month", "value": "monthly:1"},
        {"label": "15th of every month", "value": "monthly:15"},
    ]


def validate_recurrence_for_task(
    frequency: RecurrenceFrequency,
    due_date: Optional[datetime],
) -> Tuple[bool, Optional[str]]:
    """Validate that a recurrence pattern is valid for the given task.

    Args:
        frequency: The recurrence frequency
        due_date: Optional due date to validate against

    Returns:
        Tuple of (is_valid, error_message)
    """
    if frequency == RecurrenceFrequency.NONE:
        return True, None

    if frequency == RecurrenceFrequency.MONTHLY:
        # For monthly with specific day, ensure due date exists
        if not due_date:
            return False, "Monthly recurring tasks require a due date"

    return True, None
