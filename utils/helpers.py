"""
DataFix - Helper Utilities
String processing, fuzzy matching fallbacks, regex pattern recognition, and UI formatters.
"""

import re
import difflib
from datetime import datetime
from typing import Any, Optional, Tuple, List
import pandas as pd
import numpy as np

# Try importing RapidFuzz, fall back to difflib
try:
    from rapidfuzz import fuzz as rf_fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


# Common Regex Patterns
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}$")
ZIP_REGEX = re.compile(r"^\d{5}(-\d{4})?$")
NUMERIC_STRING_REGEX = re.compile(r"^[-+]?[\$€£]?\s*[\d,]+(\.\d+)?%?$")

COMMON_EMAIL_TYPOS = {
    "gmaill.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmial.com": "gmail.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "hotmial.com": "hotmail.com",
    "hotmaill.com": "hotmail.com",
    "outlok.com": "outlook.com"
}


def calculate_similarity(s1: str, s2: str) -> float:
    """
    Computes fuzzy string similarity score between 0.0 and 1.0.
    Uses RapidFuzz ratio if available; falls back to difflib.SequenceMatcher.
    """
    if not isinstance(s1, str) or not isinstance(s2, str):
        return 0.0
    s1, s2 = s1.strip().lower(), s2.strip().lower()
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
        
    if RAPIDFUZZ_AVAILABLE:
        return rf_fuzz.ratio(s1, s2) / 100.0
    else:
        return difflib.SequenceMatcher(None, s1, s2).ratio()


def is_valid_email(val: Any) -> bool:
    """Checks if a string is a syntactically valid email address."""
    if not isinstance(val, str) or not val.strip():
        return False
    return bool(EMAIL_REGEX.match(val.strip()))


def fix_email_domain_typo(val: str) -> Optional[str]:
    """Corrects known common domain typos in email addresses."""
    if not isinstance(val, str) or "@" not in val:
        return None
    val = val.strip()
    user, domain = val.rsplit("@", 1)
    domain_lower = domain.lower()
    if domain_lower in COMMON_EMAIL_TYPOS:
        corrected_domain = COMMON_EMAIL_TYPOS[domain_lower]
        return f"{user}@{corrected_domain}"
    return None


def is_valid_phone(val: Any) -> bool:
    """Checks if a string looks like a standard phone number."""
    if not isinstance(val, str) or not val.strip():
        return False
    cleaned = re.sub(r"[^\d+]", "", val.strip())
    # Typically 10 to 15 digits
    return 10 <= len(cleaned) <= 15


def normalize_phone_number(val: Any) -> Optional[str]:
    """Formats phone number into clean US/international representation: +1-XXX-XXX-XXXX or standard."""
    if not isinstance(val, str) or not val.strip():
        return None
    digits = re.sub(r"[^\d]", "", val)
    if len(digits) == 10:
        return f"+1-{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+1-{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
    elif len(digits) >= 10:
        return f"+{digits}"
    return None


def try_parse_date(val: Any) -> Tuple[bool, Optional[datetime]]:
    """
    Attempts to parse arbitrary date formats into standard datetime object.
    Supports ISO, US (MM/DD/YYYY), European (DD/MM/YYYY), named months, etc.
    """
    if pd.isna(val) or val is None or val == "":
        return False, None
    if isinstance(val, (datetime, pd.Timestamp)):
        return True, val.to_pydatetime() if hasattr(val, "to_pydatetime") else val
        
    s = str(val).strip()
    
    # Check for epoch milliseconds or seconds
    if s.isdigit() and len(s) in [10, 13]:
        try:
            ts = int(s)
            if len(s) == 13:
                ts /= 1000.0
            dt = datetime.fromtimestamp(ts)
            if 1950 <= dt.year <= 2050:
                return True, dt
        except Exception:
            pass

    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S", "%m-%d-%Y", "%d-%m-%Y",
        "%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%d %B %Y",
        "%Y%m%d", "%m/%d/%y", "%d/%m/%y"
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(s, fmt)
            # Filter unrealistic years (e.g. 0001, 2999)
            if 1900 <= parsed.year <= 2100:
                return True, parsed
        except ValueError:
            continue
            
    # Try pandas to_datetime as fallback
    try:
        parsed_pd = pd.to_datetime(s, errors="raise")
        if 1900 <= parsed_pd.year <= 2100:
            return True, parsed_pd.to_pydatetime()
    except Exception:
        pass
        
    return False, None


def clean_numeric_string(val: Any) -> Tuple[bool, Optional[float]]:
    """
    Extracts numeric float from strings with currency symbols ($), commas, percent signs, or spaces.
    e.g. '$1,250.50' -> 1250.50, ' 45% ' -> 45.0
    """
    if pd.isna(val) or val is None or val == "":
        return False, None
    if isinstance(val, (int, float, np.number)):
        return True, float(val)
        
    s = str(val).strip()
    # Remove currency signs and spaces
    s_cleaned = re.sub(r"[\$€£₹¥,\s%]", "", s)
    
    # Handle parenthesized negatives: (120.5) -> -120.5
    if s_cleaned.startswith("(") and s_cleaned.endswith(")"):
        s_cleaned = "-" + s_cleaned[1:-1]
        
    try:
        num = float(s_cleaned)
        return True, num
    except ValueError:
        return False, None


def format_currency(val: float) -> str:
    """Formats float as clean USD string."""
    try:
        return f"${val:,.2f}"
    except Exception:
        return str(val)


def get_severity_badge_html(severity: str) -> str:
    """Generates styled badge HTML based on severity."""
    s = str(severity).capitalize()
    if s == "Critical":
        cls = "badge-critical"
    elif s == "High":
        cls = "badge-high"
    elif s == "Medium":
        cls = "badge-medium"
    else:
        cls = "badge-low"
    return f'<span class="badge {cls}">{s}</span>'


def get_confidence_badge_html(score: float) -> str:
    """Generates styled badge HTML based on confidence percentage."""
    pct = round(score * 100, 1)
    if score >= 0.85:
        color = "#10B981"
        bg = "#D1FAE5"
        label = f"{pct}% (High Confidence)"
    elif score >= 0.60:
        color = "#F59E0B"
        bg = "#FEF3C7"
        label = f"{pct}% (Moderate)"
    else:
        color = "#EF4444"
        bg = "#FEE2E2"
        label = f"{pct}% (Low - Review)"
    return f'<span style="background:{bg}; color:{color}; padding:2px 8px; border-radius:12px; font-weight:700; font-size:0.75rem;">{label}</span>'
