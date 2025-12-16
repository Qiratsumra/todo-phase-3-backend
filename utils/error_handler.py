"""
Enhanced error handling and fallback system for API quota issues
Add this to your agents module or create a new utils/error_handler.py
"""

import logging
from typing import Optional, Dict, Any
import time
from functools import wraps

logger = logging.getLogger(__name__)


class APIQuotaError(Exception):
    """Custom exception for API quota issues"""
    def __init__(self, message: str, retry_after: int = 60):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)


class FallbackResponseGenerator:
    """Generate helpful fallback responses when API is unavailable"""
    
    @staticmethod
    def get_task_management_fallback(user_message: str) -> str:
        """Generate contextual fallback for task management queries"""
        message_lower = user_message.lower()
        
        # Detect intent from keywords
        if any(word in message_lower for word in ['create', 'add', 'new task']):
            return (
                "I'd like to help you create a task, but I'm currently experiencing "
                "API limitations. Please try one of these:\n\n"
                "• Use the task creation form directly in the UI\n"
                "• Try again in a few minutes\n"
                "• Or tell me: What task would you like to create? "
                "(title, description, priority, due date)"
            )
        
        elif any(word in message_lower for word in ['list', 'show', 'view', 'tasks']):
            return (
                "I can't fetch your tasks right now due to API limits, but you can:\n\n"
                "• View all tasks in the main dashboard\n"
                "• Refresh the page to see your latest tasks\n"
                "• Try asking again in a moment"
            )
        
        elif any(word in message_lower for word in ['update', 'edit', 'change', 'modify']):
            return (
                "I'm unable to process task updates at the moment. You can:\n\n"
                "• Edit tasks directly from the task list\n"
                "• Try again shortly\n"
                "• Let me know which task you want to update and I'll help once available"
            )
        
        elif any(word in message_lower for word in ['delete', 'remove', 'cancel']):
            return (
                "I can't process deletions right now due to API constraints. Instead:\n\n"
                "• Delete tasks using the delete button in the UI\n"
                "• Retry in a few minutes\n"
                "• Tell me which task to delete for when I'm back online"
            )
        
        elif any(word in message_lower for word in ['search', 'find']):
            return (
                "Search is temporarily unavailable. Meanwhile:\n\n"
                "• Use the search bar in the task dashboard\n"
                "• Filter tasks by status or priority\n"
                "• Try your search again shortly"
            )
        
        elif any(word in message_lower for word in ['recommend', 'suggest', 'priority']):
            return (
                "I can't provide recommendations right now, but here are some tips:\n\n"
                "• Focus on high-priority tasks first\n"
                "• Check tasks with approaching due dates\n"
                "• Review overdue tasks in your dashboard\n"
                "• I'll be able to give personalized suggestions soon!"
            )
        
        else:
            return (
                "I'm currently experiencing API limitations and can't process your request fully. "
                "However, you can:\n\n"
                "• Use the task management UI directly\n"
                "• Try again in a few minutes\n"
                "• Check https://status.google.com for Gemini API status\n\n"
                "Your data is safe, and I'll be back to help soon!"
            )
    
    @staticmethod
    def get_general_fallback() -> str:
        """Generic fallback message"""
        return (
            "I'm temporarily unable to process requests due to API quota limits. "
            "Please try again in a few minutes, or use the direct UI controls. "
            "Your data is safe and will be available when the service resumes."
        )


def handle_api_errors(fallback_type: str = "general"):
    """
    Decorator to handle API errors gracefully with fallback responses
    
    Args:
        fallback_type: Type of fallback to use ("task_management", "general")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a quota error (429)
                if "429" in error_str or "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                    logger.error(f"API quota exceeded in {func.__name__}: {error_str}")
                    
                    # Extract user message if available
                    user_message = ""
                    for arg in args:
                        if isinstance(arg, str) and len(arg) > 0 and len(arg) < 500:
                            user_message = arg
                            break
                    
                    # Generate appropriate fallback
                    if fallback_type == "task_management":
                        fallback_response = FallbackResponseGenerator.get_task_management_fallback(user_message)
                    else:
                        fallback_response = FallbackResponseGenerator.get_general_fallback()
                    
                    return {
                        "response": fallback_response,
                        "error": "quota_exceeded",
                        "retry_after": 60,
                        "fallback": True
                    }
                
                # For other errors, re-raise
                logger.error(f"Unexpected error in {func.__name__}: {error_str}")
                raise
        
        return wrapper
    return decorator


class RateLimiter:
    """Simple in-memory rate limiter to prevent quota exhaustion"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed for user"""
        current_time = time.time()
        
        # Initialize user if not exists
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests outside time window
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if current_time - req_time < self.time_window
        ]
        
        # Check if under limit
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(current_time)
            return True
        
        return False
    
    def get_retry_after(self, user_id: str) -> int:
        """Get seconds until user can make next request"""
        if user_id not in self.requests or not self.requests[user_id]:
            return 0
        
        oldest_request = min(self.requests[user_id])
        elapsed = time.time() - oldest_request
        return max(0, int(self.time_window - elapsed))


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=10, time_window=60)