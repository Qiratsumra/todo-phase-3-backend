"""
Main Agent - Intent router that delegates to specialized skill agents.
"""

from typing import List, Dict, Any, Optional
import logging

from .skills.task_management import TaskManagementSkill
from .skills.task_search import TaskSearchSkill
from .skills.task_analytics import TaskAnalyticsSkill
from .skills.task_recommendation import TaskRecommendationSkill
from .skills.base_skill import BaseSkill
from utils.api_monitor import api_monitor

logger = logging.getLogger("agents.main_agent")


class MainAgent:
    """
    Main agent that routes user intents to specialized skill agents.

    The main agent analyzes user messages and delegates to the most
    appropriate skill based on keyword matching and confidence scores.
    """

    def __init__(self):
        """Initialize the main agent with all skill agents."""
        self.skills: List[BaseSkill] = [
            TaskManagementSkill(),
            TaskSearchSkill(),
            TaskAnalyticsSkill(),
            TaskRecommendationSkill(),
        ]

        # Default skill for fallback
        self.default_skill = self.skills[0]  # TaskManagementSkill

        logger.info(f"MainAgent initialized with {len(self.skills)} skills")

    def route_intent(self, user_message: str) -> BaseSkill:
        """
        Route user message to the most appropriate skill.

        Uses keyword-based matching with confidence scores.
        Falls back to TaskManagementSkill for ambiguous messages.

        Args:
            user_message: The user's input message

        Returns:
            The skill that should handle this message
        """
        best_skill = self.default_skill
        best_confidence = 0.0

        for skill in self.skills:
            confidence = skill.get_confidence(user_message)
            if confidence > best_confidence:
                best_confidence = confidence
                best_skill = skill

        # Use default if confidence is too low
        if best_confidence < 0.1:
            logger.info(f"Low confidence ({best_confidence}), using default skill")
            return self.default_skill

        logger.info(f"Routed to {best_skill.name} (confidence: {best_confidence:.2f})")
        return best_skill

    async def process_message(
        self,
        user_id: str,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        db
    ) -> Dict[str, Any]:
        """
        Process a user message and return the response.

        1. Routes to appropriate skill
        2. Calls skill.process()
        3. Adds skill_used to response

        Args:
            user_id: ID of the user
            user_message: The user's input message
            conversation_history: List of previous messages
            db: Database session for tool execution

        Returns:
            Dict containing:
                - content: Response text
                - tool_calls: List of tools called
                - skill_used: Name of the skill that processed this
        """
        try:
            # Check if user is rate limited
            if api_monitor.is_user_rate_limited(user_id, max_requests=10, window_minutes=1):
                 return {
                    "content": "Please wait a moment before sending another message. This helps us manage API quotas.",
                    "tool_calls": [],
                    "skill_used": "RateLimiter"
                }

            # Route to appropriate skill
            skill = self.route_intent(user_message)

            logger.info(f"Processing message for user {user_id} with {skill.name}")

            # Process with the selected skill
            result = await skill.process(
                user_message=user_message,
                conversation_history=conversation_history,
                db=db
            )

            # Add skill tracking
            result["skill_used"] = skill.name
            
            # Log successful request
            api_monitor.log_request(user_id, model="gemini", success=True)

            return result

        except Exception as e:
            # Log error
            api_monitor.log_error(user_id, type(e).__name__, str(e))
            
            # Check if we should use fallback
            if "429" in str(e) or "quota" in str(e).lower() or "resource_exhausted" in str(e).lower():
                from config.settings import settings
                return {
                    "content": settings.get_fallback_message("quota_exceeded"),
                    "tool_calls": [],
                    "skill_used": "Fallback"
                }
            raise

    def get_skill_info(self) -> List[Dict[str, str]]:
        """Get information about available skills."""
        return [
            {
                "name": skill.name,
                "description": skill.description
            }
            for skill in self.skills
        ]


# Singleton instance
_main_agent: Optional[MainAgent] = None


def get_main_agent() -> MainAgent:
    """Get or create the main agent singleton."""
    global _main_agent
    if _main_agent is None:
        _main_agent = MainAgent()
    return _main_agent

