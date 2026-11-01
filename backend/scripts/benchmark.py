"""Run warm CPU latency/RSS benchmark against the local API (no content retained)."""
import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8000/v1/sentiment")
    p.add_argument("--token", default="")
    p.add_argument("--requests", type=int, default=30)
    p.add_argument("--concurrency", type=int, default=1)
    p.add_argument("--text", default="این محصول کیفیت خوبی دارد و من راضی هستم.")
    args = p.parse_args()
    if args.requests < 1 or not (1 <= args.concurrency <= 32):
        p.error("invalid requests or concurrency")
    payload = json.dumps({"text": args.text}, ensure_ascii=False).encode()
    def request(_):
        headers = {"Content-Type": "application/json"}
        if args.token:
            headers["X-API-Key"] = args.token
        req = urllib.request.Request(args.url, data=payload, headers=headers, method="POST")
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.load(resp)
        return round((time.perf_counter() - start) * 1000, 2), result["label"]
    for _ in range(3):
        request(0)
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        points = list(pool.map(request, range(args.requests)))
    times = sorted(p[0] for p in points)
    def pct(q):
        return times[round((len(times) - 1) * q)]
    print(json.dumps({"requests": len(times), "concurrency": args.concurrency, "p50_ms": pct(.5),
                      "p95_ms": pct(.95), "mean_ms": round(statistics.mean(times), 2),
                      "min_ms": min(times), "max_ms": max(times)}, indent=2))

if __name__ == "__main__":
    main()
