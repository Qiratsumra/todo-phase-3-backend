"""
API Usage Monitor - Track quota usage and provide insights
Save as utils/api_monitor.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class APIUsageMonitor:
    """Monitor and track API usage to prevent quota exhaustion"""
    
    def __init__(self):
        self.requests_log: List[Dict] = []
        self.errors_log: List[Dict] = []
        self.quota_warnings: List[Dict] = []
        self.user_requests: Dict[str, List[datetime]] = defaultdict(list)
        
        # Thresholds
        self.warning_threshold = 0.8  # Warn at 80% of estimated quota
        self.critical_threshold = 0.95  # Critical at 95%
    
    def log_request(self, user_id: str, model: str, tokens_used: int = 0, success: bool = True):
        """Log an API request"""
        request_data = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "model": model,
            "tokens": tokens_used,
            "success": success
        }
        
        self.requests_log.append(request_data)
        self.user_requests[user_id].append(datetime.now())
        
        # Clean old logs (keep last 24 hours)
        self._cleanup_old_logs()
    
    def log_error(self, user_id: str, error_type: str, error_message: str):
        """Log an API error"""
        error_data = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "error_type": error_type,
            "message": error_message
        }
        
        self.errors_log.append(error_data)
        
        # Check if it's a quota error
        if "429" in error_message or "quota" in error_message.lower():
            self._log_quota_warning(user_id, error_message)
        
        logger.error(f"API Error for {user_id}: {error_type} - {error_message}")
    
    def _log_quota_warning(self, user_id: str, message: str):
        """Log quota-related warnings"""
        warning = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "message": message
        }
        self.quota_warnings.append(warning)
        logger.warning(f"⚠️ Quota Warning for {user_id}: {message}")
    
    def get_usage_stats(self, hours: int = 1) -> Dict:
        """Get usage statistics for the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_requests = [r for r in self.requests_log if r["timestamp"] > cutoff]
        recent_errors = [e for e in self.errors_log if e["timestamp"] > cutoff]
        
        total_requests = len(recent_requests)
        successful_requests = sum(1 for r in recent_requests if r["success"])
        failed_requests = total_requests - successful_requests
        
        # Calculate tokens used
        total_tokens = sum(r.get("tokens", 0) for r in recent_requests)
        
        # Get unique users
        unique_users = len(set(r["user_id"] for r in recent_requests))
        
        # Error breakdown
        error_types = defaultdict(int)
        for error in recent_errors:
            error_types[error["error_type"]] += 1
        
        return {
            "time_window_hours": hours,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "total_tokens": total_tokens,
            "unique_users": unique_users,
            "avg_requests_per_hour": total_requests / hours,
            "error_breakdown": dict(error_types),
            "quota_warnings": len([w for w in self.quota_warnings if w["timestamp"] > cutoff])
        }
    
    def get_user_stats(self, user_id: str, hours: int = 1) -> Dict:
        """Get statistics for a specific user"""
        cutoff = datetime.now() - timedelta(hours=hours)
        user_requests = [r for r in self.requests_log 
                        if r["user_id"] == user_id and r["timestamp"] > cutoff]
        user_errors = [e for e in self.errors_log 
                      if e["user_id"] == user_id and e["timestamp"] > cutoff]
        
        return {
            "user_id": user_id,
            "time_window_hours": hours,
            "total_requests": len(user_requests),
            "successful_requests": sum(1 for r in user_requests if r["success"]),
            "failed_requests": len(user_errors),
            "total_tokens": sum(r.get("tokens", 0) for r in user_requests),
            "last_request": max((r["timestamp"] for r in user_requests), default=None),
            "error_count": len(user_errors)
        }
    
    def is_user_rate_limited(self, user_id: str, max_requests: int = 10, window_minutes: int = 1) -> bool:
        """Check if user should be rate limited"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_user_requests = [t for t in self.user_requests[user_id] if t > cutoff]
        
        return len(recent_user_requests) >= max_requests
    
    def get_quota_health(self) -> str:
        """Get overall quota health status"""
        stats = self.get_usage_stats(hours=1)
        recent_warnings = len([w for w in self.quota_warnings 
                             if w["timestamp"] > datetime.now() - timedelta(minutes=30)])
        
        if recent_warnings > 5:
            return "CRITICAL - Multiple quota errors detected"
        elif recent_warnings > 0:
            return "WARNING - Approaching quota limits"
        elif stats["total_requests"] > 100:
            return "CAUTION - High usage detected"
        else:
            return "HEALTHY - Normal operation"
    
    def _cleanup_old_logs(self):
        """Remove logs older than 24 hours"""
        cutoff = datetime.now() - timedelta(hours=24)
        self.requests_log = [r for r in self.requests_log if r["timestamp"] > cutoff]
        self.errors_log = [e for e in self.errors_log if e["timestamp"] > cutoff]
        self.quota_warnings = [w for w in self.quota_warnings if w["timestamp"] > cutoff]
        
        # Clean user request history
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [t for t in self.user_requests[user_id] if t > cutoff]
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
    
    def export_stats(self, filepath: str):
        """Export statistics to JSON file"""
        stats = {
            "exported_at": datetime.now().isoformat(),
            "overall_stats": self.get_usage_stats(hours=24),
            "quota_health": self.get_quota_health(),
            "recent_errors": [
                {
                    "timestamp": e["timestamp"].isoformat(),
                    "user": e["user_id"],
                    "type": e["error_type"],
                    "message": e["message"]
                }
                for e in self.errors_log[-50:]  # Last 50 errors
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Stats exported to {filepath}")


# Global monitor instance
api_monitor = APIUsageMonitor()


# Decorator to automatically track API calls
def track_api_call(func):
    """Decorator to track API calls"""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user_id = kwargs.get('user_id', 'unknown')
        
        try:
            result = await func(*args, **kwargs)
            api_monitor.log_request(user_id, model="gemini", success=True)
            return result
        except Exception as e:
            error_type = type(e).__name__
            api_monitor.log_error(user_id, error_type, str(e))
            raise
    
    return wrapper