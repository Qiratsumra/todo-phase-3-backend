"""
Base Skill class - Abstract base for all skill agents.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("agents.skills")


class BaseSkill(ABC):
    """
    Abstract base class for skill agents.

    Each skill is a specialized agent that handles a specific domain
    of user intents (e.g., task management, search, analytics).
    """

    def __init__(self, name: str, description: str, tools: List[dict]):
        """
        Initialize the skill.

        Args:
            name: Unique name of the skill (e.g., "TaskManagementSkill")
            description: Brief description of what this skill handles
            tools: List of tool definitions this skill can use
        """
        self.name = name
        self.description = description
        self.tools = tools
        logger.info(f"Initialized skill: {name}")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this skill.

        Returns:
            System prompt string that defines the skill's behavior
        """
        pass

    @abstractmethod
    def can_handle(self, user_message: str) -> bool:
        """
        Check if this skill can handle the given user message.

        Args:
            user_message: The user's input message

        Returns:
            True if this skill should handle the message
        """
        pass

    @abstractmethod
    async def process(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        db
    ) -> Dict[str, Any]:
        """
        Process the user message and return a response.

        Args:
            user_message: The user's input message
            conversation_history: List of previous messages
            db: Database session for tool execution

        Returns:
            Dict containing:
                - content: Response text
                - tool_calls: List of tools that were called (optional)
        """
        pass

    def get_confidence(self, user_message: str) -> float:
        """
        Get confidence score for handling this message.

        Override this method to provide more nuanced routing.

        Args:
            user_message: The user's input message

        Returns:
            Confidence score from 0.0 to 1.0
        """
        return 1.0 if self.can_handle(user_message) else 0.0

    def __repr__(self) -> str:
        return f"<{self.name}: {self.description}>"
