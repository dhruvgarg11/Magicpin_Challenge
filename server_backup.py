from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/healthz":
            self.send_json({
                "status": "ok"
            })

        elif self.path == "/v1/metadata":
            self.send_json({
                "team_name": "Dhruv Garg",
                "model": "Vera Merchant AI"
            })

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        data = json.loads(body) if body else {}

        if self.path == "/v1/context":
            self.send_json({
                "accepted": True
            })

        elif self.path == "/v1/tick":
            self.send_json({
                "actions": []
            })

        elif self.path == "/v1/reply":
            message = data.get("message", "").lower()

            if any(x in message for x in ["stop messaging", "spam", "useless"]):
                self.send_json({
                    "action": "end"
                })
            elif any(x in message for x in ["ok lets do it", "what's next", "whats next"]):
                self.send_json({
                    "action": "send",
                    "body": "Done — I’ll help you with the next step."
                })
            else:
                self.send_json({
                    "action": "wait",
                    "wait_seconds": 5
                })

        else:
            self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8080), Handler)
    print("Vera bot server running on http://localhost:8080")
    server.serve_forever()
