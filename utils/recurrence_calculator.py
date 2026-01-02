"""Recurrence Calculator for Next Due Date Computation.

This module provides utilities for calculating the next due date
for recurring tasks based on their recurrence pattern and current completion date.

Supports:
- Daily recurrence
- Weekly recurrence (with optional specific day of week)
- Monthly recurrence (with optional specific day of month)
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, Tuple
from dateutil.relativedelta import relativedelta

logger = logging.getLogger("app")


class RecurrenceCalculator:
    """Calculator for next occurrence of recurring tasks."""

    @staticmethod
    def calculate_next_due_date(
        current_due_date: datetime,
        frequency: str,
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
    ) -> Optional[datetime]:
        """Calculate the next due date after task completion.

        Args:
            current_due_date: The date when the task was completed
            frequency: Recurrence frequency ("daily", "weekly", "monthly")
            day_of_week: Day of week for weekly (0=Monday, 6=Sunday)
            day_of_month: Day of month for monthly (1-31, 0=last day)

        Returns:
            Next due date, or None if no recurrence
        """
        if frequency == "none":
            return None

        if frequency == "daily":
            return RecurrenceCalculator._next_daily(current_due_date)
        elif frequency == "weekly":
            return RecurrenceCalculator._next_weekly(current_due_date, day_of_week)
        elif frequency == "monthly":
            return RecurrenceCalculator._next_monthly(current_due_date, day_of_month)
        else:
            logger.warning(f"Unknown recurrence frequency: {frequency}")
            return None

    @staticmethod
    def _next_daily(completed_at: datetime) -> datetime:
        """Calculate next daily occurrence (next day)."""
        # Next occurrence is the next day at the same time
        return completed_at + timedelta(days=1)

    @staticmethod
    def _next_weekly(completed_at: datetime, target_day: Optional[int] = None) -> datetime:
        """Calculate next weekly occurrence.

        Args:
            completed_at: When the task was completed
            target_day: Target day of week (0=Monday, 6=Sunday)
                       If None, uses same day of week as current_due_date
        """
        # If no specific day, use the day of week from current due date
        if target_day is None:
            target_day = completed_at.weekday()

        current_day = completed_at.weekday()

        # Calculate days until target day
        days_ahead = target_day - current_day
        if days_ahead <= 0:
            # Target day has passed this week, go to next week
            days_ahead += 7

        return completed_at + timedelta(days=days_ahead)

    @staticmethod
    def _next_monthly(completed_at: datetime, target_day: Optional[int] = None) -> datetime:
        """Calculate next monthly occurrence.

        Args:
            completed_at: When the task was completed
            target_day: Target day of month (1-31, 0=last day of month)
                       If None, uses same day as current due date
        """
        # Determine target day
        if target_day is None:
            target_day = completed_at.day
        elif target_day == 0:
            # Last day of month - calculate last day of next month
            next_month = completed_at + relativedelta(months=1)
            return RecurrenceCalculator._get_last_day_of_month(next_month)

        # Calculate next month with target day
        next_month = completed_at + relativedelta(months=1)

        # Handle months with fewer days than target_day
        # e.g., if target is 31 but next month only has 30 days
        try:
            return next_month.replace(day=target_day)
        except ValueError:
            # Roll back to last day of month
            return RecurrenceCalculator._get_last_day_of_month(next_month)

    @staticmethod
    def _get_last_day_of_month(dt: datetime) -> datetime:
        """Get the last day of the month for a given date."""
        # Go to first day of next month, then subtract one day
        if dt.month == 12:
            next_month = dt.replace(year=dt.year + 1, month=1, day=1)
        else:
            next_month = dt.replace(month=dt.month + 1, day=1)

        return next_month - timedelta(days=1)

    @staticmethod
    def calculate_next_chain(
        completed_task_data: dict,
        max_occurrences: int = 52,
    ) -> list:
        """Calculate a chain of future occurrences for display.

        Args:
            completed_task_data: Data from the completed task
            max_occurrences: Maximum number of occurrences to generate

        Returns:
            List of future due dates
        """
        frequency = completed_task_data.get("recurrence_pattern", "none")
        if frequency == "none":
            return []

        current = datetime.now()
        occurrences = []

        # Parse frequency for extra parameters
        day_of_week = None
        day_of_month = None

        if ":" in frequency:
            freq_type, param = frequency.split(":", 1)
            if freq_type == "weekly" and param in [
                "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
            ]:
                day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                          "friday": 4, "saturday": 5, "sunday": 6}
                day_of_week = day_map.get(param)
            elif freq_type == "monthly":
                try:
                    day_of_month = int(param)
                except ValueError:
                    pass

        # Generate occurrences
        for i in range(min(max_occurrences, 52)):  # Max 1 year
            next_date = RecurrenceCalculator.calculate_next_due_date(
                current,
                frequency,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
            )
            if next_date:
                occurrences.append(next_date)
                current = next_date
            else:
                break

        return occurrences

    @staticmethod
    def is_valid_recurrence(frequency: str) -> bool:
        """Check if a recurrence frequency is valid.

        Args:
            frequency: The frequency string to validate

        Returns:
            True if valid, False otherwise
        """
        valid_frequencies = {"none", "daily", "weekly", "monthly"}
        if frequency in valid_frequencies:
            return True
        if frequency.startswith("weekly:") and len(frequency) > 8:
            day = frequency.split(":")[1].lower()
            return day in {"monday", "tuesday", "wednesday", "thursday",
                          "friday", "saturday", "sunday"}
        if frequency.startswith("monthly:") and len(frequency) > 8:
            try:
                day = int(frequency.split(":")[1])
                return 1 <= day <= 31 or day == 0
            except ValueError:
                return False
        return False


def get_next_occurrence(
    completed_at: datetime,
    recurrence_pattern: str,
) -> Optional[datetime]:
    """Convenience function to get next occurrence date.

    Args:
        completed_at: When the task was completed
        recurrence_pattern: The recurrence pattern string

    Returns:
        Next due date or None if no recurrence
    """
    return RecurrenceCalculator.calculate_next_due_date(
        completed_at,
        recurrence_pattern,
    )


def format_next_occurrence(next_date: Optional[datetime]) -> str:
    """Format the next occurrence for display.

    Args:
        next_date: The next due date

    Returns:
        Human-readable string representation
    """
    if next_date is None:
        return "Does not repeat"

    now = datetime.now()

    if next_date.date() == now.date():
        return "Today"
    elif next_date.date() == (now + timedelta(days=1)).date():
        return "Tomorrow"
    elif next_date.date() == (now + timedelta(days=7)).date():
        return "In 1 week"
    else:
        # Format as "Mon, Jan 15" or similar
        return next_date.strftime("%a, %b %d")


def calculate_occurrences_until(
    start_date: datetime,
    end_date: datetime,
    frequency: str,
    day_of_week: Optional[int] = None,
    day_of_month: Optional[int] = None,
) -> list:
    """Calculate all occurrences between start and end dates.

    Args:
        start_date: Start of the range
        end_date: End of the range
        frequency: Recurrence frequency
        day_of_week: Day of week for weekly
        day_of_month: Day of month for monthly

    Returns:
        List of occurrence dates
    """
    occurrences = []
    current = start_date

    while current <= end_date:
        next_date = RecurrenceCalculator.calculate_next_due_date(
            current,
            frequency,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
        )
        if next_date and next_date <= end_date:
            occurrences.append(next_date)
            current = next_date
        else:
            break

    return occurrences
