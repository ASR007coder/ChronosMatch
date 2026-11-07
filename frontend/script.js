
const API = {
    start: "/api/v1/simulation/start",
    dashboard: "/api/v1/dashboard",
    health: "/api/v1/health",
};

const MIN_ORDERS = 10_000;
const MAX_ORDERS = 10_000_000;

const form = document.getElementById("simulation-form");
const orderInput = document.getElementById("order-count");
const startButton = document.getElementById("start-button");
const buttonText = document.getElementById("button-text");

let polling = false;

function formatNumber(value) {
    if (value === null || value === undefined) return "—";

    return Number(value).toLocaleString("en-IN", {
        maximumFractionDigits: 2,
    });
}

function formatSeconds(value) {
    if (value === null || value === undefined) return "—";

    return `${Number(value).toFixed(4)} s`;
}

function formatMicroseconds(valueInNs) {
    if (valueInNs === null || valueInNs === undefined) return "—";

    return `${(Number(valueInNs) / 1000).toFixed(2)} µs`;
}

function setStatus(status, message) {
    const statusText = document.getElementById("simulation-status");
    const messageText = document.getElementById("simulation-message");
    const dot = document.getElementById("simulation-dot");

    statusText.textContent = status.toUpperCase();
    messageText.textContent = message;

    dot.className = "status-dot";

    if (status === "running" || status === "queued") {
        dot.classList.add("running");
    }

    if (status === "failed") {
        dot.classList.add("failed");
    }
}

function showError(message) {
    const errorElement = document.getElementById("error-message");

    errorElement.textContent = message;
    errorElement.classList.remove("hidden");
}

function clearError() {
    const errorElement = document.getElementById("error-message");

    errorElement.textContent = "";
    errorElement.classList.add("hidden");
}

function resetMetrics() {
    const ids = [
        "orders-processed",
        "throughput",
        "p99-latency",
        "mean-latency",
        "trades-executed",
        "steady-time",
        "p50-latency",
        "p95-latency",
        "detail-p99",
        "max-latency",
        "integrity-generated",
        "integrity-accepted",
        "integrity-published",
        "integrity-received",
        "integrity-unique",
        "integrity-duplicates",
    ];

    ids.forEach((id) => {
        document.getElementById(id).textContent = "—";
    });

    document.getElementById("stage-timings").innerHTML = `
        <tr>
            <td colspan="2" class="empty-row">Waiting for results</td>
        </tr>
    `;
}

function renderMetrics(job) {
    const metrics = job.metrics;

    if (!metrics) return;

    const simulator = metrics.simulator || {};
    const latency = metrics.latency || {};
    const timings = metrics.timings || {};

    document.getElementById("orders-processed").textContent =
        formatNumber(metrics.orders_processed);

    document.getElementById("throughput").textContent =
        formatNumber(metrics.steady_throughput);

    document.getElementById("p99-latency").textContent =
        formatMicroseconds(latency.p99);

    document.getElementById("mean-latency").textContent =
        formatMicroseconds(latency.mean);

    document.getElementById("trades-executed").textContent =
        formatNumber(metrics.trades_executed);

    document.getElementById("steady-time").textContent =
        formatSeconds(timings.steady_state_seconds);

    document.getElementById("p50-latency").textContent =
        formatMicroseconds(latency.median);

    document.getElementById("p95-latency").textContent =
        formatMicroseconds(latency.p95);

    document.getElementById("detail-p99").textContent =
        formatMicroseconds(latency.p99);

    document.getElementById("max-latency").textContent =
        formatMicroseconds(latency.max);

    document.getElementById("integrity-generated").textContent =
        formatNumber(simulator.generated);

    document.getElementById("integrity-accepted").textContent =
        formatNumber(simulator.accepted);

    document.getElementById("integrity-published").textContent =
        formatNumber(metrics.published);

    document.getElementById("integrity-received").textContent =
        formatNumber(metrics.orders_received);

    document.getElementById("integrity-unique").textContent =
        formatNumber(metrics.unique_order_ids);

    document.getElementById("integrity-duplicates").textContent =
        formatNumber(metrics.duplicate_order_ids);

    renderStageTimings(timings);
}

