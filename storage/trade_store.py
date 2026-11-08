import sqlite3
from pathlib import Path


class TradeStore:
    def __init__(self, database=":memory:"):
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row

        schema_path = (
            Path(__file__).resolve().parents[1]
            / "backend"
            / "storage"
            / "schema.sql"
        )

        schema = schema_path.read_text(encoding="utf-8")
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
        if price <= 0:
            raise ValueError("Price must be greater than zero")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

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

        self.connection.commit()

    def get_recent_trades(self, limit=10):
        if limit <= 0:
            raise ValueError("Limit must be greater than zero")

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
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()