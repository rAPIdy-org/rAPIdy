wrk.method = "POST"
wrk.body = io.open("benchmarks/common/payload.json"):read("*a")
wrk.headers["Content-Type"] = "application/json"

done = function(summary, latency, requests)
    io.write(string.format(
        '\nBENCH_JSON {"rps": %.2f, "p50_ms": %.3f, "p95_ms": %.3f, "p99_ms": %.3f, "req2xx": %d, "non2xx": %d}\n',
        summary.requests / (summary.duration / 1e6),
        latency:percentile(50) / 1000,
        latency:percentile(95) / 1000,
        latency:percentile(99) / 1000,
        summary.requests - summary.errors.status,
        summary.errors.status))
end
