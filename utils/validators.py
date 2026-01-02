"""Tag Validation Utilities for Task Management.

This module provides validation functions for task tags.

Tag Rules:
- Max 10 tags per task
- Tags must start with #
- Max 50 characters per tag
- Tags are case-insensitive for storage
"""

import re
import logging
from typing import List, Tuple, Optional, Set

logger = logging.getLogger("app")


# Constants
MAX_TAGS_PER_TASK = 10
MAX_TAG_LENGTH = 50
MIN_TAG_LENGTH = 2  # At least # + 1 character


class TagValidationError(Exception):
    """Exception raised for tag validation errors."""

    def __init__(self, message: str, code: str = "INVALID_TAG"):
        self.message = message
        self.code = code
        super().__init__(message)


def validate_tags(tags: List[str]) -> Tuple[bool, Optional[str], List[str]]:
    """Validate a list of tags.

    Args:
        tags: List of tag strings to validate

    Returns:
        Tuple of (is_valid, error_message, normalized_tags)
    """
    if not tags:
        return True, None, []

    # Convert to set to remove duplicates
    unique_tags = set()

    for tag in tags:
        is_valid, normalized, error = validate_single_tag(tag)
        if not is_valid:
            return False, error, []
        unique_tags.add(normalized)

    # Check max tags limit
    if len(unique_tags) > MAX_TAGS_PER_TASK:
        return False, f"Maximum {MAX_TAGS_PER_TASK} tags allowed", []

    return True, None, list(unique_tags)


def validate_single_tag(tag: str) -> Tuple[bool, Optional[str], str]:
    """Validate a single tag.

    Args:
        tag: Tag string to validate

    Returns:
        Tuple of (is_valid, error_message, normalized_tag)
    """
    if not tag:
        return False, "Tag cannot be empty", ""

    # Remove leading/trailing whitespace
    tag = tag.strip()

    # Check minimum length
    if len(tag) < MIN_TAG_LENGTH:
        return False, f"Tag must be at least {MIN_TAG_LENGTH} characters", ""

    # Check maximum length
    if len(tag) > MAX_TAG_LENGTH:
        return False, f"Tag must be at most {MAX_TAG_LENGTH} characters", ""

    # Check if it starts with #
    if not tag.startswith("#"):
        tag = f"#{tag}"

    # Validate tag format (alphanumeric, underscore, hyphen after #)
    pattern = r"^#[a-zA-Z0-9_\-]+$"
    if not re.match(pattern, tag):
        return False, "Tag can only contain letters, numbers, underscores, and hyphens", ""

    return True, None, tag.lower()


def normalize_tags(tags: List[str]) -> List[str]:
    """Normalize a list of tags.

    - Adds # prefix if missing
    - Converts to lowercase
    - Removes duplicates

    Args:
        tags: List of tag strings

    Returns:
        Normalized list of tags
    """
    unique_tags = set()

    for tag in tags:
        if not tag.startswith("#"):
            tag = f"#{tag}"
        unique_tags.add(tag.lower())

    return list(unique_tags)


def extract_tags_from_text(text: str) -> List[str]:
    """Extract tags from natural language text.

    Args:
        text: Text that may contain tags

    Returns:
        List of extracted tags
    """
    if not text:
        return []

    # Find all patterns that look like tags
    pattern = r"#(\w+)"
    matches = re.findall(pattern, text)

    # Normalize and return
    return [f"#{match.lower()}" for match in matches]


def parse_tag_string(tag_string: str) -> List[str]:
    """Parse a comma or space-separated string of tags.

    Args:
        tag_string: String like "#work, #urgent, #important" or "#work #urgent"

    Returns:
        List of individual tags
    """
    if not tag_string:
        return []

    # Split by comma or whitespace
    raw_tags = re.split(r"[,\s]+", tag_string)

    # Filter and normalize
    tags = []
    for tag in raw_tags:
        tag = tag.strip()
        if tag:
            if not tag.startswith("#"):
                tag = f"#{tag}"
            tags.append(tag.lower())

    return list(set(tags))  # Remove duplicates


def get_common_tags() -> List[str]:
    """Get a list of common/predefined tags.

    Returns:
        List of suggested tags
    """
    return [
        "#work",
        "#personal",
        "#urgent",
        "#important",
        "#home",
        "#shopping",
        "#health",
        "#finance",
        "#learning",
        "#travel",
        "#meetings",
        "#deadline",
        "#project",
        "#ideas",
        "#followup",
    ]


def validate_priority(priority: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate a priority value.

    Args:
        priority: Priority string (low, medium, high)

    Returns:
        Tuple of (is_valid, error_message, normalized_priority)
    """
    valid_priorities = {"low", "medium", "high"}

    priority_lower = priority.lower().strip()

    if priority_lower not in valid_priorities:
        return False, f"Invalid priority. Must be one of: {', '.join(valid_priorities)}", None

    return True, None, priority_lower


class PriorityValidator:
    """Validator for task priorities."""

    @staticmethod
    def validate(priority: str) -> Tuple[bool, Optional[str]]:
        """Validate a priority value."""
        return validate_priority(priority)

    @staticmethod
    def get_valid_options() -> List[str]:
        """Get valid priority options."""
        return ["low", "medium", "high"]

    @staticmethod
    def get_weight(priority: str) -> int:
        """Get numeric weight for priority (for sorting)."""
        weights = {"low": 1, "medium": 2, "high": 3}
        return weights.get(priority.lower(), 0)


def merge_tags(existing_tags: List[str], tags_to_add: List[str]) -> List[str]:
    """Merge new tags with existing tags.

    Args:
        existing_tags: Current tags on the task
        tags_to_add: New tags to add

    Returns:
        Combined list of tags (unique)
    """
    existing = set(normalize_tags(existing_tags))
    to_add = set(normalize_tags(tags_to_add))

    combined = existing.union(to_add)

    # Limit to max tags
    return list(combined)[:MAX_TAGS_PER_TASK]


def remove_tags(existing_tags: List[str], tags_to_remove: List[str]) -> List[str]:
    """Remove tags from existing tags.

    Args:
        existing_tags: Current tags on the task
        tags_to_remove: Tags to remove

    Returns:
        List of remaining tags
    """
    existing = set(normalize_tags(existing_tags))
    to_remove = set(normalize_tags(tags_to_remove))

    remaining = existing - to_remove

    return list(remaining)
