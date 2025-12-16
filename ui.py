from typing import List, Optional, Tuple
import uuid
from datetime import date, datetime
from rich.console import Console
from rich.table import Table
from .models import Task


console = Console()


def display_tasks(tasks: List[Task]):
    """Displays a list of tasks in a table."""
    if not tasks:
        console.print("No tasks yet.", style="bold yellow")
        return

    table = Table(title="Todo List")
    table.add_column("ID", style="dim", width=36)
    table.add_column("Title", min_width=20)
    table.add_column("Priority", width=10)
    table.add_column("Due Date", width=12)
    table.add_column("Recurrence", width=15)
    table.add_column("Next Recur.", width=12)
    table.add_column("Tags", width=20)
    table.add_column("Completed", justify="right")

    for task in tasks:
        completed_str = "✅" if task.completed else "❌"
        priority_str = (
            "High" if task.priority == 1 else "Medium" if task.priority == 2 else "Low"
        )
        due_date_str = task.due_date.strftime("%Y-%m-%d") if task.due_date else "None"
        recurrence_pattern_str = task.recurrence_pattern if task.recurrence_pattern else "None"
        next_recurrence_date_str = task.next_recurrence_date.strftime("%Y-%m-%d") if task.next_recurrence_date else "None"
        tags_str = ", ".join(task.tags)
        table.add_row(
            str(task.id),
            task.title,
            priority_str,
            due_date_str,
            recurrence_pattern_str,
            next_recurrence_date_str,
            tags_str,
            completed_str,
        )

    console.print(table)


def get_new_task_details() -> Tuple[str, str, int, Optional[date], List[str], Optional[str], Optional[date], Optional[date], Optional[datetime]]:
    """Gets the details for a new task from the user."""
    title = console.input("Enter task title: ")
    description = console.input("Enter task description: ")
    priority = int(console.input("Enter priority (1-High, 2-Medium, 3-Low): "))

    due_date_str = console.input("Enter due date (YYYY-MM-DD) or leave blank: ")
    due_date = (
        datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None
    )

    reminder_time_str = console.input("Enter reminder time (YYYY-MM-DD HH:MM) or leave blank: ")
    reminder_time = (
        datetime.strptime(reminder_time_str, "%Y-%m-%d %H:%M") if reminder_time_str else None
    )

    tags_str = console.input("Enter tags (comma-separated): ")
    tags = [tag.strip() for tag in tags_str.split(",")]

    recurrence_pattern = console.input("Enter recurrence pattern (daily, weekly, monthly, yearly) or leave blank: ")
    recurrence_start_date_str = console.input("Enter recurrence start date (YYYY-MM-DD) or leave blank: ")
    recurrence_start_date = (
        datetime.strptime(recurrence_start_date_str, "%Y-%m-%d").date() if recurrence_start_date_str else None
    )
    recurrence_end_date_str = console.input("Enter recurrence end date (YYYY-MM-DD) or leave blank: ")
    recurrence_end_date = (
        datetime.strptime(recurrence_end_date_str, "%Y-%m-%d").date() if recurrence_end_date_str else None
    )

    return title, description, priority, due_date, tags, recurrence_pattern, recurrence_start_date, recurrence_end_date, reminder_time


def get_task_id() -> uuid.UUID:
    """Gets a task ID from the user."""
    while True:
        try:
            task_id_str = console.input("Enter task ID: ")
            return uuid.UUID(task_id_str)
        except ValueError:
            console.print("Invalid UUID format. Please try again.", style="bold red")


def get_update_task_details() -> Tuple[str, str, int, Optional[date], List[str], Optional[str], Optional[date], Optional[date], Optional[datetime]]:
    """Gets the new details for a task from the user."""
    title = console.input("Enter new task title: ")
    description = console.input("Enter new task description: ")
    priority = int(console.input("Enter new priority (1-High, 2-Medium, 3-Low): "))

    due_date_str = console.input("Enter new due date (YYYY-MM-DD) or leave blank: ")
    due_date = (
        datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None
    )

    reminder_time_str = console.input("Enter new reminder time (YYYY-MM-DD HH:MM) or leave blank: ")
    reminder_time = (
        datetime.strptime(reminder_time_str, "%Y-%m-%d %H:%M") if reminder_time_str else None
    )

    tags_str = console.input("Enter new tags (comma-separated): ")
    tags = [tag.strip() for tag in tags_str.split(",")]

    recurrence_pattern = console.input("Enter new recurrence pattern (daily, weekly, monthly, yearly) or leave blank: ")
    recurrence_start_date_str = console.input("Enter new recurrence start date (YYYY-MM-DD) or leave blank: ")
    recurrence_start_date = (
        datetime.strptime(recurrence_start_date_str, "%Y-%m-%d").date() if recurrence_start_date_str else None
    )
    recurrence_end_date_str = console.input("Enter new recurrence end date (YYYY-MM-DD) or leave blank: ")
    recurrence_end_date = (
        datetime.strptime(recurrence_end_date_str, "%Y-%m-%d").date() if recurrence_end_date_str else None
    )

    return title, description, priority, due_date, tags, recurrence_pattern, recurrence_start_date, recurrence_end_date, reminder_time


def display_menu():
    """Displays the main menu."""
    console.print("\n[bold cyan]Menu:[/bold cyan]")
    console.print("1. Add task")
    console.print("2. View all tasks")
    console.print("3. Mark task as complete")
    console.print("4. Update task")
    console.print("5. Delete task")
    console.print("6. Search tasks")
    console.print("7. Filter tasks")
    console.print("8. Sort tasks")
    console.print("9. Exit")


def get_menu_choice() -> str:
    """Gets the user's menu choice."""
    return console.input("Enter your choice: ")


def show_confirmation(message: str):
    """Displays a confirmation message."""
    console.print(message, style="bold green")


def show_error(message: str):
    """Displays an error message."""
    console.print(message, style="bold red")


def get_search_keyword() -> str:
    """Gets a search keyword from the user."""
    return console.input("Enter search keyword: ")


def get_filter_options() -> Tuple[Optional[bool], Optional[int], Optional[str]]:
    """Gets filtering options from the user."""
    status_str = console.input(
        "Filter by status (completed/pending/any): "
    ).lower()
    status = (
        True
        if status_str == "completed"
        else False
        if status_str == "pending"
        else None
    )
    priority_str = console.input(
        "Filter by priority (High/Medium/Low/any): "
    ).lower()
    priority = (
        1
        if priority_str == "high"
        else 2
        if priority_str == "medium"
        else 3
        if priority_str == "low"
        else None
    )
    tag = console.input("Filter by tag (or leave blank): ")
    return status, priority, tag or None


def get_sort_options() -> Tuple[str, bool]:
    """Gets sorting options from the user."""
    sort_by = console.input(
        "Sort by (due_date/priority/title/created_at): "
    ).lower()
    reverse_str = console.input("Sort in reverse order? (yes/no): ").lower()
    reverse = reverse_str == "yes"
    return sort_by, reverse


def show_reminder_notification(task: Task):
    """Displays a reminder notification for a task."""
    console.print(f"\n🔔 [bold yellow]REMINDER:[/bold yellow] Task '[cyan]{task.title}[/cyan]' is due at [green]{task.reminder_time.strftime("%Y-%m-%d %H:%M")}[/green]!", style="bold")
