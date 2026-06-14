import time
import random
import requests
import argparse
import threading
import sys

# Default Service URLs (from host machine perspective)
ORDER_SERVICE_URL = "http://localhost:8000"
PAYMENT_SERVICE_URL = "http://localhost:8001"

traffic_running = True
total_requests = 0
successful_requests = 0
failed_requests = 0

ITEMS = [
    {"item": "Laptop Pro", "price": 1299.99},
    {"item": "Wireless Mouse", "price": 49.99},
    {"item": "4K Monitor 27-inch", "price": 349.99},
    {"item": "Mechanical Keyboard", "price": 119.99},
    {"item": "USB-C Hub", "price": 29.99}
]

def run_traffic_simulator(qps=2):
    global total_requests, successful_requests, failed_requests, traffic_running
    print(f"[*] Starting background traffic simulation at ~{qps} QPS...")
    
    while traffic_running:
        item = random.choice(ITEMS)
        payload = {
            "item": item["item"],
            "quantity": random.randint(1, 3),
            "price": item["price"]
        }
        
        total_requests += 1
        try:
            # Send order request
            response = requests.post(f"{ORDER_SERVICE_URL}/order", json=payload, timeout=8.0)
            if response.status_code == 200:
                successful_requests += 1
            else:
                failed_requests += 1
                # print(f"[!] Order failed with status {response.status_code}: {response.text[:100]}")
        except Exception as e:
            failed_requests += 1
            # print(f"[!] Order failed with error: {str(e)}")
            
        time.sleep(1.0 / qps)

def update_anomaly(service_url, anomaly_type, value):
    """Sends a request to the target service to set an anomaly value."""
    url = f"{service_url}/anomaly"
    payload = {
        "anomaly_type": anomaly_type,
        "value": value
    }
    try:
        res = requests.post(url, json=payload, timeout=5.0)
        if res.status_code == 200:
            print(f"[+] Successfully updated anomaly '{anomaly_type}' to {value} on {service_url}")
            return True
        else:
            print(f"[x] Failed to update anomaly on {service_url}: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"[x] Error reaching service at {url}: {str(e)}")
        return False

def reset_all_anomalies():
    """Resets all anomalies to 0 on both services."""
    print("\n[*] Resetting all anomalies to normal status on all services...")
    for service_url in [ORDER_SERVICE_URL, PAYMENT_SERVICE_URL]:
        for anomaly in ["latency", "error_rate", "cpu_spike", "memory_leak"]:
            update_anomaly(service_url, anomaly, 0.0)
    print("[+] System reset complete.")

def main():
    global traffic_running
    parser = argparse.ArgumentParser(description="Traffic Simulator & Anomaly Injector for AIOps Platform")
    
    parser.add_argument("--qps", type=float, default=2.0, help="Queries per second for background traffic")
    parser.add_argument("--anomaly", type=str, choices=["latency", "error_rate", "cpu_spike", "memory_leak"], help="Anomaly to inject")
    parser.add_argument("--service", type=str, choices=["order-service", "payment-service"], help="Target service for the anomaly")
    parser.add_argument("--value", type=float, default=0.0, help="Value for anomaly (e.g. latency in seconds, error rate 0.0-1.0, 1.0 to enable CPU/Memory anomalies)")
    parser.add_argument("--duration", type=int, default=30, help="Duration of anomaly injection in seconds")
    parser.add_argument("--traffic-only", action="store_true", help="Only run background traffic simulator, do not inject anomalies")
    
    args = parser.parse_args()
    
    # Ensure variables align if injecting anomaly
    if not args.traffic_only and args.anomaly:
        if not args.service:
            print("[x] Error: Must specify --service when injecting an anomaly.")
            sys.exit(1)
        if args.value == 0.0:
            print("[x] Error: Must specify a non-zero --value to inject an anomaly.")
            sys.exit(1)

    # Start traffic thread
    traffic_thread = threading.Thread(target=run_traffic_simulator, args=(args.qps,), daemon=True)
    traffic_thread.start()
    
    # If traffic only, run indefinitely
    if args.traffic_only:
        print("[*] Traffic simulator running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
                print(f"    [Status] Total requests: {total_requests} | Success: {successful_requests} | Failed: {failed_requests}", end="\r")
        except KeyboardInterrupt:
            print("\n[-] Exiting traffic simulator.")
            traffic_running = False
            sys.exit(0)

    # Injecting Anomaly Flow
    target_service_url = ORDER_SERVICE_URL if args.service == "order-service" else PAYMENT_SERVICE_URL
    
    print("\n" + "="*60)
    print(f"ANOMALY INJECTION STAGE")
    print(f"Injecting: {args.anomaly.upper()}")
    print(f"Service:   {args.service} ({target_service_url})")
    print(f"Value:     {args.value}")
    print(f"Duration:  {args.duration} seconds")
    print("="*60 + "\n")
    
    try:
        # Trigger the anomaly
        success = update_anomaly(target_service_url, args.anomaly, args.value)
        if not success:
            print("[x] Failed to inject anomaly. Exiting.")
            sys.exit(1)
            
        print(f"\n[*] Keeping anomaly active for {args.duration} seconds...")
        for remaining in range(args.duration, 0, -1):
            sys.stdout.write(f"\r    Time remaining: {remaining}s | Requests: {total_requests} | Success: {successful_requests} | Failed: {failed_requests}")
            sys.stdout.flush()
            time.sleep(1)
            
        print("\n\n[*] Injection window completed.")
        
    except KeyboardInterrupt:
        print("\n\n[!] Script execution interrupted by user!")
    finally:
        # Clean up and reset anomalies
        reset_all_anomalies()
        traffic_running = False
        print(f"\n[Final Run Stats] Total requests: {total_requests} | Success: {successful_requests} | Failed: {failed_requests}\n")

if __name__ == "__main__":
    main()
