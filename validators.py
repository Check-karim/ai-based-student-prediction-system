"""Input validation helpers for registration."""

import re

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
NAME_PATTERN = re.compile(r"^[a-zA-Z\s]+$")


def validate_username(username: str) -> list[str]:
    errors = []
    if " " in username:
        errors.append("Username cannot contain spaces.")
    if username and username[0].isdigit():
        errors.append("Username cannot start with a number.")
    return errors


def validate_full_name(full_name: str) -> list[str]:
    errors = []
    if not NAME_PATTERN.match(full_name):
        errors.append("Full name can only contain letters and spaces.")
    return errors


def validate_email(email: str) -> list[str]:
    errors = []
    if not EMAIL_PATTERN.match(email):
        errors.append("Please enter a valid email address.")
    return errors
