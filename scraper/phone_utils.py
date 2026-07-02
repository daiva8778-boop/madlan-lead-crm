import re


def normalize_il_phone(raw):
    """'0738085411' / '073-808-5411' / '+972738085411' -> '972738085411'. None if invalid."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("972"):
        normalized = digits
    elif digits.startswith("0"):
        normalized = "972" + digits[1:]
    else:
        normalized = "972" + digits
    if len(normalized) != 12:
        return None
    return normalized


def is_mobile(normalized_972_number):
    """972-formatted number -> True if it's an 05X Israeli mobile (vs. 07X tracking / landline)."""
    if not normalized_972_number or not normalized_972_number.startswith("972"):
        return False
    local = "0" + normalized_972_number[3:]
    return local.startswith("05")
