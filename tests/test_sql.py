import pytest

from medibot.sql import SQLValidationError, validate_read_only_sql


def test_allowed_select_is_normalized() -> None:
    assert (
        validate_read_only_sql(" SELECT COUNT(*) FROM claims; ")
        == "SELECT COUNT(*) FROM claims"
    )


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO claims VALUES (1)",
        "SELECT * FROM unknown_table",
        "SELECT * FROM claims; DELETE FROM claims",
        "DROP TABLE claims",
    ],
)
def test_unsafe_sql_is_rejected(query: str) -> None:
    with pytest.raises(SQLValidationError):
        validate_read_only_sql(query)
