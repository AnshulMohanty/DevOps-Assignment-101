import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app.server import CalculatorHandler


@pytest.fixture(scope="module")
def base_url():
    server = HTTPServer(("127.0.0.1", 0), CalculatorHandler)   # port 0 = any free port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def get(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_health(base_url):
    status, body = get(f"{base_url}/health")
    assert status == 200 and body["status"] == "ok"


def test_add_endpoint(base_url):
    status, body = get(f"{base_url}/add?a=2&b=3")
    assert status == 200 and body["result"] == 5


def test_divide_by_zero_is_400(base_url):
    status, body = get(f"{base_url}/divide?a=1&b=0")
    assert status == 400 and "zero" in body["error"]


def test_unknown_operation_is_404(base_url):
    status, _ = get(f"{base_url}/modulo?a=1&b=2")
    assert status == 404
