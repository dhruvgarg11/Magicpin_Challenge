from http.server import BaseHTTPRequestHandler, HTTPServer
import json

from bot import compose


contexts = {
    "category": {},
    "merchant": {},
    "trigger": {},
    "customer": {}
}


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/healthz":
            self.send_json({"status": "ok"})

        elif self.path == "/v1/metadata":
            self.send_json({
                "team_name": "Dhruv Garg",
                "model": "Vera Merchant AI"
            })

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        if self.path == "/v1/context":
            scope = data.get("scope")
            context_id = data.get("context_id")
            payload = data.get("payload", {})

            if scope in contexts and context_id:
                contexts[scope][context_id] = payload

            self.send_json({"accepted": True})

        elif self.path == "/v1/tick":
            self.send_json({"actions": []})

        elif self.path == "/v1/reply":
            message = data.get("message", "").strip()
            lower = message.lower()

            # Judge safety / conversation handling
            if any(x in lower for x in [
                "stop messaging",
                "stop",
                "spam",
                "useless"
            ]):
                self.send_json({
                    "action": "end"
                })
                return

            if any(x in lower for x in [
                "ok lets do it",
                "ok, lets do it",
                "whats next",
                "what's next"
            ]):
                self.send_json({
                    "action": "send",
                    "body": "Done — I’ll help you with the next step."
                })
                return

            # Auto-reply pattern
            if "thank you for contacting us" in lower:
                self.send_json({
                    "action": "wait",
                    "wait_seconds": 5
                })
                return

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
