import unittest
from datetime import date, datetime, time

from app.core.database_urls import normalize_async_database_url
from app.core.identifiers import (
    normalize_email,
    normalize_phone,
    validate_email,
    validate_phone,
)
from app.core.password_policy import assess_password, require_strong_password
from app.core.scheduling import calculate_streak, in_quiet_hours, within_dispatch_window


class IdentifierTests(unittest.TestCase):
    def test_email_is_normalized(self) -> None:
        self.assertEqual(normalize_email("  Miranda@Exemplo.COM "), "miranda@exemplo.com")

    def test_email_validation_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "E-mail inválido"):
            validate_email("miranda@")

    def test_brazilian_phone_is_normalized_to_e164(self) -> None:
        self.assertEqual(normalize_phone("(11) 99999-9999"), "+5511999999999")
        self.assertEqual(validate_phone("+55 11 99999-9999"), "+5511999999999")

    def test_phone_validation_rejects_short_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "Telefone inválido"):
            validate_phone("12345")


class PasswordPolicyTests(unittest.TestCase):
    def test_strong_password_is_accepted(self) -> None:
        assessment = assess_password("Kaizen#Seguro2026")
        self.assertTrue(assessment.valid)
        self.assertEqual(assessment.missing, ())

    def test_missing_requirements_are_reported(self) -> None:
        assessment = assess_password("senhafraca")
        self.assertFalse(assessment.valid)
        self.assertIn("12 ou mais caracteres", assessment.missing)
        self.assertIn("uma letra maiúscula", assessment.missing)
        self.assertIn("um número", assessment.missing)
        self.assertIn("um símbolo", assessment.missing)

    def test_spaces_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "nenhum espaço"):
            require_strong_password("Kaizen #Seguro2026")


class DatabaseUrlTests(unittest.TestCase):
    def test_neon_url_is_ready_for_asyncpg(self) -> None:
        original = (
            "postgresql://miranda:segredo@ep-example-pooler.us-east-1.aws.neon.tech/"
            "kaizen?sslmode=require&channel_binding=require"
        )
        normalized = normalize_async_database_url(original)
        self.assertEqual(
            normalized,
            "postgresql+asyncpg://miranda:segredo@"
            "ep-example-pooler.us-east-1.aws.neon.tech/kaizen?ssl=require",
        )

    def test_sqlite_url_is_unchanged(self) -> None:
        original = "sqlite+aiosqlite:///./kaizen.db"
        self.assertEqual(normalize_async_database_url(original), original)


class SchedulingTests(unittest.TestCase):
    def test_streak_counts_from_today(self) -> None:
        completed = {date(2026, 8, 31), date(2026, 8, 30), date(2026, 8, 29)}
        self.assertEqual(calculate_streak(completed, date(2026, 8, 31)), 3)

    def test_streak_accepts_yesterday_as_last_completion(self) -> None:
        completed = {date(2026, 8, 30), date(2026, 8, 29)}
        self.assertEqual(calculate_streak(completed, date(2026, 8, 31)), 2)

    def test_quiet_hours_can_cross_midnight(self) -> None:
        self.assertTrue(in_quiet_hours(time(23, 0), time(22, 0), time(7, 0)))
        self.assertTrue(in_quiet_hours(time(6, 59), time(22, 0), time(7, 0)))
        self.assertFalse(in_quiet_hours(time(12, 0), time(22, 0), time(7, 0)))

    def test_dispatch_window_is_bounded(self) -> None:
        self.assertTrue(
            within_dispatch_window(datetime(2026, 8, 31, 8, 0, 20), time(8, 0), 45)
        )
        self.assertFalse(
            within_dispatch_window(datetime(2026, 8, 31, 8, 1), time(8, 0), 45)
        )


if __name__ == "__main__":
    unittest.main()
