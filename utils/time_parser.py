import re
from datetime import timedelta

def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string into timedelta"""
    if match := re.match(r'^(\d+)([mh])$', duration_str.lower()):
        amount, unit = match.groups()
        amount = int(amount)
        
        if unit == 'm':
            return timedelta(minutes=amount)
        elif unit == 'h':
            return timedelta(hours=amount)
    
    return None
