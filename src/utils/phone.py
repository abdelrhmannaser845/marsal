import re
from typing import Optional, Any
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


def normalize_phone(raw_phone: Any, default_region: str = "EG") -> str:
    """
    Standardize a phone number to international E.164 format (e.g., +201120844781).
    
    Handles:
      - Local Egyptian formats (010..., 011..., 012..., 015...) -> +2010...
      - International numbers with or without leading '+' (e.g. 201120844781)
      - Numbers formatted with spaces, dashes, or parentheses
      - Floating-point representations from Excel (e.g. 201120844781.0)
    """
    if raw_phone is None:
        raise ValueError("Phone number cannot be None")

    # If Excel parsed number as float/int
    if isinstance(raw_phone, (int, float)):
        raw_phone = str(int(raw_phone))
    else:
        raw_phone = str(raw_phone).strip()

    # Remove trailing .0 if present
    if raw_phone.endswith(".0"):
        raw_phone = raw_phone[:-2]

    # Clean characters except digits and leading '+'
    cleaned = re.sub(r"[^\d+]", "", raw_phone)

    # Handle local numbers without country code
    # For Egypt: numbers starting with '01' (11 digits: 010, 011, 012, 015)
    if cleaned.startswith("01") and len(cleaned) == 11:
        cleaned = "+2" + cleaned
    elif cleaned.startswith("201") and len(cleaned) == 12:
        cleaned = "+" + cleaned
    elif not cleaned.startswith("+"):
        # If it doesn't have a plus, try adding one if it looks like international
        # or parse with default region
        pass

    try:
        if cleaned.startswith("+"):
            parsed = phonenumbers.parse(cleaned, None)
        else:
            parsed = phonenumbers.parse(cleaned, default_region)
        
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        elif phonenumbers.is_possible_number(parsed) and len(cleaned) >= 8:
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        else:
            raise ValueError(f"Phone number '{raw_phone}' is not a valid number")
    except (NumberParseException, ValueError):
        # Fallback manual regex normalization
        digits_only = re.sub(r"\D", "", cleaned)
        if digits_only.startswith("201") and len(digits_only) == 12:
            return f"+{digits_only}"
        elif digits_only.startswith("01") and len(digits_only) == 11:
            return f"+2{digits_only}"
        elif digits_only.startswith("1") and len(digits_only) == 10:
            return f"+20{digits_only}"
        raise ValueError(f"Invalid phone number format: '{raw_phone}'")


def is_valid_phone(phone_str: str, default_region: str = "EG") -> bool:
    """Check if a phone number string can be normalized and is valid."""
    try:
        normalize_phone(phone_str, default_region)
        return True
    except Exception:
        return False
