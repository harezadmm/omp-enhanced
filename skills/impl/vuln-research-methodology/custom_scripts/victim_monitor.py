import requests
import time
from datetime import datetime
import urllib3

urllib3.disable_warnings()

# Configuration
ELASTICSEARCH_IP = "127.0.0.1"
AUTH = ("username", "password")
URL = f"http://{ELASTICSEARCH_IP}:9200/_search?size=0"

# Thresholds & Timing
LATENCY_WARNING = 2.0
LATENCY_CRITICAL = 5.0
MAX_WAIT = 15.0
SLEEP_INTERVAL = 1.0  # Time in seconds between requests

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

print(f"[*] Monitoring Elasticsearch Search Thread Responsiveness on {ELASTICSEARCH_IP}...")
print(f"[!] Target: _search?size=0 | Measuring cluster metadata response with zero document overhead.")
print(f"[*] Max Wait: {MAX_WAIT}s | Interval: {SLEEP_INTERVAL}s")
print(f"[*] Warning: {LATENCY_WARNING}s | Critical: {LATENCY_CRITICAL}s\n")

while True:
    try:
        start = time.time()
        r = requests.get(URL, auth=AUTH, verify=False, timeout=MAX_WAIT)
        elapsed = time.time() - start

        # Logic Priority: 
        if elapsed >= LATENCY_CRITICAL:
            color_code = "\033[91m" # Red Text
            status_text = "DEGRADED "
        elif r.status_code == 429:
            color_code = "\033[93m" # Yellow Text
            status_text = "RATELIMIT" 
        elif elapsed >= LATENCY_WARNING:
            color_code = "\033[93m" # Yellow Text
            status_text = "LAGGING  " 
        else:
            color_code = "\033[92m" # Green Text
            status_text = "HEALTHY  "

        log(f"Status: {r.status_code} {color_code}{status_text}\033[0m | Latency: {elapsed:.3f}s")

    except requests.exceptions.ReadTimeout:
        log("\033[1;31m[!] TIMEOUT\033[0m  | No response after " + f"{MAX_WAIT}s")
    except requests.exceptions.ConnectionError:
        log("\033[1;35m[!] DOWN\033[0m     | Connection Refused/Reset")
    except KeyboardInterrupt:
        print("\n[*] Stopping monitor.")
        break
    except Exception as e:
        log(f"[!] Error: {e}")

    # Use the customized variable here
    time.sleep(SLEEP_INTERVAL)
