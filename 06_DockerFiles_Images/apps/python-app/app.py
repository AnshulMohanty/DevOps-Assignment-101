from http.server import BaseHTTPRequestHandler, HTTPServer

PAGE = b"<h1>Python app</h1><p>Anshul Mohanty - 24BCS10191</p>"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    print("Python app listening on 8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
