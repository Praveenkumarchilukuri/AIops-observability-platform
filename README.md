# AIOps Observability & Diagnostic Platform

A premium microservice observability platform configured with **OpenTelemetry**, **Prometheus**, **Loki**, **Tempo**, and a **Gemini-powered AIOps CLI agent** to inject system anomalies (CPU spikes, memory leaks, latency, error rates) and diagnose the root cause.

---

## 🛠️ Port Bindings & Endpoints

| Component | Host Port | In-Network Address | Purpose |
|---|---|---|---|
| **order-service** | `http://localhost:8000` | `order-service:8000` | Front-end order REST API |
| **payment-service** | `http://localhost:8001` | `payment-service:8001` | Downstream payments REST API |
| **Grafana** | `http://localhost:3000` | `grafana:3000` | Visual Dashboards (Creds: `admin` / `admin`) |
| **Prometheus** | `http://localhost:9090` | `prometheus:9090` | Metrics DB |
| **Loki** | `http://localhost:3100` | `loki:3100` | Log Aggregator DB |
| **Tempo** | `http://localhost:3200` | `tempo:3200` | Distributed Trace DB |
| **OTel Collector** | `4317` (gRPC), `4318` (HTTP) | `otel-collector:*` | Telemetry Receiver |

---

## 🚀 Getting Started

### 1. Prerequisites
Make sure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your machine and python 3.9+ with virtual environments.

### 2. Boot up the Observability Stack
Start the entire infrastructure using Docker Compose:
```bash
docker compose up --build -d
```
This builds the microservices, sets up networks, and initializes Loki, Prometheus, Tempo, and Grafana.

### 3. Verify Container Status
Ensure all containers are running:
```bash
docker compose ps
```

---

## 🚦 Phase 1: Run Traffic & Inject Anomalies

The platform contains a helper script to simulate transaction traffic and trigger system degradation.

### Set up local requirements
Before executing the script on your host machine, install python requirements:
```bash
# In the root workspace
pip install -r services/order-service/requirements.txt
pip install -r aiops-agent/requirements.txt
```

### A. Run background transaction traffic (No anomalies)
To simulate continuous customer requests (adds rate, latency metrics):
```bash
python anomaly-injector/inject_anomalies.py --traffic-only
```

### B. Inject Latency Anomaly
Slows down payment transactions, cascading slow response rates up to the order-service.
```bash
# Inject 2.5 second delay in payment-service for 45 seconds
python anomaly-injector/inject_anomalies.py --anomaly latency --service payment-service --value 2.5 --duration 45
```

### C. Inject Error Rate Anomaly
Generates database connection exceptions inside payment-service, inducing HTTP 502/503 errors in order-service.
```bash
# Inject 40% error failure rate in payment-service for 30 seconds
python anomaly-injector/inject_anomalies.py --anomaly error_rate --service payment-service --value 0.4 --duration 30
```

### D. Inject CPU Spike Anomaly
Forces order-service to consume 100% of available CPU cores.
```bash
# Inject CPU spike on order-service for 40 seconds
python anomaly-injector/inject_anomalies.py --anomaly cpu_spike --service order-service --value 1.0 --duration 40
```

### E. Inject Memory Leak Anomaly
Slowly leaks 10MB memory blocks in payment-service.
```bash
# Inject memory leak on payment-service for 60 seconds
python anomaly-injector/inject_anomalies.py --anomaly memory_leak --service payment-service --value 1.0 --duration 60
```

*Note: The script has a built-in clean-up mechanism. Pressing `Ctrl+C` at any point will automatically reset all anomalies back to normal on both services.*

---

## 🧠 Phase 2: Run the AIOps Diagnosis Agent

The AIOps agent polls Prometheus metrics and Loki logs to inspect system status and run root-cause analysis (RCA) using Google Gemini.

### A. Local Detection Dashboard
Inspect the current status of QPS, p95 Latency, error rates, and system resources from the terminal:
```bash
python aiops-agent/agent.py --detect
```

### B. Full SRE AI Diagnosis
Analyze the telemetry logs and metrics, isolate the cascading failure path, and generate a remediation plan using Gemini:

First, export your Gemini API key:
```powershell
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# Windows CMD
set GEMINI_API_KEY="your-gemini-api-key-here"
```

Then run the diagnostic command:
```bash
python aiops-agent/agent.py --diagnose
```

This retrieves logs and metrics, structures them, queries Gemini, and outputs a complete, actionable incident analysis report.

---

## 📊 Phase 3: Visualize on Grafana

1. Open your browser and navigate to `http://localhost:3000`.
2. Login with username `admin` and password `admin`.
3. Open **Dashboards** and click on **AIOps Observability Control Center**.
4. You will see a beautiful visualization of:
   * Active Injected Anomalies (highlighted in red)
   * System CPU and Memory utilization trends
   * Request Rates (QPS)
   * p95 Latency charts
   * 5xx Error rates
   * Application Log Streams aggregated by Loki
