"""
TaskSearchSkill - Handles advanced task search and filtering.
"""

import json
from typing import List, Dict, Any
import logging

from .base_skill import BaseSkill
from agents.agent_config import get_chat_completion
from mcp_tools.tool_definitions import SKILL_TOOLS, execute_tool

logger = logging.getLogger("agents.skills.task_search")

# Keywords that indicate search intent
SEARCH_KEYWORDS = [
    "find", "search", "look for", "where",
    "filter", "show me", "which tasks",
    "containing", "with", "that have",
    "from", "between", "before", "after"
]

SYSTEM_PROMPT = """You are a search expert for a todo application. Your job is to help users find tasks using complex queries.

You can:
- Search tasks by keyword in title/description (search_tasks)
- Filter by completion status, priority, date range
- List all tasks with filters (list_tasks)

Guidelines:
- Understand natural language search queries
- Use appropriate filters based on user intent
- Format search results clearly
- If no results found, suggest broadening the search
- Use the search_tasks tool for keyword searches
- Use list_tasks for simple filtering

Always use the available tools to search. Don't just describe what you would search for - actually search."""


class TaskSearchSkill(BaseSkill):
    """Skill for advanced task search and filtering."""

    def __init__(self):
        super().__init__(
            name="TaskSearchSkill",
            description="Handles advanced search with keywords, date ranges, and filters",
            tools=SKILL_TOOLS.get("TaskSearchSkill", [])
        )

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def can_handle(self, user_message: str) -> bool:
        """Check if message contains search-related keywords."""
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in SEARCH_KEYWORDS)

    def get_confidence(self, user_message: str) -> float:
        """Calculate confidence based on keyword matches."""
        message_lower = user_message.lower()
        matches = sum(1 for kw in SEARCH_KEYWORDS if kw in message_lower)
        return min(1.0, matches * 0.35)

    async def process(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        db
    ) -> Dict[str, Any]:
        """Process search query using Gemini with search tools."""

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

                    logger.info(f"Executing search tool: {tool_name}")
                    result = execute_tool(tool_name, db, **tool_args)

                    tool_calls_made.append({
                        "name": tool_name,
                        "arguments": tool_args,
                        "result": result
                    })

                # Build tool response messages
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
                "content": content or "Search completed.",
                "tool_calls": tool_calls_made
            }

        except Exception as e:
            logger.error(f"Error in TaskSearchSkill: {e}")
            return {
                "content": f"I encountered an error while searching: {str(e)}",
                "tool_calls": tool_calls_made
            }
