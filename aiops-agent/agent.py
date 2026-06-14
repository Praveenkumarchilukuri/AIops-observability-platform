import os
import sys
import time
import argparse
import requests
import pandas as pd
from tabulate import tabulate

# Import prompts
try:
    from prompts import AIOPS_SYSTEM_PROMPT, DIAGNOSTIC_TEMPLATE
except ImportError:
    from .prompts import AIOPS_SYSTEM_PROMPT, DIAGNOSTIC_TEMPLATE

# OpenTelemetry Metrics and Logs targets (inside compose: prometheus:9090, loki:3100)
# From host machine CLI, we use localhost
DEFAULT_PROMETHEUS_URL = "http://localhost:9090"
DEFAULT_LOKI_URL = "http://localhost:3100"

def query_prometheus(url, query):
    endpoint = f"{url}/api/v1/query"
    try:
        response = requests.get(endpoint, params={"query": query}, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("result", [])
            parsed = []
            for r in results:
                metric = r.get("metric", {})
                value = r.get("value", [0, "0"])[1]
                metric["value"] = float(value)
                parsed.append(metric)
            return pd.DataFrame(parsed)
        else:
            # Silent failure helper
            pass
    except Exception:
        pass
    return pd.DataFrame()

def query_loki(url, query, start_ns):
    endpoint = f"{url}/loki/api/v1/query_range"
    params = {
        "query": query,
        "limit": 150,
        "start": str(start_ns)
    }
    try:
        res = requests.get(endpoint, params=params, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            streams = data.get("data", {}).get("result", [])
            logs = []
            for stream in streams:
                labels = stream.get("stream", {})
                svc = labels.get("service_name", "unknown")
                for val in stream.get("values", []):
                    ts = pd.to_datetime(int(val[0]), unit='ns')
                    logs.append({
                        "timestamp": str(ts),
                        "service": svc,
                        "message": val[1].strip()
                    })
            # Sort logs by timestamp ascending
            logs = sorted(logs, key=lambda x: x["timestamp"])
            return logs
    except Exception:
        pass
    return []

def get_telemetry_summary(prom_url):
    """Gathers and formats Prometheus metrics into text summaries."""
    # 1. Active Injected Anomalies
    df_anom = query_prometheus(prom_url, "otel_active_anomalies")
    active_anom = []
    if not df_anom.empty:
        for _, row in df_anom.iterrows():
            if row.get("value", 0.0) > 0.0:
                active_anom.append(f"{row.get('service_name', 'unknown')}: {row.get('anomaly_type', 'unknown')} ({row.get('value')})")
    
    # 2. QPS
    df_qps = query_prometheus(prom_url, "sum(rate(otel_http_requests_total[2m])) by (service_name)")
    qps_summary = []
    if not df_qps.empty:
        for _, row in df_qps.iterrows():
            qps_summary.append({
                "Service": row.get("service_name", "unknown"),
                "QPS (avg 2m)": f"{row.get('value', 0.0):.2f}"
            })
    
    # 3. p95 Latency
    df_lat = query_prometheus(prom_url, "histogram_quantile(0.95, sum(rate(otel_http_request_duration_seconds_bucket[2m])) by (le, service_name))")
    lat_summary = []
    if not df_lat.empty:
        for _, row in df_lat.iterrows():
            lat_summary.append({
                "Service": row.get("service_name", "unknown"),
                "p95 Latency": f"{row.get('value', 0.0):.4f}s"
            })

    # 4. Error Rates
    df_err = query_prometheus(prom_url, "sum(rate(otel_http_requests_total{http_status=~\"5..\"}[2m])) by (service_name) / sum(rate(otel_http_requests_total[2m])) by (service_name) * 100")
    err_summary = []
    if not df_err.empty:
        for _, row in df_err.iterrows():
            err_summary.append({
                "Service": row.get("service_name", "unknown"),
                "Error Rate %": f"{row.get('value', 0.0):.2f}%"
            })
    else:
        # Check if QPS exists (so services are up), error rates are 0
        if qps_summary:
            for s in qps_summary:
                err_summary.append({"Service": s["Service"], "Error Rate %": "0.00%"})

    # 5. System Usage
    df_cpu = query_prometheus(prom_url, "otel_system_cpu_usage")
    df_mem = query_prometheus(prom_url, "otel_system_memory_usage")
    sys_summary = []
    services_seen = set()
    
    if not df_cpu.empty:
        for _, row in df_cpu.iterrows():
            svc = row.get("service_name")
            services_seen.add(svc)
            cpu_val = row.get("value", 0.0)
            mem_val = 0.0
            
            # Find matching memory row
            if not df_mem.empty:
                m_row = df_mem[df_mem["service_name"] == svc]
                if not m_row.empty:
                    mem_val = m_row.iloc[0]["value"]
            
            sys_summary.append({
                "Service": svc,
                "CPU Usage %": f"{cpu_val:.1f}%",
                "Memory Usage %": f"{mem_val:.1f}%"
            })
            
    # Format Tables
    active_anom_str = ", ".join(active_anom) if active_anom else "None"
    
    qps_df = pd.DataFrame(qps_summary)
    lat_df = pd.DataFrame(lat_summary)
    err_df = pd.DataFrame(err_summary)
    sys_df = pd.DataFrame(sys_summary)
    
    metrics_str = f"Active Anomalies (Injected): {active_anom_str}\n\n"
    
    metrics_str += "--- MICROSERVICE RED METRICS ---\n"
    if not qps_df.empty or not lat_df.empty or not err_df.empty:
        # Merge metrics on Service
        merged = pd.DataFrame(columns=["Service"])
        if not qps_df.empty:
            merged = qps_df
        if not lat_df.empty:
            merged = pd.merge(merged, lat_df, on="Service", how="outer")
        if not err_df.empty:
            merged = pd.merge(merged, err_df, on="Service", how="outer")
        merged.fillna("N/A", inplace=True)
        metrics_str += tabulate(merged, headers="keys", tablefmt="grid", showindex=False) + "\n\n"
    else:
        metrics_str += "No active request metrics found.\n\n"
        
    metrics_str += "--- SYSTEM RESOURCE UTILIZATION ---\n"
    if not sys_df.empty:
        metrics_str += tabulate(sys_df, headers="keys", tablefmt="grid", showindex=False) + "\n"
    else:
        metrics_str += "No host metrics found.\n"
        
    return metrics_str

def run_diagnose(prom_url, loki_url):
    """Queries Prometheus and Loki, compiles context, and runs LLM diagnosis."""
    # Print status
    print("[*] Polling Prometheus metrics...")
    metrics_summary = get_telemetry_summary(prom_url)
    
    print("[*] Polling Loki log streams (last 5 minutes)...")
    start_ns = int((time.time() - 300) * 1000000000)
    # Query logs matching exporter="loki" (pushed by otel collector)
    logs = query_loki(loki_url, '{exporter="loki"}', start_ns)
    
    formatted_logs = ""
    if logs:
        for l in logs[-80:]: # Limit to last 80 lines to conserve token context
            formatted_logs += f"[{l['timestamp']}] [{l['service'].upper()}] {l['message']}\n"
    else:
        formatted_logs = "No log records found in Loki for this timeframe.\n"
        
    # Verify Gemini API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n[!] Error: GEMINI_API_KEY environment variable is not set.")
        print("[*] Showing local telemetry table instead:\n")
        print(metrics_summary)
        print("\n--- RECENT LOGS ---")
        print(formatted_logs)
        print("\n[!] To perform full SRE AI diagnosis, run: $env:GEMINI_API_KEY='your-key'; python aiops-agent/agent.py --diagnose")
        return
        
    print("[*] Telemetry context assembled. Contacting Gemini AI for analysis...")
    
    try:
        from google import genai
        from google.genai import types
        
        # Initialize Google GenAI client
        client = genai.Client()
        
        prompt = DIAGNOSTIC_TEMPLATE.format(
            metrics_summary=metrics_summary,
            loki_logs=formatted_logs
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=AIOPS_SYSTEM_PROMPT,
                temperature=0.2
            )
        )
        
        print("\n" + "="*80)
        print(response.text)
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"[x] Error during Gemini AI generating diagnosis: {str(e)}")
        print("\n[*] Raw Telemetry gathered:\n")
        print(metrics_summary)

def main():
    parser = argparse.ArgumentParser(description="AIOps SRE Observability Agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--detect", action="store_true", help="Print local CLI dashboard of current metrics")
    group.add_argument("--diagnose", action="store_true", help="Run full LLM-based root-cause analysis")
    
    parser.add_argument("--prometheus-url", type=str, default=DEFAULT_PROMETHEUS_URL, help="Prometheus host endpoint")
    parser.add_argument("--loki-url", type=str, default=DEFAULT_LOKI_URL, help="Loki host endpoint")
    
    args = parser.parse_args()
    
    if args.detect:
        print("\n" + "="*60)
        print("AIOps TELEMETRY DETECTION CONTROL")
        print("="*60 + "\n")
        summary = get_telemetry_summary(args.prometheus_url)
        print(summary)
        print("="*60 + "\n")
    elif args.diagnose:
        run_diagnose(args.prometheus_url, args.loki_url)

if __name__ == "__main__":
    main()
