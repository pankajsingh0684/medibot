import re

ALLOWED_TABLES = {"claims", "maintenance_tickets"}
FORBIDDEN_KEYWORDS = {
    "attach",
    "alter",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma",
    "replace",
    "truncate",
    "update",
}


class SQLValidationError(ValueError):
    pass


def validate_read_only_sql(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise SQLValidationError("SQL query cannot be empty.")
    if not re.match(r"^select\b", normalized, flags=re.IGNORECASE):
        raise SQLValidationError("Only SELECT statements are allowed.")
    if ";" in normalized.rstrip(";"):
        raise SQLValidationError("Only one SQL statement is allowed.")

    tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", normalized.lower()))
    forbidden = tokens.intersection(FORBIDDEN_KEYWORDS)
    if forbidden:
        raise SQLValidationError("The SQL statement contains a forbidden operation.")

    referenced_tables = set(
        re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", normalized.lower())
    )
    if not referenced_tables or not referenced_tables.issubset(ALLOWED_TABLES):
        raise SQLValidationError("The SQL statement references an unauthorized table.")

    return normalized.rstrip(";").strip()
