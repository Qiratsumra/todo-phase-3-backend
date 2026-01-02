"""
TaskAnalyticsSkill - Provides task statistics and productivity insights.
"""

import json
from typing import List, Dict, Any
import logging

from .base_skill import BaseSkill
from agents.agent_config import get_chat_completion
from mcp_tools.tool_definitions import SKILL_TOOLS, execute_tool

logger = logging.getLogger("agents.skills.task_analytics")

# Keywords that indicate analytics intent
ANALYTICS_KEYWORDS = [
    "how many", "count", "total",
    "completion rate", "percentage", "percent",
    "statistics", "stats", "analytics",
    "productivity", "progress", "trend",
    "completed this", "done this"
]

SYSTEM_PROMPT = """You are a data analyst specializing in productivity metrics. Your job is to provide insights about task completion patterns.

You can:
- Get task statistics (get_task_stats)
- Calculate completion rates
- Show productivity trends
- Analyze task distribution by priority

Guidelines:
- Present data clearly and concisely
- Use numbers and percentages
- Offer actionable insights when relevant
- Format statistics in an easy-to-read way
- Compare current performance to goals if asked

Always use the get_task_stats tool to get accurate data. Don't make up numbers."""


class TaskAnalyticsSkill(BaseSkill):
    """Skill for task analytics and statistics."""

    def __init__(self):
        super().__init__(
            name="TaskAnalyticsSkill",
            description="Provides statistics, completion rates, and productivity insights",
            tools=SKILL_TOOLS.get("TaskAnalyticsSkill", [])
        )

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def can_handle(self, user_message: str) -> bool:
        """Check if message contains analytics-related keywords."""
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in ANALYTICS_KEYWORDS)

    def get_confidence(self, user_message: str) -> float:
        """Calculate confidence based on keyword matches."""
        message_lower = user_message.lower()
        matches = sum(1 for kw in ANALYTICS_KEYWORDS if kw in message_lower)
        return min(1.0, matches * 0.4)

    async def process(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        db
    ) -> Dict[str, Any]:
        """Process analytics query using Gemini with stats tools."""

        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": user_message})

        tool_calls_made = []

        try:
            response = await get_chat_completion(
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

                    logger.info(f"Executing analytics tool: {tool_name}")
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

                final_response = await get_chat_completion(messages=messages)
                content = final_response.choices[0].message.content
            else:
                content = assistant_message.content

            return {
                "content": content or "Here are your task statistics.",
                "tool_calls": tool_calls_made
            }

        except Exception as e:
            logger.error(f"Error in TaskAnalyticsSkill: {e}")
            return {
                "content": f"I encountered an error getting statistics: {str(e)}",
                "tool_calls": tool_calls_made
            }
