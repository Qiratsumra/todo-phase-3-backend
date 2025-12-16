"""
Tool definitions for Gemini function calling.
Aggregates all MCP tool definitions.
"""

from . import add_task, list_tasks, complete_task, delete_task, update_task, search_tasks, get_task_stats

# All tool definitions for Gemini
TOOLS = [
    add_task.TOOL_DEFINITION,
    list_tasks.TOOL_DEFINITION,
    complete_task.TOOL_DEFINITION,
    delete_task.TOOL_DEFINITION,
    update_task.TOOL_DEFINITION,
    search_tasks.TOOL_DEFINITION,
    get_task_stats.TOOL_DEFINITION,
]

# Tool name to module mapping for execution
TOOL_EXECUTORS = {
    "add_task": add_task.execute,
    "list_tasks": list_tasks.execute,
    "complete_task": complete_task.execute,
    "delete_task": delete_task.execute,
    "update_task": update_task.execute,
    "search_tasks": search_tasks.execute,
    "get_task_stats": get_task_stats.execute,
}

# Skill-to-tools mapping
SKILL_TOOLS = {
    "TaskManagementSkill": [
        add_task.TOOL_DEFINITION,
        list_tasks.TOOL_DEFINITION,
        complete_task.TOOL_DEFINITION,
        delete_task.TOOL_DEFINITION,
        update_task.TOOL_DEFINITION,
    ],
    "TaskSearchSkill": [
        search_tasks.TOOL_DEFINITION,
        list_tasks.TOOL_DEFINITION,
    ],
    "TaskAnalyticsSkill": [
        get_task_stats.TOOL_DEFINITION,
        list_tasks.TOOL_DEFINITION,
    ],
    "TaskRecommendationSkill": [
        list_tasks.TOOL_DEFINITION,
        get_task_stats.TOOL_DEFINITION,
    ],
}


def get_tools_for_skill(skill_name: str) -> list:
    """Get tool definitions for a specific skill."""
    return SKILL_TOOLS.get(skill_name, TOOLS)


def execute_tool(tool_name: str, db, **kwargs) -> dict:
    """Execute a tool by name with provided arguments."""
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    return executor(db, **kwargs)
