"""
TaskManagementSkill - Handles CRUD operations for tasks.
"""

import re
import json
from typing import List, Dict, Any
import logging

from .base_skill import BaseSkill
from agents.agent_config import get_chat_completion
from mcp_tools.tool_definitions import SKILL_TOOLS, execute_tool

logger = logging.getLogger("agents.skills.task_management")

# Keywords that indicate task management intent
CRUD_KEYWORDS = [
    "add", "create", "new", "make",
    "delete", "remove", "destroy",
    "complete", "done", "finish", "mark",
    "update", "edit", "change", "modify",
    "list", "show", "display", "see", "what", "my tasks"
]

SYSTEM_PROMPT = """You are a friendly task management assistant. Your job is to help users manage their tasks efficiently.

You can:
- Create new tasks (add_task)
- List existing tasks (list_tasks)
- Mark tasks as complete (complete_task)
- Delete tasks (delete_task)
- Update task details (update_task)

Guidelines:
- Be friendly and use emojis occasionally
- Confirm actions with clear feedback
- When listing tasks, format them nicely
- If a task isn't found, suggest listing tasks first
- For ambiguous task references, ask for clarification

Priority levels: 0=none, 1=low, 2=medium, 3=high

Always use the available tools to perform actions. Don't just describe what you would do - actually do it."""


class TaskManagementSkill(BaseSkill):
    """Skill for handling task CRUD operations."""

    def __init__(self):
        super().__init__(
            name="TaskManagementSkill",
            description="Handles creating, listing, completing, deleting, and updating tasks",
            tools=SKILL_TOOLS.get("TaskManagementSkill", [])
        )

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def can_handle(self, user_message: str) -> bool:
        """Check if message contains CRUD-related keywords."""
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in CRUD_KEYWORDS)

    def get_confidence(self, user_message: str) -> float:
        """Calculate confidence based on keyword matches."""
        message_lower = user_message.lower()
        matches = sum(1 for kw in CRUD_KEYWORDS if kw in message_lower)
        return min(1.0, matches * 0.3)

    async def process(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        db
    ) -> Dict[str, Any]:
        """Process the user message using Gemini with function calling."""

        # Build messages for LLM
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        messages.extend(conversation_history[-10:])  # Last 10 messages for context
        messages.append({"role": "user", "content": user_message})

        tool_calls_made = []

        try:
            # Call Gemini with tools
            response = get_chat_completion(
                messages=messages,
                tools=self.tools
            )

            assistant_message = response.choices[0].message

            # Handle tool calls if any
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Execute the tool
                    result = execute_tool(tool_name, db, **tool_args)

                    tool_calls_made.append({
                        "name": tool_name,
                        "arguments": tool_args,
                        "result": result
                    })

                # Get final response with tool results
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

                # Get final response
                final_response = get_chat_completion(messages=messages)
                content = final_response.choices[0].message.content

            else:
                content = assistant_message.content

            return {
                "content": content or "I've completed the task operation.",
                "tool_calls": tool_calls_made
            }

        except Exception as e:
            logger.error(f"Error in TaskManagementSkill: {e}")
            # Re-raise quota errors for MainAgent to handle
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                raise

            return {
                "content": f"I encountered an error: {str(e)}. Please try again.",
                "tool_calls": tool_calls_made
            }

    def _get_fallback_response(self, user_message: str) -> str:
    # Add your custom logic here
        if "urgent" in user_message.lower():
            return "For urgent tasks, please use the Quick Add button..."
