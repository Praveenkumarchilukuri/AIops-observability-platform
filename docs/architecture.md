# System Architecture: AIOps Observability Platform

This document describes the technical architecture, data flows, and design principles of the microservice-based AIOps Observability Platform.

---

## 1. Component Overview

The platform consists of seven distinct services running inside a dedicated Docker bridge network (`observability-network`):

1. **`order-service`**: An entrypoint FastAPI service simulating a standard order processing endpoint.
2. **`payment-service`**: A downstream FastAPI service simulating transaction validation and bank routing.
3. **`otel-collector`**: The OpenTelemetry Collector Contrib node receiving gRPC and HTTP telemetry traces, metrics, and logs.
4. **`prometheus`**: Scrapes consolidated metrics from the OTel Collector.
5. **`loki`**: Aggregates container logging streams pushed by the OTel Collector.
6. **`tempo`**: Aggregates trace boundaries pushed by the OTel Collector, providing distributed trace viewing inside Grafana.
7. **`grafana`**: Consolidates Prometheus, Loki, and Tempo dashboards for centralized visual representation.
8. **AIOps Agent & Anomaly Injector**: External CLI tooling interacting with host-exposed ports.

---

## 2. Distributed Tracing and Telemetry Flow

The microservices are manually instrumented using the OpenTelemetry Python SDK. This provides complete control over metric namespaces and transaction boundaries.

### Context Propagation Flow
When a client sends a request to `order-service` `/order`:
1. `order-service` creates a Server Span representing the entry trace.
2. The service creates an HTTP headers dictionary.
3. The OTel propagators inject the active trace context (consisting of the `traceparent` header) into the headers dict.
4. `order-service` makes a downstream async HTTP call using `httpx` to `payment-service` `/pay`, passing the headers.
5. `payment-service`'s middleware intercepts the request, extracts the headers, and starts a Server Span bound to the parent trace.
6. The OTel Collector receives all spans, formatting and passing them directly to **Grafana Tempo**.

```
[Traffic Injector]
       │ (HTTP POST /order)
       ▼
┌──────────────────┐
│  order-service   │ (Start trace context)
│  (port 8000)     │
└────────┬─────────┘
         │ (HTTP POST /pay + traceparent header)
         ▼
┌──────────────────┐
│ payment-service  │ (Extract trace context, link spans)
│  (port 8001)     │
└──────────────────┘
```

---

## 3. Metrics Schema

To guarantee seamless dashboard visualization and robust PromQL queries for the AIOps agent, the microservices expose exact, structured metrics under the `otel_` namespace:

| Metric Name | Type | Label Dimensions | Description |
|---|---|---|---|
| `otel_http_requests_total` | Counter | `service_name`, `method`, `http_status`, `path` | Total processed HTTP requests |
| `otel_http_request_duration_seconds` | Histogram | `service_name`, `method`, `http_status`, `path` | Request execution latency |
| `otel_system_cpu_usage` | Gauge | `service_name` | System CPU utilization percentage |
| `otel_system_memory_usage` | Gauge | `service_name` | System memory allocation percentage |
| `otel_active_anomalies` | Gauge | `service_name`, `anomaly_type` | Binary state of injected anomaly (1 = active, 0 = inactive) |

---

## 4. Anomaly Simulation Mechanics

Service-level anomalies are triggered dynamically by writing state values to the `/anomaly` endpoint of the target service. The service executes the following code patterns depending on the type:

* **Latency Anomaly**: Inserts a block using `time.sleep(value)` inside the request routing thread.
* **Error Rate Anomaly**: Intercepts request routes and returns `HTTPException(500)` if a random float is below the target error rate limit.
* **CPU Spike Anomaly**: Spawns 4 background daemon threads running a math intensive busy loop (`_ = [x*x for x in range(5000)]`) to load CPU cores.
* **Memory Leak Anomaly**: Spawns a background thread appending large string buffers (10MB blocks) to a global list. Clearing the anomaly resets the list and runs `gc.collect()`.

---

## 5. AIOps LLM Incident Investigation Loop

The **AIOps Agent** executes a diagnostic loop to investigate system anomalies:

1. **Poll Prometheus**: Queries Prometheus HTTP API (`/api/v1/query`) for current average CPU usage, RAM usage, request volume (QPS), p95 latency, and HTTP 5xx error rates.
2. **Poll Loki**: Queries Loki API (`/loki/api/v1/query_range`) for logs containing warnings or errors from both services.
3. **Assemble Context**: Formats the metrics as clean ASCII text tables (using Pandas/Tabulate) and compiles logs in chronological order.
4. **LLM Evaluation**: Submits the combined context to Google Gemini with a rigorous system prompt instructing the model to correlate data points (e.g. downstream latency causing gateway errors) and construct a structured Incident Diagnosis Report (Summary, Telemetry, Cause & Effect, Root Cause, Mitigation).
