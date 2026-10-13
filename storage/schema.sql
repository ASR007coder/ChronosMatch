
CREATE TABLE IF NOT EXISTS trades (
    trade_id INTEGER PRIMARY KEY,
    buy_order_id INTEGER NOT NULL,
    sell_order_id INTEGER NOT NULL,
    price INTEGER NOT NULL CHECK (price > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    sequence INTEGER NOT NULL UNIQUE CHECK (sequence > 0)
);
