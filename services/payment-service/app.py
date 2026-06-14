import os
import time
import random
import logging
import threading
import gc
import psutil
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

from opentelemetry.propagate import extract

# ----------------- Configuration & Initialization -----------------
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "payment-service")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")

# Define Resource
resource = Resource.create({"service.name": SERVICE_NAME, "service.version": "1.0.0"})

# 1. Initialize Tracing
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)
span_exporter = OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")
tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
tracer = trace.get_tracer(SERVICE_NAME)

# 2. Initialize Metrics
metric_exporter = OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT}/v1/metrics")
reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(SERVICE_NAME)

# 3. Initialize Logs
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
log_exporter = OTLPLogExporter(endpoint=f"{OTEL_ENDPOINT}/v1/logs")
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

# Attach OTel Log handler to python logger
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
# Set formatter to see logs in console as well
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)
logging.getLogger().setLevel(logging.INFO)

app = FastAPI(title="Payment Service")

# ----------------- Telemetry Metrics Definitions -----------------
http_requests_counter = meter.create_counter(
    "http_requests_total",
    description="Total number of HTTP requests processed",
    unit="1"
)

http_request_duration_histogram = meter.create_histogram(
    "http_request_duration_seconds",
    description="Duration of HTTP requests in seconds",
    unit="s"
)

# Active anomalies and utilization state
ACTIVE_ANOMALIES = {
    "latency": 0.0,
    "error_rate": 0.0,
    "cpu_spike": 0.0,
    "memory_leak": 0.0
}

def get_cpu_usage(options):
    yield metrics.Observation(psutil.cpu_percent(), {"service_name": SERVICE_NAME})

def get_mem_usage(options):
    yield metrics.Observation(psutil.virtual_memory().percent, {"service_name": SERVICE_NAME})

def get_active_anomalies(options):
    for name, val in ACTIVE_ANOMALIES.items():
        yield metrics.Observation(val, {"service_name": SERVICE_NAME, "anomaly_type": name})

meter.create_observable_gauge("system_cpu_usage", callbacks=[get_cpu_usage], description="CPU usage percent")
meter.create_observable_gauge("system_memory_usage", callbacks=[get_mem_usage], description="Memory usage percent")
meter.create_observable_gauge("active_anomalies", callbacks=[get_active_anomalies], description="Active anomalies")

# ----------------- Middleware for Telemetry -----------------
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    method = request.method
    
    # Don't track metric/health endpoints in statistics to avoid spam
    skip_telemetry = path in ["/health", "/metrics", "/anomaly"]
    
    if skip_telemetry:
        return await call_next(request)
        
    context = extract(request.headers)
    with tracer.start_as_current_span(
        f"{method} {path}", 
        context=context, 
        kind=trace.SpanKind.SERVER
    ) as span:
        span.set_attribute("http.method", method)
        span.set_attribute("http.target", path)
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            span.set_attribute("http.status_code", response.status_code)
        except Exception as e:
            status_code = "500"
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            logging.error(f"Request failed: {method} {path} - Error: {str(e)}")
            raise e
        finally:
            duration = time.time() - start_time
            attributes = {
                "service_name": SERVICE_NAME,
                "method": method,
                "http_status": status_code,
                "path": path
            }
            http_requests_counter.add(1, attributes)
            http_request_duration_histogram.record(duration, attributes)
            
            log_level = logging.INFO if int(status_code) < 400 else logging.ERROR
            logging.log(log_level, f"Processed request: {method} {path} - {status_code} in {duration:.4f}s")
            
    return response

# ----------------- Anomaly Threads & Tasks -----------------
cpu_threads = []
cpu_threads_running = False

def cpu_heavy_loop():
    global cpu_threads_running
    logging.info("Starting CPU spike thread loop...")
    while cpu_threads_running:
        # High CPU calculations with minor sleep to avoid locks
        _ = [x*x for x in range(5000)]
        time.sleep(0.001)
    logging.info("Stopped CPU spike thread loop.")

memory_leak_store = []
memory_leak_running = False

def memory_leak_worker():
    global memory_leak_running, memory_leak_store
    logging.info("Starting memory leak background simulation...")
    while memory_leak_running:
        # Append about 10MB of structured data
        large_chunk = "X" * (10 * 1024 * 1024)
        memory_leak_store.append(large_chunk)
        logging.warning(f"Memory leak active: Added 10MB. Total chunks: {len(memory_leak_store)}. Approx heap: {len(memory_leak_store)*10}MB")
        time.sleep(2)

# ----------------- Endpoints & Models -----------------
class AnomalyRequest(BaseModel):
    anomaly_type: str  # latency, error_rate, cpu_spike, memory_leak
    value: float       # latency in sec, error_rate in ratio (0-1), cpu_spike on/off (1/0), memory_leak on/off (1/0)

class PayRequest(BaseModel):
    order_id: str
    amount: float

@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME}

@app.post("/pay")
async def pay(payload: PayRequest):
    logging.info(f"Received payment request for order: {payload.order_id}, amount: {payload.amount}")
    
    # 1. Check Latency Anomaly
    latency = ACTIVE_ANOMALIES["latency"]
    if latency > 0:
        logging.warning(f"Injecting latency anomaly: sleeping {latency} seconds")
        time.sleep(latency)
        
    # 2. Check Error Rate Anomaly
    error_rate = ACTIVE_ANOMALIES["error_rate"]
    if error_rate > 0:
        if random.random() < error_rate:
            logging.error(f"Injecting error anomaly: random payment failure (rate: {error_rate})")
            raise HTTPException(status_code=500, detail="Database transaction validation failure: timeout")
            
    # Success path
    return {
        "status": "approved",
        "transaction_id": f"tx_{random.randint(100000, 999999)}",
        "timestamp": time.time()
    }

@app.post("/anomaly")
async def trigger_anomaly(payload: AnomalyRequest):
    global cpu_threads_running, cpu_threads, memory_leak_running, memory_leak_store
    
    a_type = payload.anomaly_type
    val = payload.value
    
    if a_type not in ACTIVE_ANOMALIES:
        raise HTTPException(status_code=400, detail="Invalid anomaly type")
        
    ACTIVE_ANOMALIES[a_type] = val
    logging.warning(f"Anomaly updated: {a_type} set to {val}")
    
    # CPU Spike Handler
    if a_type == "cpu_spike":
        if val > 0 and not cpu_threads_running:
            cpu_threads_running = True
            # Spawn threads to consume multiple cores
            cpu_threads = []
            for _ in range(4):
                t = threading.Thread(target=cpu_heavy_loop, daemon=True)
                t.start()
                cpu_threads.append(t)
            logging.warning("CPU spike active (4 threads running busy loops)")
        elif val == 0 and cpu_threads_running:
            cpu_threads_running = False
            for t in cpu_threads:
                t.join(timeout=1.0)
            cpu_threads = []
            logging.warning("CPU spike deactivated")
            
    # Memory Leak Handler
    if a_type == "memory_leak":
        if val > 0 and not memory_leak_running:
            memory_leak_running = True
            t = threading.Thread(target=memory_leak_worker, daemon=True)
            t.start()
            logging.warning("Memory leak active (adding 10MB every 2s)")
        elif val == 0 and memory_leak_running:
            memory_leak_running = False
            memory_leak_store = []
            gc.collect()
            logging.warning("Memory leak deactivated and garbage collected")
            
    return {"status": "success", "active_anomalies": ACTIVE_ANOMALIES}