function renderStageTimings(timings) {
    const container = document.getElementById("stage-timings");

    const labels = {
        pipeline_wall_seconds: "Pipeline wall time",
        steady_state_seconds: "Steady-state time",
        workload_build_seconds: "Workload construction",
        simulator_run_seconds: "Simulator run",
        producer_queue_wait_seconds: "Producer queue wait",
        producer_publish_seconds: "Producer publishing",
        consumer_receive_seconds: "Consumer receiving",
        consumer_timeout_seconds: "Consumer timeout",
        matching_seconds: "Matching engine",
        trade_materialization_seconds: "Trade materialization",
        depth_seconds: "Order book depth",
        adapter_drain_seconds: "Adapter drain",
        consumer_join_seconds: "Consumer join",
        ring_cleanup_seconds: "Ring cleanup",
    };

    container.innerHTML = "";

    Object.entries(labels).forEach(([key, label]) => {
        const row = document.createElement("tr");
        const name = document.createElement("td");
        const value = document.createElement("td");

        name.textContent = label;
        value.textContent = formatSeconds(timings[key]);

        row.appendChild(name);
        row.appendChild(value);
        container.appendChild(row);
    });
}

async function getDashboard() {
    const response = await fetch(API.dashboard);

    if (!response.ok) {
        throw new Error("Could not retrieve dashboard data.");
    }

    return response.json();
}

async function pollDashboard() {
    if (polling) return;

    polling = true;

    try {
        while (true) {
            const data = await getDashboard();
            const job = data.job;

            if (!job) {
                setStatus("idle", "Waiting for simulation command");
                break;
            }

            if (job.status === "queued" || job.status === "running") {
                setStatus(
                    job.status,
                    `Processing ${formatNumber(job.total_orders)} orders`
                );

                await new Promise((resolve) => setTimeout(resolve, 1000));
                continue;
            }

            if (job.status === "completed") {
                renderMetrics(job);
                setStatus("completed", "Simulation completed successfully");

                startButton.disabled = false;
                orderInput.disabled = false;
                buttonText.textContent = "START SIMULATION";

                break;
            }

            if (job.status === "failed") {
                setStatus("failed", "Simulation failed");
                showError(job.error || "Unknown simulation error");

                startButton.disabled = false;
                orderInput.disabled = false;
                buttonText.textContent = "START SIMULATION";

                break;
            }

            break;
        }
    } catch (error) {
        showError(error.message);
        setStatus("failed", "Unable to retrieve simulation status");

        startButton.disabled = false;
        orderInput.disabled = false;
        buttonText.textContent = "START SIMULATION";
    } finally {
        polling = false;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    clearError();

    const totalOrders = Number(orderInput.value);

    if (
        !Number.isSafeInteger(totalOrders) ||
        totalOrders < MIN_ORDERS ||
        totalOrders > MAX_ORDERS
    ) {
        showError(
            "Order count must be an integer between 10,000 and 10,000,000."
        );
        return;
    }

    startButton.disabled = true;
    orderInput.disabled = true;
    buttonText.textContent = "STARTING...";

    resetMetrics();
    setStatus("queued", "Submitting simulation request");

    try {
        const response = await fetch(API.start, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                total_orders: totalOrders,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not start simulation.");
        }

        setStatus("running", `Job ID: ${data.job_id}`);
        buttonText.textContent = "SIMULATION RUNNING";

        await pollDashboard();

    } catch (error) {
        showError(error.message);
        setStatus("failed", "Could not start simulation");

        startButton.disabled = false;
        orderInput.disabled = false;
        buttonText.textContent = "START SIMULATION";
    }
});

async function initialize() {
    try {
        const response = await fetch(API.health);

        if (!response.ok) {
            throw new Error("Backend unavailable");
        }

        document.getElementById("connection-status").textContent =
            "SYSTEM ONLINE";

        await pollDashboard();

    } catch {
        document.getElementById("connection-status").textContent =
            "BACKEND OFFLINE";

        showError("Cannot connect to ChronosMatch backend.");
    }
}

