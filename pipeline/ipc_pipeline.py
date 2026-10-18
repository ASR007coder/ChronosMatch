# backend/pipeline/ipc_pipeline.py
from backend.ipc.consumer import Consumer
from backend.ipc.producer import Producer
from backend.ipc.ring_buffer import RingBuffer
from backend.engine.matching_engine import MatchingEngine


def process_orders(orders: list[dict]) -> dict:
    """Transfer orders through IPC and process them in the matching engine."""

    ring = RingBuffer.create()

    try:
        producer = Producer(ring)
        consumer = Consumer(ring)
        engine = MatchingEngine()

        orders_received = 0
        all_trades = []

        for order in orders:
            producer.submit(
                order_id=order["order_id"],
                sequence=order["sequence"],
                price=order["price"],
                timestamp_ns=order["timestamp_ns"],
                quantity=order["quantity"],
                side=order["side"],
                timeout=1,
            )

            (
                order_id,
                sequence,
                price,
                timestamp_ns,
                quantity,
                side,
            ) = consumer.receive(timeout=1)

            orders_received += 1

            trades = engine.submit(
                order_id=order_id,
                side=side,
                price=price,
                quantity=quantity,
                sequence=sequence,
            )

            for trade in trades:
                all_trades.append({
                    "trade_id": trade[0],
                    "buy_order_id": trade[1],
                    "sell_order_id": trade[2],
                    "price": trade[3],
                    "quantity": trade[4],
                    "sequence": trade[5],
                })

        bids, asks = engine.depth(5)

        return {
            "orders_received": orders_received,
            "orders_processed": engine.orders_processed,
            "trades_executed": engine.trades_executed,
            "trades": all_trades,
            "order_book": {
                "bids": bids,
                "asks": asks,
            },
        }

    finally:
        ring.unlink()