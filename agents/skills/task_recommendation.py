"""
TaskRecommendationSkill - Provides smart suggestions and priorities.
"""

import json
from typing import List, Dict, Any
import logging

from .base_skill import BaseSkill
from agents.agent_config import get_chat_completion
from mcp_tools.tool_definitions import SKILL_TOOLS, execute_tool

logger = logging.getLogger("agents.skills.task_recommendation")

# Keywords that indicate recommendation intent
RECOMMENDATION_KEYWORDS = [
    "what should", "suggest", "recommend",
    "prioritize", "priority", "focus",
    "next", "work on", "important",
    "help me decide", "which task"
]

SYSTEM_PROMPT = """You are a productivity coach helping users prioritize their work. Your job is to provide smart suggestions based on their task list.

You can:
- Analyze tasks to suggest priorities (list_tasks, get_task_stats)
- Recommend what to work on next
- Help with task prioritization
- Identify overdue or urgent tasks

Guidelines:
- Consider due dates, priorities, and completion status
- Suggest high-priority and overdue tasks first
- Provide actionable advice
- Be encouraging and supportive
- Explain your reasoning briefly

Always fetch the actual task list before making recommendations. Don't guess."""


class TaskRecommendationSkill(BaseSkill):
    """Skill for smart task recommendations and prioritization."""

    def __init__(self):
        super().__init__(
            name="TaskRecommendationSkill",
            description="Provides smart suggestions, prioritization advice, and next-action recommendations",
            tools=SKILL_TOOLS.get("TaskRecommendationSkill", [])
        )

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def can_handle(self, user_message: str) -> bool:
        """Check if message contains recommendation-related keywords."""
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in RECOMMENDATION_KEYWORDS)

    def get_confidence(self, user_message: str) -> float:
        """Calculate confidence based on keyword matches."""
        message_lower = user_message.lower()
        matches = sum(1 for kw in RECOMMENDATION_KEYWORDS if kw in message_lower)
        return min(1.0, matches * 0.4)

    async def process(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        db
    ) -> Dict[str, Any]:
        """Process recommendation query using Gemini with task tools."""

        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": user_message})

        tool_calls_made = []

        try:
            response = get_chat_completion(
                messages=messages,
                tools=self.tools
            )

            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info(f"Executing recommendation tool: {tool_name}")
                    result = execute_tool(tool_name, db, **tool_args)

                    tool_calls_made.append({
                        "name": tool_name,
                        "arguments": tool_args,
                        "result": result
                    })

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                for i, tc in enumerate(assistant_message.tool_calls):
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_calls_made[i]["result"])
                    })

                final_response = get_chat_completion(messages=messages)
                content = final_response.choices[0].message.content
            else:
                content = assistant_message.content

            return {
                "content": content or "Here are my recommendations based on your tasks.",
                "tool_calls": tool_calls_made
            }

        except Exception as e:
            logger.error(f"Error in TaskRecommendationSkill: {e}")
            return {
                "content": f"I encountered an error making recommendations: {str(e)}",
                "tool_calls": tool_calls_made
            }