initialize();

/* =========================================
   FRONTEND-ONLY MARKET VISUALIZER
   These events are illustrative, not real.
========================================= */

const visualizer = {
    running: false,
    timer: null,
    orders: 0,
    trades: 0,
    buyVolume: 0,
    sellVolume: 0,
    price: 50000,

    random(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    },

    format(value) {
        return value.toLocaleString("en-IN");
    },

    start() {
        if (this.running) return;

        this.reset();
        this.running = true;

        document.getElementById("visual-status").classList.add("active");
        document.getElementById("visual-status").lastChild.textContent = " RUNNING";

        document.getElementById("engine-status").textContent = "PROCESSING";
        document.getElementById("engine-status").classList.add("processing");
        document.querySelector(".matching-core").classList.add("processing");

        this.timer = setInterval(() => this.tick(), 450);
    },

    stop() {
        this.running = false;
        clearInterval(this.timer);
        this.timer = null;

        document.getElementById("visual-status").classList.remove("active");
        document.getElementById("visual-status").lastChild.textContent = " COMPLETED";

        document.getElementById("engine-status").textContent = "STANDBY";
        document.getElementById("engine-status").classList.remove("processing");
        document.querySelector(".matching-core").classList.remove("processing");
    },

    reset() {
        this.orders = 0;
        this.trades = 0;
        this.buyVolume = 0;
        this.sellVolume = 0;
        this.price = 50000;

        document.getElementById("buy-flow").replaceChildren();
        document.getElementById("sell-flow").replaceChildren();
        document.getElementById("trade-tape-body").innerHTML =
            '<div class="empty-tape">Waiting for market activity...</div>';

        this.render();
    },

    tick() {
        const isBuy = Math.random() < 0.5;
        const quantity = this.random(1, 100);
        const price = this.price + this.random(-15, 15);

        this.orders++;

        if (isBuy) {
            this.buyVolume += quantity;
        } else {
            this.sellVolume += quantity;
        }

        this.addOrder(isBuy, price, quantity);

        // Illustrative execution probability.
        if (Math.random() < 0.65) {
            this.executeTrade(price, quantity);
        }

        this.price = price;
        this.render();
    },

    addOrder(isBuy, price, quantity) {
        const container = document.getElementById(
            isBuy ? "buy-flow" : "sell-flow"
        );

        const order = document.createElement("div");
        order.className = `flow-order ${isBuy ? "buy-order" : "sell-order"}`;

        const id = `ORD-${this.orders.toString().padStart(6, "0")}`;

        const left = document.createElement("span");
        left.textContent = id;

        const right = document.createElement("strong");
        right.textContent = `${this.format(price)} × ${quantity}`;

        order.append(left, right);
        container.prepend(order);

        while (container.children.length > 4) {
            container.lastElementChild.remove();
        }
    },

    executeTrade(price, quantity) {
        this.trades++;

        const tape = document.getElementById("trade-tape-body");

        if (tape.querySelector(".empty-tape")) {
            tape.replaceChildren();
        }

        const row = document.createElement("div");
        row.className = "trade-row";

        const values = [
            new Date().toLocaleTimeString("en-IN"),
            `BUY-${this.trades} / SELL-${this.trades}`,
            this.format(price),
            quantity.toString()
        ];

        values.forEach((value, index) => {
            const cell = document.createElement("span");
            cell.textContent = value;

            if (index === 2) {
                cell.className = "trade-price";
            }

            row.appendChild(cell);
        });

        tape.prepend(row);

        while (tape.children.length > 12) {
            tape.lastElementChild.remove();
        }
    },

    render() {
        document.getElementById("visual-orders").textContent =
            this.format(this.orders);

        document.getElementById("visual-trades").textContent =
            this.format(this.trades);

        document.getElementById("visual-price").textContent =
            this.format(this.price);

        document.getElementById("buy-volume").textContent =
            this.format(this.buyVolume);

        document.getElementById("sell-volume").textContent =
            this.format(this.sellVolume);
    }
};
