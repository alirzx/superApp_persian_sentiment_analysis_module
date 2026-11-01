# CPU benchmark and Persian evaluation plan

## Executed here

`PYTHONPATH=backend pytest backend/tests -q`: deterministic tests with **fake engine** covering API/auth/health, routing, batch, combined analysis, Persian normalization, class score mapping, artifact hash integrity. Tests do not download models and must not be represented as real-model benchmark results.

## Required model E2E on network-enabled CPU host

1. `make model` and `make model-verify` succeed for **both models**.
2. Verify immutable HF commit IDs, original `.bin` files and license provenance; keep hash inventory.
3. Inspect exported ONNX input/output names and numerical parity test tolerance, batch sizes 1 and 2, sequence sizes 16,128,256.
4. Execute real requests for all endpoints through API and through UI reverse proxy.
5. Check three-class sentiment and eight-class topic labels against upstream config and a manually labeled corpus.
6. Benchmark 30+ warmed examples under concurrency 1,2,4 with recorded CPU model, ISA, RAM, base system load, thread count, process RSS, P50/P95, requests/sec, and error rate.
7. Verify `503` when inference capacity is overloaded, `413` on request limits, `401` on wrong tokens, and failing `ready` on a corrupted manifest.
8. Verify offline cold restart, detached/reconnected volume, failure recovery, and no runtime network downloads.
9. Evaluate reviews (Digikala/food), informal Persian, news, negation, sarcasm, mixed sentiment, noisy OCR/STT, Persian digits, ZWNJ, and short versus long inputs.
10. Measure macro-F1 and per-class precision/recall, confusion matrix, confidence calibration and domain drift. Decide whether a calibrated abstain/unknown class is needed; do not manufacture it by relabeling neutral scores.

### Quick latency check

```bash
python -m backend.scripts.benchmark --url http://127.0.0.1:8001/v1/sentiment --requests 30 --concurrency 1
python -m backend.scripts.benchmark --url http://127.0.0.1:8001/v1/topics --requests 30 --concurrency 2
```

For production set `--token` securely without placing secrets into shared shell history. Benchmark text defaults are synthetic sample sentences. Container-level memory statistics: `docker stats` plus system metrics. Only declare CPU latency/memory SLA after measuring target server hardware.
