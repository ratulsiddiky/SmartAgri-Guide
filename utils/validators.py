from bson import ObjectId
import re


_EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", re.IGNORECASE)


def is_non_empty_string(value):
    return isinstance(value, str) and bool(value.strip())


def normalize_email(value):
    if not is_non_empty_string(value):
        return None
    email = value.strip().lower()
    if not _EMAIL_RE.match(email):
        return None
    return email


def validate_password_strength(password: str):
    if not is_non_empty_string(password):
        return "Password is required."

    pwd = password.strip()
    if len(pwd) < 8:
        return "Password must be at least 8 characters long."

    has_lower = any(c.islower() for c in pwd)
    has_upper = any(c.isupper() for c in pwd)
    has_digit = any(c.isdigit() for c in pwd)
    has_symbol = any(not c.isalnum() for c in pwd)

    if not (has_lower and has_upper and has_digit and has_symbol):
        return "Password must include uppercase, lowercase, a number, and a symbol."

    return None


def serialize_document(value):
    if isinstance(value, list):
        return [serialize_document(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_document(item) for key, item in value.items()}
    if isinstance(value, ObjectId):
        return str(value)
    return value
