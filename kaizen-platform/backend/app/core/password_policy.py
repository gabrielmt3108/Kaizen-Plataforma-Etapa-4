from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordAssessment:
    valid: bool
    missing: tuple[str, ...]


def assess_password(password: str) -> PasswordAssessment:
    checks = {
        "12 ou mais caracteres": len(password) >= 12,
        "uma letra minúscula": any(char.islower() for char in password),
        "uma letra maiúscula": any(char.isupper() for char in password),
        "um número": any(char.isdigit() for char in password),
        "um símbolo": any(not char.isalnum() and not char.isspace() for char in password),
        "nenhum espaço": bool(password) and not any(char.isspace() for char in password),
    }
    missing = tuple(label for label, passed in checks.items() if not passed)
    return PasswordAssessment(valid=not missing, missing=missing)


def require_strong_password(password: str) -> None:
    assessment = assess_password(password)
    if not assessment.valid:
        requirements = ", ".join(assessment.missing)
        raise ValueError(f"A senha precisa conter: {requirements}")

