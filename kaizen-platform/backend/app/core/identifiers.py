import re


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_email(value: str) -> str:
    normalized = normalize_email(value)
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("E-mail inválido")
    return normalized


def normalize_phone(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) in {10, 11} and not digits.startswith("55"):
        digits = f"55{digits}"
    return f"+{digits}" if digits else ""


def validate_phone(value: str) -> str:
    normalized = normalize_phone(value)
    digits = normalized.removeprefix("+")
    if len(digits) not in {12, 13}:
        raise ValueError("Telefone inválido")
    return normalized

