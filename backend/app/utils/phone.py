"""Phone number normalization for Ghana mobile formats."""


def normalize_ghana_phone(phone: str) -> str:
    """Normalize to local 10-digit format starting with 0."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("233") and len(digits) >= 12:
        return "0" + digits[3:12]
    if digits.startswith("0") and len(digits) >= 10:
        return digits[:10]
    if len(digits) == 9:
        return "0" + digits
    return phone.strip()
