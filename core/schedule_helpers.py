"""
Helper functions for working with cron schedules.

Converts between cron expressions and human-readable descriptions.
"""

from typing import Dict, Optional


def cron_to_human(cron: str) -> str:
    """
    Convert a cron expression to human-readable text.
    
    Args:
        cron: Cron expression (e.g., "0 * * * *")
    
    Returns:
        Human-readable description (e.g., "Every hour")
    """
    parts = cron.strip().split()
    
    if len(parts) != 5:
        return f"Custom schedule: {cron}"
    
    minute, hour, day, month, weekday = parts
    
    # Every X minutes
    if minute.startswith("*/") and hour == "*" and day == "*" and month == "*" and weekday == "*":
        interval = minute[2:]
        if interval == "15":
            return "Every 15 minutes"
        elif interval == "30":
            return "Every 30 minutes"
        else:
            return f"Every {interval} minutes"
    
    # Every hour
    if minute == "0" and hour == "*" and day == "*" and month == "*" and weekday == "*":
        return "Every hour"
    
    # Every X hours
    if minute == "0" and hour.startswith("*/") and day == "*" and month == "*" and weekday == "*":
        interval = hour[2:]
        return f"Every {interval} hours"
    
    # Daily at specific time
    if hour.isdigit() and day == "*" and month == "*" and weekday == "*":
        hour_int = int(hour)
        minute_int = int(minute) if minute.isdigit() else 0
        
        # Convert to 12-hour format
        period = "AM"
        display_hour = hour_int
        if hour_int == 0:
            display_hour = 12
        elif hour_int == 12:
            period = "PM"
        elif hour_int > 12:
            display_hour = hour_int - 12
            period = "PM"
        
        return f"Daily at {display_hour}:{minute_int:02d} {period}"
    
    # Weekly on specific day
    if weekday.isdigit() and day == "*" and month == "*":
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_name = days[int(weekday)]
        hour_int = int(hour) if hour.isdigit() else 0
        minute_int = int(minute) if minute.isdigit() else 0
        
        period = "AM"
        display_hour = hour_int
        if hour_int == 0:
            display_hour = 12
        elif hour_int == 12:
            period = "PM"
        elif hour_int > 12:
            display_hour = hour_int - 12
            period = "PM"
        
        return f"Weekly on {day_name} at {display_hour}:{minute_int:02d} {period}"
    
    # Default fallback
    return f"Custom schedule: {cron}"


def interval_to_cron(interval: str, custom_hour: Optional[str] = None, custom_minute: Optional[str] = None) -> str:
    """
    Convert an interval preset to a cron expression.
    
    Args:
        interval: Preset interval (e.g., "15min", "1hour", "daily")
        custom_hour: Hour for daily schedules (0-23)
        custom_minute: Minute for daily schedules (0-59)
    
    Returns:
        Cron expression
    """
    presets: Dict[str, str] = {
        "15min": "*/15 * * * *",
        "30min": "*/30 * * * *",
        "1hour": "0 * * * *",
        "2hours": "0 */2 * * *",
        "4hours": "0 */4 * * *",
        "6hours": "0 */6 * * *",
        "12hours": "0 */12 * * *",
        "daily": f"{custom_minute or '0'} {custom_hour or '0'} * * *",
    }
    
    return presets.get(interval, "0 * * * *")
