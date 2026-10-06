"""A small HTTP API around the calculator so the app can run as a container.

GET /health                 -> {"status": "ok", "version": ...}
GET /<operation>?a=..&b=..  -> {"operation": ..., "a": ..., "b": ..., "result": ...}
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from app.calculator import add, divide, multiply, power, subtract

OPERATIONS = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
    "power": power,
}
VERSION = os.environ.get("APP_VERSION", "dev")


class CalculatorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            return self._send(200, {"status": "ok", "version": VERSION})

        operation = url.path.strip("/")
        if operation not in OPERATIONS:
            return self._send(404, {"error": f"unknown operation '{operation}'",
                                    "operations": sorted(OPERATIONS)})
        query = parse_qs(url.query)
        try:
            a, b = float(query["a"][0]), float(query["b"][0])
            result = OPERATIONS[operation](a, b)
        except KeyError:
            return self._send(400, {"error": "both a and b are required"})
        except ValueError as e:
            return self._send(400, {"error": str(e)})
        return self._send(200, {"operation": operation, "a": a, "b": b, "result": result})

    def _send(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main(port=8000):
    server = HTTPServer(("0.0.0.0", port), CalculatorHandler)
    print(f"Calculator API {VERSION} listening on port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
