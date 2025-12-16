"""
Configuration file for API settings and fallback behavior
Save as config/settings.py or similar
"""

import os
from typing import Optional

class Settings:
    """Application settings with fallback configuration"""
    
    # API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Model selection (use lite to save quota)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
    
    # Fallback configuration
    ENABLE_FALLBACK: bool = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
    FALLBACK_MODE: str = os.getenv("FALLBACK_MODE", "smart")  # "smart", "always", "never"
    
    # Rate limiting (requests per minute per user)
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    # API retry configuration
    MAX_API_RETRIES: int = int(os.getenv("MAX_API_RETRIES", "2"))
    API_RETRY_DELAY: int = int(os.getenv("API_RETRY_DELAY", "2"))  # seconds
    
    # Token limits (to save quota)
    MAX_TOKENS_PER_REQUEST: int = int(os.getenv("MAX_TOKENS_PER_REQUEST", "500"))
    MAX_CONTEXT_TASKS: int = int(os.getenv("MAX_CONTEXT_TASKS", "10"))
    
    # Graceful degradation
    GRACEFUL_DEGRADATION: bool = os.getenv("GRACEFUL_DEGRADATION", "true").lower() == "true"
    
    # Monitoring
    LOG_API_ERRORS: bool = os.getenv("LOG_API_ERRORS", "true").lower() == "true"
    LOG_QUOTA_WARNINGS: bool = os.getenv("LOG_QUOTA_WARNINGS", "true").lower() == "true"
    
    @classmethod
    def get_fallback_message(cls, context: str = "general") -> str:
        """Get appropriate fallback message based on context"""
        if not cls.ENABLE_FALLBACK:
            return "Service temporarily unavailable. Please try again later."
        
        messages = {
            "quota_exceeded": (
                "🔄 **API Quota Reached**\n\n"
                "I'm temporarily limited by API quotas, but you have full access to all features through the UI!\n\n"
                "**What works:**\n"
                "✅ Creating, editing, and deleting tasks\n"
                "✅ Searching and filtering\n"
                "✅ All task management features\n\n"
                "**When will AI chat return?**\n"
                "Usually within 2-5 minutes. Your data is safe and I'll be back soon! 💪"
            ),
            "rate_limited": (
                "⏱️ **Slow Down There!**\n\n"
                "To preserve API quota for everyone, please wait a moment between requests.\n\n"
                "Meanwhile, use the UI buttons and forms for instant task management! ⚡"
            ),
            "api_error": (
                "⚠️ **Temporary Issue**\n\n"
                "I encountered an error, but all UI features work perfectly!\n\n"
                "Try again in a moment, or manage tasks directly through the interface. 👍"
            ),
        }
        
        return messages.get(context, messages["api_error"])
    
    @classmethod
    def should_use_fallback(cls, error: Exception) -> bool:
        """Determine if fallback should be used based on error"""
        if not cls.ENABLE_FALLBACK:
            return False
        
        error_str = str(error).lower()
        
        # Always use fallback for quota errors
        if any(indicator in error_str for indicator in ["429", "quota", "resource_exhausted"]):
            return True
        
        # Use fallback for rate limits if enabled
        if cls.GRACEFUL_DEGRADATION and "rate limit" in error_str:
            return True
        
        # Smart mode: use fallback for common API errors
        if cls.FALLBACK_MODE == "smart":
            return any(indicator in error_str for indicator in [
                "timeout", "connection", "unavailable", "503", "502", "500"
            ])
        
        # Always mode: use fallback for any error
        if cls.FALLBACK_MODE == "always":
            return True
        
        return False


# Create global settings instance
settings = Settings()


# Environment variable template for .env file
ENV_TEMPLATE = """
# API Configuration
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash-lite

# Fallback Settings
ENABLE_FALLBACK=true
FALLBACK_MODE=smart
GRACEFUL_DEGRADATION=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# API Retry
MAX_API_RETRIES=2
API_RETRY_DELAY=2

# Token Management
MAX_TOKENS_PER_REQUEST=500
MAX_CONTEXT_TASKS=10

# Monitoring
LOG_API_ERRORS=true
LOG_QUOTA_WARNINGS=true
"""