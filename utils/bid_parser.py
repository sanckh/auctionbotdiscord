import re

def parse_bid(bid_str: str) -> tuple[int, str]:
    """Parse bid string into total silver amount and formatted display string"""
    try:
        bid_str = bid_str.lower()
        # Handle full names and abbreviations
        replacements = {
            'mithril': 'm', 'mith': 'm',
            'platinum': 'p', 'plat': 'p',
            'gold': 'g',
            'silver': 's', 'sil': 's'
        }
        for full, short in replacements.items():
            bid_str = bid_str.replace(full, short)
        
        total_silver = 0
        parts = bid_str.split()
        
        # Validate currency order
        valid_order = ['m', 'p', 'g', 's']
        last_currency_index = -1
        
        for part in parts:
            if not (match := re.match(r'^(\d+)([mgps])$', part)):
                return None, None
                
            amount, unit = match.groups()
            current_index = valid_order.index(unit)
            
            # Check if currencies are in correct order
            if current_index <= last_currency_index:
                return None, None
            last_currency_index = current_index
            
            amount = int(amount)
            
            multipliers = {
                'm': 1000000,
                'p': 10000,
                'g': 100,
                's': 1
            }
            total_silver += amount * multipliers[unit]
        
        # Convert total silver to mixed denominations
        mithril = total_silver // 1000000
        remainder = total_silver % 1000000
        
        platinum = remainder // 10000
        remainder = remainder % 10000
        
        gold = remainder // 100
        silver = remainder % 100
        
        # Build display string with only non-zero amounts
        parts = []
        if mithril > 0:
            parts.append(f"{mithril}m")
        if platinum > 0:
            parts.append(f"{platinum}p")
        if gold > 0:
            parts.append(f"{gold}g")
        if silver > 0:
            parts.append(f"{silver}s")
        
        display = " ".join(parts) if parts else "0s"
        
        return total_silver, display
    except (ValueError, KeyError, AttributeError):
        return None, None
