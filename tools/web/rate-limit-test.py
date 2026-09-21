#!/usr/bin/env python3
"""Rate limit detection. Usage: python3 rate-limit-test.py https://target.com/login [--burst 20]"""
import sys, urllib.request, ssl, time
URL = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: rate-limit-test.py https://target.com/endpoint [--burst 20]")
BURST = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--burst" else 20
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = False
results = {"429":0,"200":0,"403":0,"other":0,"min_ms":999,"max_ms":0}
times = []
print(f"Bursting {BURST} requests to {URL}...\n")
for i in range(BURST):
    try:
        start = time.time()
        req = urllib.request.Request(URL, headers={"User-Agent":f"Mozilla/5.0-{i}"})
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        ms = int((time.time()-start)*1000)
        times.append(ms)
        results[str(resp.status)] = results.get(str(resp.status),0)+1
        results["min_ms"] = min(results["min_ms"],ms)
        results["max_ms"] = max(results["max_ms"],ms)
        code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code; results[str(code)] = results.get(str(code),0)+1
    except Exception as e:
        code = f"ERR"; results["other"] += 1
    if code == 429 or code == 503: print(f"  [{i+1}/{BURST}] {code} — RATE LIMITED at request {i+1}"); break
    if i % 5 == 0: print(f"  [{i+1}/{BURST}] {code}")
    if i < BURST-1: time.sleep(0.1)
avg_ms = sum(times)//len(times) if times else 0
print(f"\nResults: 200={results['200']} 429={results['429']} 403={results['403']} avg={avg_ms}ms min={results['min_ms']}ms max={results['max_ms']}ms")
print("VERDICT: Rate limit DETECTED" if results["429"] > 0 else "VERDICT: No rate limit detected (all requests accepted)")
