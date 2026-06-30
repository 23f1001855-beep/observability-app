import time
import uuid
import json
from collections import deque
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

# 1. Remember when we started (for uptime)
START_TIME = time.time()

# 2. The Prometheus counter — this is what /metrics will expose
REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total number of HTTP requests received",
    ["path", "method"]
)

# 3. In-memory log buffer (keeps only the last 1000 entries)
LOG_BUFFER = deque(maxlen=1000)

def write_log(level: str, path: str, request_id: str, extra: dict = None):
    entry = {
        "level": level,
        "ts": time.time(),
        "path": path,
        "request_id": request_id,
    }
    if extra:
        entry.update(extra)
    LOG_BUFFER.append(entry)
    print(json.dumps(entry))  # also print as structured JSON to stdout

# 4. Middleware — runs for EVERY request, on every endpoint
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    path = request.url.path

    # increment the counter no matter which endpoint was hit
    REQUEST_COUNTER.labels(path=path, method=request.method).inc()

    response = await call_next(request)

    write_log("INFO", path, request_id, {"status_code": response.status_code})
    return response

# ---- Endpoint: /work ----
@app.get("/work")
def work(n: int = 1):
    total = 0
    for i in range(n):
        total += i  # simulate doing "work"
    return {"email": "youremail@example.com", "done": n}

# ---- Endpoint: /metrics ----
@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ---- Endpoint: /healthz ----
@app.get("/healthz")
def healthz():
    uptime = time.time() - START_TIME
    return {"status": "ok", "uptime_s": uptime}

# ---- Endpoint: /logs/tail ----
@app.get("/logs/tail")
def logs_tail(limit: int = 50):
    logs = list(LOG_BUFFER)[-limit:]
    return JSONResponse(content=logs)