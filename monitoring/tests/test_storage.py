import pytest
import sqlite3
from pathlib import Path

from storage.trade_store import TradeStore


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
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO trades
                VALUES (1, 101, 202, 0, 5, 1)
                """
            )
    finally:
        connection.close()


def test_zero_quantity_is_rejected():
    connection = create_database()

    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO trades
                VALUES (1, 101, 202, 10000, 0, 1)
                """
            )
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


def test_trade_store_saves_and_reads_recent_trades():
    with TradeStore() as store:
        store.save_trade(1, 101, 201, 10000, 5, 1)
        store.save_trade(2, 102, 202, 11000, 3, 2)
        store.save_trade(3, 103, 203, 12000, 2, 3)

        recent = store.get_recent_trades(limit=2)

        assert [trade["trade_id"] for trade in recent] == [3, 2]
        assert recent[0]["price"] == 12000
        assert recent[0]["quantity"] == 2


def test_trade_store_rejects_invalid_price():
    with TradeStore() as store:
        with pytest.raises(ValueError):
            store.save_trade(1, 101, 201, 0, 5, 1)


def test_trade_store_rejects_invalid_quantity():
    with TradeStore() as store:
        with pytest.raises(ValueError):
            store.save_trade(1, 101, 201, 10000, 0, 1)


def test_trade_store_rejects_invalid_recent_trade_limit():
    with TradeStore() as store:
        with pytest.raises(ValueError):
            store.get_recent_trades(limit=0)


def test_trade_store_returns_empty_list_when_no_trades_exist():
    with TradeStore() as store:
        recent = store.get_recent_trades(limit=10)

        assert recent == []


def test_trade_store_returns_all_trades_when_limit_is_larger():
    with TradeStore() as store:
        store.save_trade(1, 101, 201, 10000, 5, 1)
        store.save_trade(2, 102, 202, 11000, 3, 2)

        recent = store.get_recent_trades(limit=10)

        assert len(recent) == 2
        assert [trade["trade_id"] for trade in recent] == [2, 1]


def test_trade_store_rejects_negative_price():
    with TradeStore() as store:
        with pytest.raises(ValueError):
            store.save_trade(1, 101, 201, -100, 5, 1)


def test_trade_store_rejects_negative_quantity():
    with TradeStore() as store:
        with pytest.raises(ValueError):
            store.save_trade(1, 101, 201, 10000, -5, 1)
