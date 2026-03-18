from utils.validators import is_non_empty_string, normalize_email


def validate_signup_payload(data):
    if not isinstance(data, dict):
        return None, "Invalid JSON body."

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not is_non_empty_string(username):
        return None, "Username is required."
    if not is_non_empty_string(email):
        return None, "Email is required."
    if not is_non_empty_string(password):
        return None, "Password is required."

    normalized_email = normalize_email(email)
    if normalized_email is None:
        return None, "A valid email address is required."

    return {
        "username": username.strip(),
        "email": normalized_email,
        "password": password,
        "role": data.get("role", "user"),
        "contact_preference": data.get("contact_preference", "email"),
    }, None
