# ========================================================================
# Next Occurrence Calculator
# ========================================================================

import logging
from datetime import datetime
from typing import Optional
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class NextOccurrenceScheduler:
    """Calculates next occurrence for recurring tasks."""

    PATTERNS = ["daily", "weekdays", "weekly", "biweekly", "monthly", "quarterly", "yearly"]

    def calculate_next_occurrence(self, recurrence: str, from_date: str = None) -> Optional[datetime]:
        """Calculate next occurrence date based on recurrence pattern."""
        try:
            if from_date:
                current = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
            else:
                current = datetime.utcnow()

            recurrence = recurrence.lower().strip()

            patterns = {
                "daily": lambda: current + relativedelta(days=1),
                "weekdays": self._next_weekday,
                "weekly": lambda: current + relativedelta(weeks=1),
                "biweekly": lambda: current + relativedelta(weeks=2),
                "monthly": lambda: current + relativedelta(months=1),
                "quarterly": lambda: current + relativedelta(months=3),
                "yearly": lambda: current + relativedelta(years=1),
            }

            if recurrence in patterns:
                return patterns[recurrence]()

            # Custom pattern: "every N days/weeks/months"
            import re
            match = re.match(r"every\s+(\d+)\s+(\w+)", recurrence)
            if match:
                count, unit = int(match.group(1)), match.group(2)
                if "day" in unit:
                    return current + relativedelta(days=count)
                elif "week" in unit:
                    return current + relativedelta(weeks=count)
                elif "month" in unit:
                    return current + relativedelta(months=count)

            return None
        except Exception as e:
            logger.error(f"Error calculating next occurrence: {e}")
            return None

    def _next_weekday(self, current: datetime) -> datetime:
        """Get next weekday (Mon-Fri)."""
        days_ahead = 1
        while (current.weekday() + days_ahead) % 7 > 4:
            days_ahead += 1
        return current + relativedelta(days=days_ahead)

    def is_recurring(self, recurrence: str) -> bool:
        """Check if task has a recurring pattern."""
        if not recurrence:
            return False
        return recurrence.lower() in self.PATTERNS or recurrence.lower().startswith("every ")
