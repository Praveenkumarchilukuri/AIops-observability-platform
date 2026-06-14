# 🎯 AIOps Observability Platform — Complete Interview Preparation Guide

> **Project:** AIOps Observability & Diagnostic Platform  
> **What it does:** A real microservices system that monitors itself, injects fake problems, and uses Google Gemini AI to diagnose what went wrong — automatically.

---

## 📖 TABLE OF CONTENTS

1. [Project Overview — In Simple Words](#1-project-overview--in-simple-words)
2. [Architecture & System Design](#2-architecture--system-design)
3. [Microservices — FastAPI & Python](#3-microservices--fastapi--python)
4. [OpenTelemetry — The Instrumentation Layer](#4-opentelemetry--the-instrumentation-layer)
5. [Prometheus — Metrics Database](#5-prometheus--metrics-database)
6. [Loki — Log Aggregation](#6-loki--log-aggregation)
7. [Grafana Tempo — Distributed Tracing](#7-grafana-tempo--distributed-tracing)
8. [Grafana — Visualization](#8-grafana--visualization)
9. [Docker & Docker Compose](#9-docker--docker-compose)
10. [Anomaly Injection — Chaos Engineering](#10-anomaly-injection--chaos-engineering)
11. [AIOps Agent — AI-Powered Diagnosis](#11-aiops-agent--ai-powered-diagnosis)
12. [Google Gemini AI Integration](#12-google-gemini-ai-integration)
13. [RED Metrics & SRE Concepts](#13-red-metrics--sre-concepts)
14. [Networking & Communication](#14-networking--communication)
15. [Python Concepts Used](#15-python-concepts-used)
16. [Security & Configuration](#16-security--configuration)
17. [Full Scenario-Based Questions](#17-full-scenario-based-questions)

---

## 1. Project Overview — In Simple Words

### 🏗️ What is this project?

Imagine you own a small online shop. It has two workers:
- **Order Worker** (order-service): Takes customer orders
- **Payment Worker** (payment-service): Processes the money

Now, sometimes these workers slow down, crash, or run out of memory. You want to **know when this happens** and **understand why**. That's what this project does.

The project has four main parts:
1. **The Shop** — Two microservices (order + payment) that handle real API calls
2. **The Watchers** — OpenTelemetry, Prometheus, Loki, Tempo — tools that record everything that happens
3. **The Dashboard** — Grafana shows pretty graphs so humans can see what's happening
4. **The AI Doctor** — A Python agent powered by Google Gemini that reads all the data and tells you exactly what broke and how to fix it

### 🔄 How does data flow?

```
[Customer Request]
       ↓
 [order-service]  ──sends telemetry──→  [OTel Collector]
       ↓                                       ↓
 [payment-service] ──sends telemetry──→  [Prometheus] [Loki] [Tempo]
                                               ↓
                                          [Grafana] ← humans watch here
                                               ↓
                                         [AIOps Agent] ← queries data
                                               ↓
                                         [Gemini AI] ← gives diagnosis
```

---

## 2. Architecture & System Design

### ❓ Q1: What is a microservices architecture? How is it used in this project?

**Answer:**  
Microservices architecture means you break a big application into **small, independent services**, each doing one job.

In this project:
- **order-service** only handles creating orders
- **payment-service** only handles processing payments

They talk to each other over HTTP. Each runs in its own Docker container and can fail independently — if payment-service crashes, order-service can still respond (with an error message instead of crashing itself).

**Why it matters:** Easier to scale, deploy, and debug individual parts.

---

### ❓ Q2: What is the "observability stack" in this project?

**Answer:**  
The observability stack = the set of tools that let you watch the system's health. The three pillars are:

| Pillar | Tool Used | What it stores |
|--------|-----------|----------------|
| **Metrics** | Prometheus | Numbers over time (CPU %, request count) |
| **Logs** | Loki | Text messages from services |
| **Traces** | Tempo | The journey of one request across services |

Grafana is the UI that shows all three. OpenTelemetry is the "reporter" that sends data from services to all three tools.

---

### ❓ Q3: What is the "three pillars of observability"?

**Answer:**
1. **Metrics** — Numbers that change over time. Example: `http_requests_total = 500`. Tells you *what* is happening.
2. **Logs** — Time-stamped text records. Example: `[ERROR] Payment failed: timeout`. Tells you *what happened* in words.
3. **Traces** — The complete path of one request. Example: User hit `/order` → order-service called `/pay` on payment-service → took 3 seconds. Tells you *where* the slowness happened.

---

### ❓ Q4: Explain the data flow from a user request to Grafana.

**Answer:**
1. A user (or the anomaly injector script) sends `POST /order` to **order-service** on port 8000
2. order-service processes the request, then calls **payment-service** at `/pay`
3. Both services emit **OpenTelemetry data** (traces, metrics, logs) to the **OTel Collector** on port 4318
4. OTel Collector **routes** the data:
   - Metrics → Prometheus (port 8889)
   - Logs → Loki (port 3100)
   - Traces → Tempo (port 4317)
5. **Prometheus** scrapes the metrics endpoint every 5 seconds
6. **Grafana** reads from all three data sources and shows live dashboards
7. The **AIOps Agent** queries Prometheus and Loki directly to feed data to Gemini

---

### ❓ Q5: What is the difference between push and pull model in monitoring?

**Answer:**
- **Push model**: Services *send* (push) their data to a central collector. **This project uses push for logs and traces** — OTel SDK pushes to OTel Collector.
- **Pull model**: A central server *fetches* (pulls) data from services. **This project uses pull for metrics** — Prometheus scrapes (pulls) from OTel Collector's endpoint every 5 seconds.

---

## 3. Microservices — FastAPI & Python

### ❓ Q6: What is FastAPI? Why was it chosen?

**Answer:**  
FastAPI is a modern Python web framework for building APIs. It was chosen because:
- **Very fast** — built on ASGI (Async Server Gateway Interface), handles many requests simultaneously
- **Automatic validation** — using Pydantic models, if you send wrong data, it automatically returns a 422 error
- **Auto-generated docs** — visit `http://localhost:8000/docs` to see interactive API documentation automatically
- **Async support** — uses Python's `async/await` to handle requests without blocking

---

### ❓ Q7: What is Pydantic? How is it used here?

**Answer:**  
Pydantic is a Python library for **data validation using type hints**.

In this project:
```python
class OrderRequest(BaseModel):
    item: str
    quantity: int
    price: float
```
When someone sends a POST request to `/order`, FastAPI uses this model to automatically:
- Check that `item` is a string
- Check that `quantity` is a number
- Return a clear error if fields are missing or wrong type

---

### ❓ Q8: What is middleware? How does telemetry middleware work in this project?

**Answer:**  
Middleware is a function that runs **on every request and response**, before and after your actual endpoint code.

In this project, `telemetry_middleware` intercepts every HTTP request:
1. Records the start time
2. Starts an OpenTelemetry **span** (for tracing)
3. Calls the actual endpoint
4. When response comes back, calculates **duration**
5. Records metrics: increments request counter, records duration in histogram
6. Logs the result

This means you don't have to add telemetry code to every single endpoint — one middleware covers everything.

---

### ❓ Q9: What are async/await in Python? Why use them in a web service?

**Answer:**  
`async` and `await` are Python keywords for **non-blocking code**.

Normal (blocking) code: While waiting for payment-service to respond, the server can't handle other requests. Everyone queues up.

Async code: While waiting for payment-service to respond, the server handles other requests. Much more efficient.

```python
# This is async - won't block other requests while waiting
async with httpx.AsyncClient() as client:
    response = await client.post(payment_url, json=payload)
```

---

### ❓ Q10: What is HTTPException in FastAPI?

**Answer:**  
`HTTPException` is FastAPI's way to return HTTP error responses with a status code and message.

```python
raise HTTPException(status_code=500, detail="Database transaction failure")
```
This immediately stops processing and returns:
```json
{"detail": "Database transaction failure"}
```
with HTTP status 500.

In this project, it's used to simulate errors when anomalies are injected.

---

### ❓ Q11: What HTTP status codes does this project use and what do they mean?

**Answer:**

| Code | Meaning | Used When |
|------|---------|-----------|
| 200 | OK | Request succeeded |
| 400 | Bad Request | Invalid anomaly type sent |
| 500 | Internal Server Error | Simulated database failure during anomaly |
| 502 | Bad Gateway | Payment service returned an error to order-service |
| 503 | Service Unavailable | Payment service is completely unreachable |

---

### ❓ Q12: What is httpx and why use it instead of requests?

**Answer:**  
`httpx` is a Python HTTP client library. It's used here instead of `requests` because:
- **Supports async** — `requests` is synchronous only; `httpx` has an `AsyncClient`
- Since order-service uses `async def` endpoints, it needs an async HTTP client to call payment-service without blocking

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(url, json=payload, headers=headers)
```

---

### ❓ Q13: What is psutil?

**Answer:**  
`psutil` is a Python library for reading **system resource information** — CPU usage, memory usage, disk, network.

In this project:
```python
psutil.cpu_percent()              # Returns CPU usage like 45.2
psutil.virtual_memory().percent   # Returns memory usage like 67.8
```
These values become OpenTelemetry metrics that flow to Prometheus and show up in Grafana.

---

## 4. OpenTelemetry — The Instrumentation Layer

### ❓ Q14: What is OpenTelemetry (OTel)?

**Answer:**  
OpenTelemetry is an **open-source standard and SDK** for collecting telemetry data (metrics, logs, traces) from your application — in a vendor-neutral way.

Think of it as a **universal reporter**. Instead of writing code specifically for Prometheus, then separately for Loki, then for Tempo — you write OTel code once and the OTel Collector routes it to all three.

This project instruments both services with the OTel SDK. Both services send all their data to the OTel Collector using OTLP (OpenTelemetry Protocol).

---

### ❓ Q15: What are the three OTel signal types used?

**Answer:**

| Signal | SDK Used | Sent To |
|--------|----------|---------|
| **Traces** | `opentelemetry.sdk.trace` | Tempo (via OTel Collector) |
| **Metrics** | `opentelemetry.sdk.metrics` | Prometheus (via OTel Collector) |
| **Logs** | `opentelemetry.sdk._logs` | Loki (via OTel Collector) |

---

### ❓ Q16: What is a Span in OpenTelemetry?

**Answer:**  
A **span** is a single unit of work — one operation with a start time, end time, and metadata (attributes).

For example: "Processing order request" is a span. Inside that span, calling payment-service creates a **child span**.

Together, all spans for one user request form a **trace** — a complete timeline of everything that happened.

In the code:
```python
with tracer.start_as_current_span("POST /order", context=context, kind=trace.SpanKind.SERVER) as span:
    span.set_attribute("http.method", "POST")
    span.set_attribute("http.status_code", 200)
```

---

### ❓ Q17: What is distributed tracing? What problem does it solve?

**Answer:**  
In microservices, one user request touches multiple services. **Distributed tracing** tracks the entire journey.

**Problem:** User says "my order is slow." Is it order-service? payment-service? The database? Without tracing, you're guessing.

**Solution:** Each service adds trace information to requests. Tempo can show you: "Your request spent 50ms in order-service and 2.5 SECONDS in payment-service — that's your problem."

---

### ❓ Q18: What is Context Propagation? How does inject/extract work?

**Answer:**  
Context propagation is how trace information travels between services.

When order-service calls payment-service:
1. **`inject(headers)`** — OTel writes trace ID into the HTTP headers before sending
2. Payment-service receives the request
3. **`extract(request.headers)`** — OTel reads the trace ID from headers
4. Payment-service continues the same trace instead of starting a new one

This creates a connected trace across both services in Tempo.

---

### ❓ Q19: What is OTLP (OpenTelemetry Protocol)?

**Answer:**  
OTLP is the **wire protocol** — the format used to send OTel data over the network.

Services send data to the OTel Collector using OTLP. Two transport options:
- **gRPC** on port 4317 — binary, very efficient
- **HTTP/Protobuf** on port 4318 — used in this project (easier to configure)

---

### ❓ Q20: What is a TracerProvider and why set it up manually?

**Answer:**  
`TracerProvider` is the factory that creates `Tracer` objects and manages how spans are exported.

In this project, it's configured manually to:
1. Attach a **Resource** (service name and version metadata)
2. Add a **BatchSpanProcessor** — collects spans in memory and sends them in batches (more efficient than sending one-by-one)
3. Use **OTLPSpanExporter** — sends batches to the OTel Collector

---

### ❓ Q21: What is the difference between a Counter, Histogram, and Gauge?

**Answer:**

| Metric Type | Description | Example in Project |
|-------------|-------------|-------------------|
| **Counter** | Only goes up, never resets | `http_requests_total` — total number of requests ever |
| **Histogram** | Tracks distribution of values in buckets | `http_request_duration_seconds` — how many requests took 0-0.1s, 0.1-0.5s, etc. |
| **Gauge** | Can go up or down, point-in-time value | `system_cpu_usage` — current CPU % right now |

---

### ❓ Q22: What is an Observable Gauge?

**Answer:**  
A regular gauge you set manually (`gauge.record(45.2)`). An **Observable Gauge** uses a **callback function** — OTel calls your function whenever it needs the current value.

```python
def get_cpu_usage(options):
    yield metrics.Observation(psutil.cpu_percent(), {"service_name": SERVICE_NAME})

meter.create_observable_gauge("system_cpu_usage", callbacks=[get_cpu_usage])
```

This is better for CPU/memory because you want the *current* value at export time, not a value you cached earlier.

---

### ❓ Q23: What is BatchSpanProcessor vs SimpleSpanProcessor?

**Answer:**
- **SimpleSpanProcessor**: Exports each span immediately when it finishes. Simple but slow — blocks the request thread.
- **BatchSpanProcessor**: Collects spans in a buffer and exports them in batches in a background thread. This project uses `BatchSpanProcessor` for better performance.

---

### ❓ Q24: What is PeriodicExportingMetricReader?

**Answer:**  
This is the metrics equivalent of BatchSpanProcessor. It runs a background thread that every `export_interval_millis` milliseconds, collects all metric values and sends them to the exporter.

In this project, it's set to 5000ms (every 5 seconds):
```python
reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
```

---

### ❓ Q25: What is a Resource in OpenTelemetry?

**Answer:**  
A Resource describes **what** is sending the telemetry — the identity of the service.

```python
resource = Resource.create({"service.name": "order-service", "service.version": "1.0.0"})
```

This metadata gets attached to every metric, log, and trace from this service. In Grafana/Prometheus, you can filter by `service_name="order-service"`.

---

## 5. Prometheus — Metrics Database

### ❓ Q26: What is Prometheus?

**Answer:**  
Prometheus is an **open-source time-series database** designed for storing metrics. A "time-series" means: a metric value recorded with a timestamp, again and again over time.

Example: Every 5 seconds, Prometheus records CPU usage → you get a line graph over time.

Prometheus also has a query language called **PromQL** to slice and analyze those metrics.

---

### ❓ Q27: How does Prometheus collect data in this project?

**Answer:**  
Prometheus uses the **pull model** — it actively scrapes (fetches) metrics from a target endpoint.

In `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
```

Every 5 seconds (`scrape_interval: 5s`), Prometheus visits `http://otel-collector:8889/metrics`, reads all metric values, and stores them.

---

### ❓ Q28: What is PromQL? Give examples from this project.

**Answer:**  
PromQL (Prometheus Query Language) lets you query and calculate things from stored metrics.

**Examples used in the AIOps agent:**

```promql
# Current active anomalies
otel_active_anomalies

# Request rate (QPS) averaged over 2 minutes
sum(rate(otel_http_requests_total[2m])) by (service_name)

# 95th percentile latency
histogram_quantile(0.95, sum(rate(otel_http_request_duration_seconds_bucket[2m])) by (le, service_name))

# Error rate percentage (5xx errors)
sum(rate(otel_http_requests_total{http_status=~"5.."}[2m])) by (service_name) 
/ 
sum(rate(otel_http_requests_total[2m])) by (service_name) * 100
```

---

### ❓ Q29: What is `rate()` in PromQL?

**Answer:**  
`rate()` calculates **how fast a counter is increasing per second**, averaged over a time window.

`http_requests_total` is a counter — it only goes up. `rate(http_requests_total[2m])` tells you: "How many requests per second, averaged over the last 2 minutes?" This gives you QPS (queries per second).

---

### ❓ Q30: What is `histogram_quantile()` and p95 latency?

**Answer:**  
A histogram splits values into buckets (e.g., "how many requests took < 0.1s, < 0.5s, < 1s...").

`histogram_quantile(0.95, ...)` calculates the **95th percentile** — the latency that 95% of requests are BELOW. Only 5% of requests are slower than this.

**Why p95?** Average latency hides outliers. p95 shows you the experience of the "slow" users. A p95 of 3 seconds means 5% of your users wait more than 3 seconds.

---

### ❓ Q31: What is label matching in PromQL like `{http_status=~"5.."}`?

**Answer:**  
Labels are key-value pairs attached to metrics (like tags). You can filter by them:
- `=` exact match: `{service_name="order-service"}`
- `=~` regex match: `{http_status=~"5.."}` matches 500, 502, 503 etc.
- `!=` not equal: `{service_name!="order-service"}`

In this project: `{http_status=~"5.."}` filters for only 5xx error responses.

---

## 6. Loki — Log Aggregation

### ❓ Q32: What is Loki?

**Answer:**  
Loki is Grafana's **log aggregation system** — it stores and indexes logs. It's like Prometheus, but for log lines instead of numbers.

The key difference from other log tools (Elasticsearch): Loki only indexes the **labels** (metadata), not the full log content. This makes it cheaper to store and faster to write, but slower to search full-text.

---

### ❓ Q33: How do logs get from services to Loki?

**Answer:**  
The flow:
1. Service uses Python's standard `logging` module
2. OTel `LoggingHandler` intercepts log records and converts them to OTel log signals
3. `BatchLogRecordProcessor` batches them
4. `OTLPLogExporter` sends them to OTel Collector via HTTP
5. OTel Collector's Loki exporter pushes them to Loki's API: `POST /loki/api/v1/push`

---

### ❓ Q34: What is LogQL? How is it used?

**Answer:**  
LogQL is Loki's query language (similar to PromQL but for logs).

In the AIOps agent:
```python
query_loki(loki_url, '{exporter="loki"}', start_ns)
```

`{exporter="loki"}` is a LogQL stream selector — it finds all logs that have the label `exporter="loki"` (which all OTel-pushed logs have).

You can also filter: `{exporter="loki"} |= "ERROR"` — only lines containing "ERROR".

---

### ❓ Q35: What does `query_range` mean in the Loki API?

**Answer:**  
Loki's API has `/loki/api/v1/query_range` — it returns logs in a **time range**.

Parameters used:
- `query`: the LogQL selector
- `limit`: max number of log lines (150 in this project)
- `start`: start time in nanoseconds since Unix epoch

The agent queries the last 5 minutes: `start_ns = (time.time() - 300) * 1_000_000_000`

---

## 7. Grafana Tempo — Distributed Tracing

### ❓ Q36: What is Tempo?

**Answer:**  
Tempo is Grafana's **distributed tracing backend**. It stores trace data sent via OTLP and lets you search for and visualize individual request traces.

In Grafana, you can click on a trace to see a "flame graph" — a visual timeline showing exactly how long each service took to process a request.

---

### ❓ Q37: How does Tempo fit into this project?

**Answer:**  
1. Services generate spans (via OTel SDK)
2. OTel Collector receives them and forwards to Tempo via OTLP gRPC (port 4317)
3. Tempo stores the traces
4. Grafana is configured with Tempo as a datasource
5. When you see high latency in Prometheus, you switch to Grafana and look at the actual traces in Tempo to see exactly which service was slow

---

### ❓ Q38: What is the difference between metrics and traces?

**Answer:**

| | Metrics | Traces |
|--|---------|--------|
| **What it stores** | Aggregated numbers | Individual request journeys |
| **Storage cost** | Low | High |
| **Use case** | Alerts, dashboards, trends | Debugging specific slow/failed requests |
| **Example** | "p95 latency is 3s" | "Order #12345 was slow because payment-service took 2.8s" |

---

## 8. Grafana — Visualization

### ❓ Q39: What is Grafana?

**Answer:**  
Grafana is an **open-source observability dashboard platform**. It connects to multiple data sources (Prometheus, Loki, Tempo) and lets you build visual dashboards.

In this project, Grafana is pre-configured with:
- **Datasources** (auto-configured via `datasources.yaml`): Prometheus, Loki, Tempo
- **Dashboards** (auto-provisioned): "AIOps Observability Control Center"

Login: `http://localhost:3000` — admin/admin

---

### ❓ Q40: What is provisioning in Grafana?

**Answer:**  
Provisioning means automatically configuring Grafana from files on startup, instead of using the UI.

This project mounts YAML files into Grafana's container:
```
./grafana/datasources/datasources.yaml → /etc/grafana/provisioning/datasources/
./grafana/dashboards/ → /etc/grafana/provisioning/dashboards/
```

When Grafana starts, it reads these files and sets up datasources and dashboards automatically. This means you don't need to manually click "Add datasource" every time.

---

## 9. Docker & Docker Compose

### ❓ Q41: What is Docker? What problem does it solve?

**Answer:**  
Docker is a **containerization platform**. A container packages your application + all its dependencies together, so it runs identically on any machine.

**Problem it solves:** "It works on my machine!" — With Docker, the application runs the same on your laptop, your colleague's machine, and production servers.

---

### ❓ Q42: What is a Dockerfile? Explain the one in this project.

**Answer:**  
A Dockerfile is a recipe for building a Docker image (a snapshot of your application and its environment).

```dockerfile
FROM python:3.11-slim        # Start from a minimal Python image
WORKDIR /app                 # Set working directory inside container
COPY requirements.txt .      # Copy dependency list
RUN pip install -r requirements.txt  # Install dependencies
COPY . .                     # Copy application code
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]  # Start the server
```

---

### ❓ Q43: What is Docker Compose? How is it used here?

**Answer:**  
Docker Compose lets you define and run **multiple Docker containers together** using a single `docker-compose.yml` file.

In this project, `docker-compose.yml` defines 7 services:
1. `order-service` — the order API
2. `payment-service` — the payment API
3. `otel-collector` — telemetry router
4. `prometheus` — metrics database
5. `loki` — log database
6. `tempo` — trace database
7. `grafana` — dashboard UI

One command `docker compose up -d` starts all 7 containers.

---

### ❓ Q44: What is `depends_on` in Docker Compose?

**Answer:**  
`depends_on` controls startup order — a service won't start until its dependencies are running.

```yaml
order-service:
  depends_on:
    - otel-collector
    - payment-service
```

This ensures otel-collector and payment-service start before order-service (because order-service needs to connect to both on startup).

---

### ❓ Q45: What is a Docker network? How is it configured here?

**Answer:**  
Docker networks let containers talk to each other using **service names as hostnames** instead of IP addresses.

```yaml
networks:
  observability-network:
    driver: bridge
```

All 7 services join this network. So order-service can reach payment-service at `http://payment-service:8001` — Docker's DNS resolves "payment-service" to the container's IP.

---

### ❓ Q46: What does `ports: "8000:8000"` mean?

**Answer:**  
Port mapping: `HOST_PORT:CONTAINER_PORT`

- Left side (8000): Port on your Windows machine
- Right side (8000): Port inside the Docker container

So when you visit `http://localhost:8000`, Docker forwards it to port 8000 inside the order-service container.

---

### ❓ Q47: What are environment variables in Docker? Why use them?

**Answer:**  
Environment variables pass configuration to containers at runtime without hardcoding values in code.

```yaml
environment:
  - PAYMENT_SERVICE_URL=http://payment-service:8001
  - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

In Python: `os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8001")`

The default value is for running locally; the Docker env var overrides it when running in containers. This is a **12-Factor App** best practice.

---

### ❓ Q48: What is uvicorn?

**Answer:**  
`uvicorn` is an **ASGI server** — it runs Python async web applications like FastAPI.

```dockerfile
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- `app:app` — module `app.py`, variable `app` (the FastAPI instance)
- `--host 0.0.0.0` — listen on all network interfaces (needed inside Docker)
- `--port 8000` — which port to listen on

---

## 10. Anomaly Injection — Chaos Engineering

### ❓ Q49: What is Chaos Engineering?

**Answer:**  
Chaos Engineering is the practice of **intentionally breaking things** in a controlled way to test how a system responds.

Netflix pioneered it with "Chaos Monkey" which randomly killed production servers.

In this project, the anomaly injector is a simplified chaos engineering tool — it can inject:
- **Latency** — adds artificial delays
- **Error Rate** — makes requests randomly fail
- **CPU Spike** — runs computation-heavy threads
- **Memory Leak** — keeps allocating memory without freeing it

---

### ❓ Q50: How does latency injection work in this project?

**Answer:**  
The anomaly injector calls the service's `/anomaly` endpoint:
```python
POST /anomaly
{"anomaly_type": "latency", "value": 2.5}
```

The service stores this in a global dictionary:
```python
ACTIVE_ANOMALIES = {"latency": 2.5, ...}
```

On every subsequent request to `/order` or `/pay`:
```python
latency = ACTIVE_ANOMALIES["latency"]
if latency > 0:
    time.sleep(latency)  # Sleep 2.5 seconds!
```

This makes every request slow. The injector resets it to 0 after the duration expires.

---

### ❓ Q51: How does the error rate anomaly work?

**Answer:**  
```python
error_rate = ACTIVE_ANOMALIES["error_rate"]  # e.g., 0.4 = 40%
if error_rate > 0:
    if random.random() < error_rate:  # 40% chance this is True
        raise HTTPException(status_code=500, detail="Database transaction failure")
```

`random.random()` returns a float between 0.0 and 1.0. If the number is less than `error_rate` (0.4), the request fails. So statistically, 40% of requests will throw a 500 error.

---

### ❓ Q52: How does the CPU spike simulation work?

**Answer:**  
```python
def cpu_heavy_loop():
    while cpu_threads_running:
        _ = [x*x for x in range(5000)]  # CPU-intensive computation
        time.sleep(0.001)

# Start 4 threads running this simultaneously
for _ in range(4):
    t = threading.Thread(target=cpu_heavy_loop, daemon=True)
    t.start()
```

4 threads simultaneously run a busy loop of calculations. This saturates CPU cores, driving CPU usage to near 100%.

---

### ❓ Q53: How does the memory leak simulation work?

**Answer:**  
```python
memory_leak_store = []  # Global list — holds references to memory

def memory_leak_worker():
    while memory_leak_running:
        large_chunk = "X" * (10 * 1024 * 1024)  # 10MB string
        memory_leak_store.append(large_chunk)    # Never freed!
        time.sleep(2)
```

Every 2 seconds, 10MB of memory is allocated and stored in a global list. Because the list holds a **reference** to the memory, Python's garbage collector won't free it. Memory grows linearly.

When deactivated:
```python
memory_leak_store = []  # Remove all references
gc.collect()            # Force garbage collection
```

---

### ❓ Q54: What is `gc.collect()`?

**Answer:**  
`gc` is Python's garbage collector module. `gc.collect()` forces an immediate garbage collection cycle — Python scans for objects with no references and frees their memory.

Normally Python's GC runs automatically. After clearing `memory_leak_store`, `gc.collect()` immediately reclaims the freed memory instead of waiting for the next automatic cycle.

---

### ❓ Q55: What is a daemon thread?

**Answer:**  
A daemon thread is a background thread that **automatically dies when the main program exits**.

```python
t = threading.Thread(target=cpu_heavy_loop, daemon=True)
```

Without `daemon=True`, if you press Ctrl+C, the main program exits but the CPU spike threads keep running! With `daemon=True`, they automatically stop when the process exits.

---

### ❓ Q56: What is the cascading failure pattern shown in this project?

**Answer:**  
**Cascading failure** = one service's problem causing another service to fail.

Example flow:
1. Inject error_rate=0.4 on **payment-service** (40% of /pay requests return 500)
2. **order-service** calls `/pay` for every order → 40% of those calls fail
3. order-service receives 500 from payment-service → returns **502 Bad Gateway** to the user
4. User sees: "Order failed!" — but the root cause is payment-service, not order-service
5. **Gemini diagnoses this**: "Payment-service error_rate anomaly is causing cascading 502s in order-service"

---

## 11. AIOps Agent — AI-Powered Diagnosis

### ❓ Q57: What is AIOps?

**Answer:**  
**AIOps** = Artificial Intelligence for IT Operations. It uses AI/ML to:
- Automatically detect anomalies
- Correlate events across systems
- Perform root-cause analysis (RCA)
- Suggest remediation steps

In this project, the AIOps agent replaces a human SRE (Site Reliability Engineer) doing manual investigation by automatically querying metrics + logs and feeding them to Gemini AI for diagnosis.

---

### ❓ Q58: What are the two modes of the AIOps agent?

**Answer:**

| Mode | Command | What it does |
|------|---------|-------------|
| `--detect` | `python agent.py --detect` | Fetches and prints metrics from Prometheus as a CLI table. No AI. Quick status check. |
| `--diagnose` | `python agent.py --diagnose` | Fetches metrics + logs, sends to Gemini AI, prints full SRE incident report |

---

### ❓ Q59: What is the RED method?

**Answer:**  
**RED** = **R**ate, **E**rrors, **D**uration — the three key metrics for any microservice:

| Metric | What it measures | PromQL in this project |
|--------|----------------|----------------------|
| **Rate** | Requests per second (QPS) | `sum(rate(otel_http_requests_total[2m])) by (service_name)` |
| **Errors** | % of requests that fail | `sum(rate(otel_http_requests_total{http_status=~"5.."}[2m])) / sum(rate(...))*100` |
| **Duration** | How long requests take (p95 latency) | `histogram_quantile(0.95, ...)` |

The agent collects all three and presents them to Gemini.

---

### ❓ Q60: What is root-cause analysis (RCA)?

**Answer:**  
RCA = finding the **real underlying reason** for an incident, not just the symptoms.

Example:
- **Symptom**: Users are getting 502 errors on the order API
- **Obvious cause**: order-service is returning errors  
- **Root cause (via RCA)**: payment-service has a 40% error rate due to a simulated database timeout anomaly, causing order-service's downstream calls to fail, resulting in 502 responses

The Gemini agent performs this multi-step reasoning automatically.

---

### ❓ Q61: How does the agent format data for Gemini?

**Answer:**  
The agent compiles metrics and logs into a structured text context:

```python
prompt = DIAGNOSTIC_TEMPLATE.format(
    metrics_summary=metrics_summary,  # Table of QPS, latency, error rates
    loki_logs=formatted_logs           # Last 80 log lines
)
```

The `metrics_summary` is a tabulated string (using `tabulate`) showing:
- Active anomalies
- QPS per service
- p95 latency per service
- Error rate per service
- CPU and memory usage

This structured text is passed to Gemini's API as the user prompt.

---

### ❓ Q62: What is `tabulate`?

**Answer:**  
`tabulate` is a Python library for formatting data into ASCII tables.

```python
from tabulate import tabulate
tabulate(dataframe, headers="keys", tablefmt="grid", showindex=False)
```

Output looks like:
```
+---------------+--------------+-------------+
| Service       | QPS (avg 2m) | p95 Latency |
+===============+==============+=============+
| order-service | 1.97         | 0.0230s     |
+---------------+--------------+-------------+
```

This makes the data readable for both humans and AI.

---

### ❓ Q63: What is pandas used for in this project?

**Answer:**  
`pandas` is Python's data analysis library. In the agent:

1. Prometheus API returns JSON data → parsed into a `pandas.DataFrame` for easy manipulation
2. Multiple metric DataFrames (QPS, latency, errors) are merged on "Service" column using `pd.merge()`
3. `df.fillna("N/A")` fills missing values gracefully
4. Used with `tabulate` to format tables

---

### ❓ Q64: Why limit logs to 80 lines for Gemini?

**Answer:**  
```python
for l in logs[-80:]:  # Limit to last 80 lines
```

AI models have a **context window** — a maximum number of tokens (words/characters) they can process at once. Sending thousands of log lines would:
1. Hit the token limit and fail
2. Make the model focus on irrelevant old logs
3. Cost more API money

80 recent log lines gives Gemini enough context without exceeding practical limits.

---

## 12. Google Gemini AI Integration

### ❓ Q65: What is Google Gemini?

**Answer:**  
Gemini is Google's family of large language models (LLMs). It can understand and generate human language, analyze data, reason across complex information, and provide actionable insights.

In this project, `gemini-2.5-flash` is used — a fast, cost-effective model balanced between speed and intelligence.

---

### ❓ Q66: What is a system prompt vs user prompt?

**Answer:**

| | System Prompt | User Prompt |
|--|--------------|-------------|
| **Set by** | Developer (fixed) | Generated per request |
| **Purpose** | Sets AI personality and rules | Contains the actual data to analyze |
| **In this project** | `AIOPS_SYSTEM_PROMPT` — tells Gemini it's an SRE agent and defines the output format | `DIAGNOSTIC_TEMPLATE` — filled with current metrics and logs |

The system prompt instructs Gemini to always output a specific markdown report format with 5 sections.

---

### ❓ Q67: What is `temperature=0.2` in Gemini config?

**Answer:**  
Temperature controls **creativity vs consistency** in AI responses:
- `temperature=0.0` — completely deterministic, same input always gives same output
- `temperature=1.0` — highly creative, varied, unpredictable
- `temperature=0.2` — mostly factual and consistent, slight variation allowed

For SRE diagnosis, you want **consistent, factual analysis** — not creative storytelling. Low temperature (0.2) ensures the AI sticks to the data.

---

### ❓ Q68: What is the Google GenAI Python SDK?

**Answer:**  
```python
from google import genai
from google.genai import types

client = genai.Client()  # Uses GEMINI_API_KEY env var automatically
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        system_instruction=AIOPS_SYSTEM_PROMPT,
        temperature=0.2
    )
)
print(response.text)
```

The SDK handles authentication, HTTP calls to Gemini API, and response parsing. The API key is read from the `GEMINI_API_KEY` environment variable.

---

### ❓ Q69: What is prompt engineering?

**Answer:**  
Prompt engineering is the art of crafting instructions for AI models to get high-quality, structured outputs.

In this project, the system prompt uses several techniques:
1. **Role assignment**: "You are Antigravity-SRE, a premium AIOps Site Reliability Engineer"
2. **Structured output format**: Defines exact markdown sections the AI must use
3. **Specific examples**: "If payment-service has high latency, point out how it cascades to order-service"
4. **Negative instructions**: "Do not use generic answers"
5. **Context description**: Lists exactly what data will be provided

Good prompts = better, more consistent AI responses.

---

## 13. RED Metrics & SRE Concepts

### ❓ Q70: What is SRE (Site Reliability Engineering)?

**Answer:**  
SRE is a discipline where software engineers apply software engineering principles to infrastructure and operations problems. Core responsibilities:
- **Monitoring** — know when things break before users do
- **Incident response** — quickly diagnose and fix outages
- **Postmortems** — analyze what went wrong and prevent recurrence
- **Reliability** — set and meet SLOs (Service Level Objectives)

This project automates the monitoring + incident response part.

---

### ❓ Q71: What is an SLO, SLA, and SLI?

**Answer:**

| Term | Meaning | Example |
|------|---------|---------|
| **SLI** (Service Level Indicator) | The actual measured metric | p95 latency = 250ms |
| **SLO** (Service Level Objective) | Your target goal | p95 latency must be < 500ms, 99.9% of the time |
| **SLA** (Service Level Agreement) | Legal contract with customer | If uptime drops below 99.5%, you get a refund |

---

### ❓ Q72: What is QPS?

**Answer:**  
**QPS** = Queries Per Second. It measures how many requests your service receives every second.

In the agent: `rate(otel_http_requests_total[2m])` calculates the average request rate over the last 2 minutes.

Low QPS could mean: traffic is down, service is down, or load balancer issue.
High QPS spike could mean: traffic surge or DDoS attack.

---

### ❓ Q73: What is an incident report in SRE?

**Answer:**  
An incident report documents a system failure. Good reports include:
1. **Executive Summary** — what broke, when, impact
2. **Timeline** — when things happened
3. **Root Cause** — the underlying reason (not the symptom)
4. **Impact** — how many users/systems affected
5. **Remediation** — what was done to fix it
6. **Prevention** — how to stop it happening again

The Gemini-generated output follows this structure with 5 markdown sections.

---

## 14. Networking & Communication

### ❓ Q74: What is REST API?

**Answer:**  
REST (Representational State Transfer) is an architectural style for building web APIs using HTTP methods:

| Method | Action | Example |
|--------|--------|---------|
| GET | Retrieve data | `GET /health` |
| POST | Create/send data | `POST /order` with body |
| PUT | Update data | - |
| DELETE | Delete data | - |

This project uses GET for health checks and POST for orders, payments, and anomaly injection.

---

### ❓ Q75: What is JSON and how is it used?

**Answer:**  
JSON (JavaScript Object Notation) is the standard data format for REST APIs. It's human-readable text that represents structured data.

```json
{"item": "Laptop Pro", "quantity": 2, "price": 1299.99}
```

In this project:
- Anomaly injector sends JSON payloads to services
- Services return JSON responses
- Prometheus and Loki APIs return JSON data
- Gemini API communicates in JSON internally

---

### ❓ Q76: What is gRPC vs HTTP?

**Answer:**

| | HTTP/REST | gRPC |
|--|-----------|------|
| **Data format** | JSON (text) | Protocol Buffers (binary) |
| **Speed** | Slower | Faster (binary is smaller) |
| **Human-readable** | Yes | No |
| **Use case** | Public APIs, simple services | High-performance internal services |

In this project, OTel to Tempo uses gRPC (port 4317) for efficiency. OTel from services to Collector uses HTTP (port 4318) for simplicity.

---

### ❓ Q77: What are request headers? How are they used for trace propagation?

**Answer:**  
HTTP headers are key-value pairs sent with every request, containing metadata.

Standard headers: `Content-Type: application/json`, `Authorization: Bearer token123`

OTel propagation uses special headers:
- `traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`

When order-service calls payment-service:
```python
headers = {}
inject(headers)  # Adds traceparent header
await client.post(payment_url, headers=headers)
```

Payment-service reads this header to join the existing trace instead of starting a new one.

---

## 15. Python Concepts Used

### ❓ Q78: What is a global variable in Python? How is it used in anomaly management?

**Answer:**  
A global variable is accessible across the entire module. 

In this project, `ACTIVE_ANOMALIES` is a global dictionary that all request handlers share:
```python
ACTIVE_ANOMALIES = {"latency": 0.0, "error_rate": 0.0, ...}
```

When `/anomaly` endpoint updates it, the next request to `/order` immediately reads the new value. This is simple but has a caveat: in production, you'd use a database or cache instead (global state doesn't work with multiple instances).

---

### ❓ Q79: What is threading in Python? What is the GIL?

**Answer:**  
`threading` creates multiple execution paths within one Python process.

The **GIL (Global Interpreter Lock)** is Python's mechanism that only allows one thread to execute Python code at a time. This means:
- Python threads don't truly run in parallel for CPU-bound work
- BUT daemon threads still consume CPU because the GIL switches between threads rapidly

In this project, the CPU spike uses 4 threads. Even with the GIL, these threads compete for CPU time and create significant load.

---

### ❓ Q80: What is argparse?

**Answer:**  
`argparse` is Python's standard library for parsing command-line arguments.

In the anomaly injector:
```python
parser.add_argument("--anomaly", choices=["latency", "error_rate", "cpu_spike", "memory_leak"])
parser.add_argument("--value", type=float, default=0.0)
parser.add_argument("--duration", type=int, default=30)
```

Usage: `python inject_anomalies.py --anomaly latency --service payment-service --value 2.5 --duration 45`

`argparse` validates the types and choices automatically.

---

### ❓ Q81: What is `add_mutually_exclusive_group` in argparse?

**Answer:**  
In the AIOps agent:
```python
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--detect", ...)
group.add_argument("--diagnose", ...)
```

This means: you MUST provide exactly ONE of `--detect` or `--diagnose`. You can't use both. If you don't provide either, argparse shows an error.

---

### ❓ Q82: What is a Python virtual environment?

**Answer:**  
A virtual environment is an isolated Python installation with its own packages. This prevents conflicts between projects.

```powershell
python -m venv venv          # Create
.\venv\Scripts\Activate.ps1  # Activate
pip install -r requirements.txt  # Install packages here, not globally
```

In this project, the services run in Docker (isolated by containers). The agent and injector scripts run on the host machine and should use a venv.

---

### ❓ Q83: What is `os.getenv()`?

**Answer:**  
`os.getenv()` reads environment variables. The second parameter is the default if the variable isn't set.

```python
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "order-service")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8001")
```

- Inside Docker: `PAYMENT_SERVICE_URL=http://payment-service:8001` is set in docker-compose.yml
- On host machine: env var not set, so default `http://payment-service:8001` is used (but that won't work from host — you'd need `http://localhost:8001`)

---

## 16. Security & Configuration

### ❓ Q84: How is the Gemini API key managed?

**Answer:**  
The API key is passed via environment variable — never hardcoded in source code.

```powershell
$env:GEMINI_API_KEY="your-key-here"  # PowerShell
```

Then in Python:
```python
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("[!] Error: GEMINI_API_KEY is not set")
    return
```

The Google GenAI SDK automatically reads `GEMINI_API_KEY` from the environment. This follows security best practices: no secrets in code, no secrets in git.

---

### ❓ Q85: What are the security risks of this project in production?

**Answer:**  
Several things fine for development but bad in production:

1. **`/anomaly` endpoint is open** — anyone can inject a CPU spike with an HTTP request. In production, this should require authentication.
2. **Hardcoded Grafana password** (`admin/admin`) — never use default passwords in production
3. **`insecure: true` on Tempo connection** — disables TLS. Production needs encrypted connections.
4. **No authentication on Prometheus/Loki** — anyone with network access can query your metrics and logs

---

## 17. Full Scenario-Based Questions

### ❓ Q86: Walk me through what happens when someone runs `inject_anomalies.py --anomaly latency --service payment-service --value 2.5 --duration 45`

**Answer (Full Flow):**

1. **Script starts**: Parses arguments — latency, payment-service, 2.5s delay, 45 seconds
2. **Traffic thread starts**: In background, sends POST /order requests every 0.5 seconds (2 QPS)
3. **Anomaly injected**: Script calls `POST http://localhost:8001/anomaly` with `{"anomaly_type": "latency", "value": 2.5}`
4. **Payment-service receives**: Sets `ACTIVE_ANOMALIES["latency"] = 2.5`
5. **Traffic effect**: Every `/order` call → order-service calls `/pay` → payment-service sleeps 2.5 seconds → order-service waits → user waits 2.5+ seconds
6. **Metrics record**: `http_request_duration_seconds` histogram records 2.5+ second durations
7. **OTel exports**: Every 5s, metrics pushed to OTel Collector → Prometheus
8. **Grafana shows**: p95 latency jumps from 0.02s to 2.5+s on the dashboard
9. **After 45s**: Script sends `{"anomaly_type": "latency", "value": 0}` to reset
10. **Latency normalizes**: Next requests complete in milliseconds again

---

### ❓ Q87: How would you run the AIOps agent to diagnose the above latency issue?

**Answer:**
```powershell
$env:GEMINI_API_KEY="your-key"
python aiops-agent/agent.py --diagnose
```

The agent:
1. Queries Prometheus for p95 latency → sees `payment-service` at 2.53s (very high)
2. Queries Prometheus for active anomalies → sees `payment-service: latency (2.5)`
3. Queries Loki → sees WARNING logs: "Injecting latency anomaly: sleeping 2.5 seconds"
4. Also sees logs from order-service: "Calling downstream payment service for order ord_XXXXX"
5. Sends all this to Gemini with the SRE system prompt
6. Gemini outputs:
   - **Executive Summary**: System degraded — payment-service latency anomaly causing cascading slowness
   - **Telemetry Analysis**: payment-service p95 at 2.5s, order-service p95 also elevated (due to downstream call)
   - **Root Cause**: Artificial latency injection of 2.5s on payment-service /pay endpoint
   - **Remediation**: Set latency anomaly to 0, investigate why latency was introduced

---

### ❓ Q88: What would you see in Grafana during a CPU spike on order-service?

**Answer:**

1. **Active Anomalies panel**: Shows `order-service: cpu_spike (1.0)` highlighted in red
2. **System Resource Utilization** panel: CPU usage for order-service jumps from ~5% to ~90-100%
3. **QPS panel**: May drop slightly (high CPU can slow request processing)
4. **p95 Latency panel**: May increase (CPU-bound requests take longer)
5. **Loki Log Stream**: Shows WARNING messages: "CPU spike active (4 threads running busy loops)"

The AIOps agent would identify: "4 background threads consuming CPU causing increased request processing times. Immediate action: stop CPU spike threads."

---

### ❓ Q89: How does this project demonstrate the concept of observability vs monitoring?

**Answer:**

| Monitoring | Observability |
|-----------|--------------|
| Checking if a service is up/down | Understanding **why** it's slow/failing |
| Pre-defined dashboards | Can answer new questions from data |
| Alerts on known failures | Can diagnose unknown/novel issues |

This project has both:
- **Monitoring**: Grafana dashboards show known metrics (QPS, latency, CPU)
- **Observability**: The three pillars (metrics + logs + traces) together let the Gemini agent ask and answer novel questions like "which specific downstream call is causing the slowness?"

---

### ❓ Q90: What is the difference between this project's approach and traditional log-based monitoring?

**Answer:**

| Traditional Log Monitoring | This Project |
|---------------------------|-------------|
| Humans read logs | AI reads logs |
| Siloed: logs separate from metrics | Correlated: logs + metrics + traces together |
| Alert fires → human investigates | AI automatically investigates and writes RCA |
| Rules-based: alert if "ERROR" count > 10 | Reasoning-based: AI understands context |
| Requires on-call human expertise | AI provides expert-level diagnosis 24/7 |

---

### ❓ Q91: How would you add a new microservice (e.g., inventory-service) to this platform?

**Answer:**

1. **Create the service**: `services/inventory-service/app.py` with FastAPI
2. **Add OTel instrumentation**: Same 3-signal setup as order/payment-service
3. **Create Dockerfile**: Same pattern as existing services
4. **Add to docker-compose.yml**: New service entry, same network, OTel env vars
5. **Update anomaly injector**: Add inventory-service URL to the reset_all_anomalies function
6. **Update Grafana**: The metrics will auto-appear with service_name="inventory-service" label
7. **Update AIOps agent prompts**: Mention inventory-service in the system prompt's context

---

### ❓ Q92: What would happen if the OTel Collector goes down?

**Answer:**

1. **Services**: Continue running and serving requests — resilient because OTel SDK buffers data
2. **Metrics**: `BatchSpanProcessor` and `PeriodicExportingMetricReader` will buffer data in memory and retry. Eventually buffer fills and data is lost.
3. **Prometheus**: Stops receiving new metrics → dashboards show "no data" or stale values
4. **Loki**: No new logs ingested
5. **Tempo**: No new traces
6. **AIOps Agent**: Prometheus queries return empty → agent sees "No active request metrics found"

This is why production systems have high availability (multiple OTel Collectors) and alerting on the collector itself.

---

### ❓ Q93: Why does order-service return 502 when payment-service fails, not 500?

**Answer:**

HTTP semantic meaning:
- **500 Internal Server Error**: The server itself has a bug/crash — its own fault
- **502 Bad Gateway**: The server called another service (downstream), and THAT service returned an error — not the calling server's fault

In the code:
```python
if pay_response.status_code >= 400:
    raise HTTPException(status_code=502, detail=f"Payment service error: {pay_response.text}")
```

order-service correctly uses 502 to signal: "I'm fine, but the payment-service I called returned an error." This helps SREs immediately know: "Don't look at order-service's code — look at payment-service."

---

### ❓ Q94: What is the benefit of using `{exporter="loki"}` as the LogQL query?

**Answer:**  
When OTel Collector exports logs to Loki, it automatically adds an `exporter="loki"` label to all log streams.

This means:
- The query reliably fetches **all** application logs regardless of service name
- You don't have to know every service name upfront
- The label is added by the infrastructure (OTel Collector), not the application code

If you need logs from just one service: `{exporter="loki", service_name="payment-service"}`

---

### ❓ Q95: How would you scale this platform for 100 microservices?

**Answer:**

1. **OTel Collector**: Deploy multiple instances with a load balancer in front
2. **Prometheus**: Add remote write to Thanos or Cortex for long-term storage and horizontal scaling
3. **Loki**: Switch from single-binary mode to microservice mode with distributed storage (S3)
4. **Grafana**: Multiple instances behind a load balancer, shared database for config
5. **AIOps Agent**: Convert to a service (not a CLI script), run on a schedule or trigger on alerts
6. **Service Discovery**: Use Kubernetes with Prometheus service discovery instead of static_configs
7. **Alerting**: Add Alertmanager to Prometheus for automatic PagerDuty/Slack alerts

---

### ❓ Q96: Explain the 12-Factor App methodology as applied to this project.

**Answer:**  
The 12-Factor App is a methodology for building scalable, maintainable cloud-native apps. Relevant factors in this project:

| Factor | How this project applies it |
|--------|---------------------------|
| **Config** | Environment variables for URLs, service names (`os.getenv()`) |
| **Processes** | Services are stateless (except in-memory anomaly state — intentional for demo) |
| **Port Binding** | Services expose ports themselves (uvicorn `--port 8000`) |
| **Logs** | Treat logs as event streams (stdout + OTel handler) |
| **Dev/Prod Parity** | Same Docker containers run locally and would run in production |

---

### ❓ Q97: What is the difference between `time.sleep()` (used for latency) and async sleep?

**Answer:**

```python
# BLOCKING - stops the entire thread
time.sleep(2.5)

# NON-BLOCKING - releases control while waiting
await asyncio.sleep(2.5)
```

In this project, `time.sleep()` is used intentionally in async endpoints for latency simulation. This is actually a flaw for a real system — using `time.sleep()` inside an async function blocks the event loop, preventing it from handling other requests during that 2.5 seconds. In production, you'd use `await asyncio.sleep()`. But for demonstration purposes, `time.sleep()` maximizes the visible latency impact.

---

### ❓ Q98: What's the purpose of `nanoseconds` in the Loki query?

**Answer:**

```python
start_ns = int((time.time() - 300) * 1000000000)
```

Loki uses **nanosecond timestamps** (Unix epoch in nanoseconds) for high-precision log timing.

- `time.time()` = seconds since Unix epoch (e.g., 1748823000.123)
- `- 300` = go back 5 minutes
- `* 1_000_000_000` = convert to nanoseconds

Why nanoseconds? Log events can happen milliseconds apart (thousands of logs per second). Microsecond or nanosecond precision avoids timestamp collisions.

---

### ❓ Q99: What would you add to this project to make it production-ready?

**Answer (Top improvements):**

1. **Authentication**: Add API keys or OAuth2 to protect `/anomaly` endpoints
2. **Alerting**: Prometheus Alertmanager → Slack/PagerDuty when error rate > 1% or p95 > 2s
3. **Persistent storage**: Prometheus/Loki data is lost when containers restart — add volume mounts
4. **Health probes**: Add Kubernetes liveness/readiness probes to Dockerfiles
5. **Distributed state**: Replace in-memory `ACTIVE_ANOMALIES` with Redis for multi-instance support
6. **Rate limiting**: Prevent the `/anomaly` endpoint from being abused
7. **Continuous AIOps**: Run diagnosis agent on a cron job (every 5 minutes), not manually
8. **Async anomaly reset**: Replace `time.sleep(latency)` with `asyncio.sleep()` for non-blocking simulation
9. **Secrets management**: Use HashiCorp Vault or AWS Secrets Manager instead of env vars for API keys
10. **CI/CD pipeline**: Automated testing and deployment on code changes

---

### ❓ Q100: If a recruiter asks "explain this project in 2 minutes", what would you say?

**Answer (Pitch):**

> "I built an end-to-end AIOps observability platform that simulates a real microservices environment and uses AI to automatically diagnose production incidents.
>
> The system has two Python FastAPI microservices — an order service and payment service — both fully instrumented with OpenTelemetry, which collects metrics, logs, and distributed traces. These flow through an OTel Collector to Prometheus for metrics, Loki for logs, and Tempo for traces. Grafana visualizes everything in a live dashboard.
>
> To test the system, I built a chaos engineering tool that can inject different types of real production failures — artificial latency, error rates, CPU spikes, and memory leaks — into either service via HTTP endpoints. This lets you see how failures cascade: a latency anomaly in payment-service causes high response times in order-service.
>
> The centerpiece is an AIOps agent that automatically queries Prometheus and Loki, compiles the telemetry into a structured report, and sends it to Google Gemini AI with a carefully crafted SRE system prompt. Gemini analyzes the data and generates a full incident diagnosis with root cause analysis and a remediation plan — like having a senior SRE engineer on-call 24/7.
>
> The whole stack runs locally with a single `docker compose up` command."

---

## 🗂️ Quick Reference: Technology Glossary

| Term | Simple Definition |
|------|------------------|
| **AIOps** | Using AI to automate IT operations tasks |
| **Anomaly** | Something unexpected/abnormal in system behavior |
| **Async** | Code that doesn't wait/block — handles many tasks at once |
| **BatchSpanProcessor** | Collects spans in memory and sends them in groups for efficiency |
| **Cascade failure** | One service's failure causing other services to also fail |
| **Container** | A lightweight, portable package of an application + dependencies |
| **Context Propagation** | Passing trace information between services via HTTP headers |
| **Counter** | A metric that only increases (like a request count) |
| **Docker Compose** | Tool for defining and running multi-container Docker apps |
| **FastAPI** | Modern Python web framework for building REST APIs |
| **Gauge** | A metric that can go up or down (like CPU%) |
| **Gemini** | Google's large language model used for AI diagnosis |
| **gRPC** | High-performance RPC framework using binary Protocol Buffers |
| **Histogram** | A metric tracking distribution of values across buckets |
| **Instrumentation** | Adding code to an application to collect telemetry data |
| **JSON** | Text format for representing structured data |
| **Loki** | Grafana's log aggregation and storage system |
| **Middleware** | Code that runs on every request before/after your handlers |
| **Microservices** | Architecture of small, independent services each doing one job |
| **Observability** | Ability to understand system's internal state from external outputs |
| **OTLP** | OpenTelemetry Protocol — the wire format for sending telemetry |
| **OpenTelemetry** | Open-source standard for collecting telemetry from applications |
| **p95 Latency** | The response time that 95% of requests are faster than |
| **Prometheus** | Open-source time-series database for metrics |
| **PromQL** | Prometheus Query Language for analyzing metric data |
| **Pydantic** | Python library for data validation using type hints |
| **QPS** | Queries Per Second — how many requests per second a service handles |
| **RCA** | Root Cause Analysis — finding the real underlying reason for a problem |
| **RED Metrics** | Rate, Errors, Duration — key metrics for microservices |
| **Resource (OTel)** | Metadata describing the service emitting telemetry (name, version) |
| **REST API** | Architecture for web APIs using HTTP methods (GET, POST, etc.) |
| **Scraping** | Prometheus fetching metrics from a target endpoint |
| **Span** | A single unit of work in distributed tracing |
| **SRE** | Site Reliability Engineering — applying software engineering to ops |
| **Tempo** | Grafana's distributed tracing storage system |
| **Trace** | The complete journey of one request across multiple services |
| **Tracing** | Recording the path of individual requests through a system |
| **uvicorn** | ASGI server that runs FastAPI applications |
| **Virtual Environment** | Isolated Python installation for a specific project |

---

*Guide generated from full project analysis of the AIops-observability-platform.*  
*Project Path: `d:\Projects\AIops-observability-platform`*
