from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

POSTGRES_SCHEMES = {"postgres", "postgresql", "postgresql+asyncpg"}


def normalize_async_database_url(value: str) -> str:
    """Converte a URL padrão do Neon para o formato aceito pelo SQLAlchemy/asyncpg."""
    raw_url = value.strip()
    parsed = urlsplit(raw_url)
    if parsed.scheme.lower() not in POSTGRES_SCHEMES:
        return raw_url

    query: list[tuple[str, str]] = []
    ssl_mode: str | None = None
    has_ssl_parameter = False
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_key = key.lower()
        if normalized_key == "channel_binding":
            # A URL copiada do Neon pode incluir esta opção do libpq, que não é
            # um argumento aceito pelo driver asyncpg usado pela aplicação.
            continue
        if normalized_key == "sslmode":
            ssl_mode = item
            continue
        if normalized_key == "ssl":
            has_ssl_parameter = True
        query.append((key, item))

    if ssl_mode and not has_ssl_parameter:
        query.append(("ssl", ssl_mode))

    return urlunsplit(
        (
            "postgresql+asyncpg",
            parsed.netloc,
            parsed.path,
            urlencode(query, doseq=True),
            parsed.fragment,
        )
    )
