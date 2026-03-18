from bson import ObjectId


def is_non_empty_string(value):
    return isinstance(value, str) and bool(value.strip())


def normalize_email(value):
    if not is_non_empty_string(value):
        return None
    email = value.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return None
    return email


def serialize_document(value):
    if isinstance(value, list):
        return [serialize_document(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_document(item) for key, item in value.items()}
    if isinstance(value, ObjectId):
        return str(value)
    return value
