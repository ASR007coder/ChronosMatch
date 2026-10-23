
import sqlite3
from pathlib import Path

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "schema.sql"
)


def create_database():
    connection = sqlite3.connect(":memory:")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript(schema)
    return connection


def test_valid_trade_is_saved():
    connection = create_database()

    try:
        connection.execute(
            """
            INSERT INTO trades
            (trade_id, buy_order_id, sell_order_id, price, quantity, sequence)
            VALUES (1, 101, 202, 10000, 5, 1)
            """
        )

        result = connection.execute(
            "SELECT price, quantity FROM trades WHERE trade_id = 1"
        ).fetchone()

        assert result == (10000, 5)
    finally:
        connection.close()


def test_zero_price_is_rejected():
    connection = create_database()

    try:
        try:
            connection.execute(
                """
                INSERT INTO trades
                VALUES (1, 101, 202, 0, 5, 1)
                """
            )
            assert False, "Zero price should be rejected"
        except sqlite3.IntegrityError:
            pass
    finally:
        connection.close()


def test_zero_quantity_is_rejected():
    connection = create_database()

    try:
        try:
            connection.execute(
                """
                INSERT INTO trades
                VALUES (1, 101, 202, 10000, 0, 1)
                """
            )
            assert False, "Zero quantity should be rejected"
        except sqlite3.IntegrityError:
            pass
    finally:
        connection.close()


def test_recent_trades_can_be_queried():
    connection = create_database()

    try:
        connection.executemany(
            """
            INSERT INTO trades
            (trade_id, buy_order_id, sell_order_id, price, quantity, sequence)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 101, 201, 10000, 5, 1),
                (2, 102, 202, 11000, 3, 2),
                (3, 103, 203, 12000, 2, 3),
            ],
        )

        recent = connection.execute(
            """
            SELECT trade_id, price
            FROM trades
            ORDER BY sequence DESC
            LIMIT 2
            """
        ).fetchall()

        assert recent == [(3, 12000), (2, 11000)]
    finally:
        connection.close()
