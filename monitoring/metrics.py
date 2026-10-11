
class Metrics:
    def __init__(self):
        self.orders_generated = 0
        self.orders_processed = 0
        self.trades_executed = 0
        self.errors = 0

    def record_generated(self):
        self.orders_generated += 1

    def record_processed(self):
        self.orders_processed += 1

    def record_trades(self, count):
        self.trades_executed += count

    def record_error(self):
        self.errors += 1

    def display(self):
        print("=== ChronosMatch Metrics ===")
        print("Orders generated:", self.orders_generated)
        print("Orders processed:", self.orders_processed)
        print("Trades executed:", self.trades_executed)
        print("Errors:", self.errors)
if __name__ == "__main__":
    metrics = Metrics()

    metrics.record_generated()
    metrics.record_generated()
    metrics.record_processed()
    metrics.record_trades(1)

    metrics.display()