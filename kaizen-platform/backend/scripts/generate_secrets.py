import secrets


def main() -> None:
    print(f"KAIZEN_JWT_SECRET={secrets.token_urlsafe(64)}")
    print(f"KAIZEN_CRON_SECRET={secrets.token_urlsafe(48)}")


if __name__ == "__main__":
    main()
