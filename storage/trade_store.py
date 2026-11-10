
import sqlite3
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class TradeStore:
    """Save and retrieve ChronosMatch trades using SQLite."""

    def __init__(self, database_path=":memory:"):
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row

        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        self.connection.executescript(schema)

    def save_trade(
        self,
        trade_id,
        buy_order_id,
        sell_order_id,
        price,
        quantity,
        sequence,
    ):
        """Save one executed trade."""
        values = {
            "trade_id": trade_id,
            "buy_order_id": buy_order_id,
            "sell_order_id": sell_order_id,
            "price": price,
            "quantity": quantity,
            "sequence": sequence,
        }

        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")

        if trade_id <= 0:
            raise ValueError("trade_id must be positive")
        if buy_order_id <= 0 or sell_order_id <= 0:
            raise ValueError("Order IDs must be positive")
        if price <= 0:
            raise ValueError("price must be positive")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if sequence <= 0:
            raise ValueError("sequence must be positive")

        with self.connection:
            self.connection.execute(
                """
                INSERT INTO trades
                (trade_id, buy_order_id, sell_order_id,
                 price, quantity, sequence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_id,
                    buy_order_id,
                    sell_order_id,
                    price,
                    quantity,
                    sequence,
                ),
            )

    def get_recent_trades(self, limit=10):
        """Return the newest trades first."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        rows = self.connection.execute(
            """
            SELECT trade_id, buy_order_id, sell_order_id,
                   price, quantity, sequence
            FROM trades
            ORDER BY sequence DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]

    def close(self):
        """Close the database connection."""
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
