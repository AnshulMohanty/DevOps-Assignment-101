"""orders-api: a small service instrumented for all three pillars of observability.

Metrics : Prometheus format on /metrics (request count, latency histogram, in-flight requests)
Traces  : OpenTelemetry spans exported over OTLP to Jaeger (one span per request + child spans)
Logs    : one JSON line per request on stdout, carrying the trace_id of the request

Behaviour is tunable with env vars so problems can be injected on purpose:
  ERROR_RATE   fraction of /api/orders requests that fail with HTTP 500   (default 0.03)
  SLOW_RATE    fraction of requests that hit a slow "database" query       (default 0.05)
"""
import json
import logging
import os
import random
import sys
import time

from flask import Flask, Response, g, jsonify, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

SERVICE = "orders-api"
VERSION = os.environ.get("APP_VERSION", "1.0.0")
ERROR_RATE = float(os.environ.get("ERROR_RATE", "0.03"))
SLOW_RATE = float(os.environ.get("SLOW_RATE", "0.05"))

# ---------------------------------------------------------------- traces
provider = TracerProvider(resource=Resource.create({"service.name": SERVICE, "service.version": VERSION}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://jaeger:4318/v1/traces"))))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(SERVICE)

# ---------------------------------------------------------------- metrics
REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["route"],
                    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5))
IN_FLIGHT = Gauge("http_requests_in_flight", "Requests being served right now")
APP_INFO = Gauge("app_info", "Static information about the running app", ["version"])
APP_INFO.labels(version=VERSION).set(1)

# ---------------------------------------------------------------- logs
log = logging.getLogger(SERVICE)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger("werkzeug").setLevel(logging.WARNING)  # no plain-text access log; ours is JSON


def log_json(level, message, **fields):
    span = trace.get_current_span().get_span_context()
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "level": level,
              "service": SERVICE, "msg": message}
    if span.is_valid:
        record["trace_id"] = format(span.trace_id, "032x")
    record.update(fields)
    log.info(json.dumps(record))


app = Flask(__name__)
FlaskInstrumentor().instrument_app(app, excluded_urls="metrics,health")


@app.before_request
def start_timer():
    g.start = time.perf_counter()
    IN_FLIGHT.inc()


@app.after_request
def record(response):
    IN_FLIGHT.dec()
    if request.path in ("/metrics",):
        return response
    route = request.url_rule.rule if request.url_rule else "unmatched"
    elapsed = time.perf_counter() - g.start
    REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    LATENCY.labels(route).observe(elapsed)
    if route != "/health":
        level = "error" if response.status_code >= 500 else "info"
        log_json(level, "request", method=request.method, route=route,
                 status=response.status_code, duration_ms=round(elapsed * 1000, 1))
    return response


def query_database(customer):
    # child span: shows up nested under the request span in Jaeger
    with tracer.start_as_current_span("db.query orders") as span:
        slow = random.random() < SLOW_RATE
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", "SELECT * FROM orders WHERE customer_id = $1")
        span.set_attribute("customer.id", customer)
        span.set_attribute("db.slow", slow)
        time.sleep(random.uniform(0.8, 1.6) if slow else random.uniform(0.01, 0.08))
        return random.randint(0, 5)


def price_orders(count):
    with tracer.start_as_current_span("pricing.calculate") as span:
        span.set_attribute("orders.count", count)
        time.sleep(random.uniform(0.002, 0.02))
        return round(count * random.uniform(100, 900), 2)


@app.route("/api/orders")
def orders():
    customer = request.args.get("customer", f"c-{random.randint(100, 120)}")
    count = query_database(customer)
    if random.random() < ERROR_RATE:
        trace.get_current_span().set_status(trace.Status(trace.StatusCode.ERROR, "payment service timeout"))
        return jsonify(error="payment service timeout"), 500
    return jsonify(customer=customer, orders=count, total=price_orders(count))


@app.route("/health")
def health():
    return jsonify(status="ok", service=SERVICE, version=VERSION)


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)  # nosec B104 - container
