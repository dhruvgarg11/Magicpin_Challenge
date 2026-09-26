import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bot import compose
from reply_logic import handle_reply
from workspace_data import compose_for_merchant, record, workspace

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset" / "expanded"
PAIRS_FILE = DATA / "test_pairs.json"
contexts = {
    "category": {},
    "merchant": {},
    "trigger": {},
    "customer": {},
}


def load_json(folder, name):
    with (DATA / folder / f"{name}.json").open(encoding="utf-8") as source:
        return json.load(source)


def demo_pairs():
    with PAIRS_FILE.open(encoding="utf-8") as source:
        return json.load(source)["pairs"]


def load_demo_scenario(pair):
    merchant = load_json("merchants", pair["merchant_id"])
    trigger = load_json("triggers", pair["trigger_id"])
    customer = (
        load_json("customers", pair["customer_id"])
        if pair.get("customer_id") else None
    )
    category = load_json("categories", merchant["category_slug"])
    return merchant, trigger, customer, category


class handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def route(self):
        return "/v1/" + parse_qs(urlparse(self.path).query).get("path", [""])[0].lstrip("/")

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def do_GET(self):
        path = self.route()
        if path == "/v1/healthz":
            self.send_json({"status": "ok"})
        elif path == "/v1/metadata":
            self.send_json({"team_name": "Dhruv Garg", "model": "Vera Merchant AI"})
        elif path == "/v1/config":
            import os

            self.send_json({"api_base_url": os.environ.get("VERA_API_BASE_URL", "")})
        elif path == "/v1/workspace":
            merchant_id = parse_qs(urlparse(self.path).query).get("merchant_id", [None])[0]
            result = workspace(merchant_id)
            if result is None:
                self.send_json({"error": "Merchant not found"}, 404)
            else:
                self.send_json(result)
        elif path == "/v1/demo/scenarios":
            scenarios = []
            for pair in demo_pairs():
                merchant, trigger, customer, _ = load_demo_scenario(pair)
                identity = merchant.get("identity", {})
                scenarios.append({
                    "test_id": pair["test_id"],
                    "merchant_id": pair["merchant_id"],
                    "customer_id": pair.get("customer_id"),
                    "trigger_id": pair["trigger_id"],
                    "kind": trigger.get("kind", "unknown"),
                    "urgency": trigger.get("urgency", 0),
                    "category": merchant.get("category_slug", ""),
                    "merchant_name": identity.get("name", "Merchant"),
                    "owner_name": identity.get("owner_first_name", "there"),
                    "city": identity.get("city", ""),
                    "customer_name": customer.get("identity", {}).get("name") if customer else None,
                })
            self.send_json({"scenarios": scenarios})
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        data = self.read_json()
        if data is None:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        path = self.route()
        if path == "/v1/compose":
            result = compose_for_merchant(
                data.get("merchant_id"),
                data.get("trigger_id"),
                data.get("customer_id"),
            )
            if result is None:
                self.send_json({"error": "Merchant, trigger, or customer not found"}, 404)
            else:
                self.send_json(result)
        elif path == "/v1/demo/compose":
            pair = next(
                (item for item in demo_pairs() if item["test_id"] == data.get("test_id")),
                None,
            )
            if pair is None:
                self.send_json({"error": "Unknown demo scenario"}, 404)
                return
            merchant, trigger, customer, category = load_demo_scenario(pair)
            self.send_json({
                "message": compose(category, merchant, trigger, customer),
                "merchant": merchant,
                "trigger": trigger,
                "customer": customer,
            })
        elif path == "/v1/context":
            scope = data.get("scope")
            context_id = data.get("context_id")
            if scope in contexts and context_id:
                contexts[scope][context_id] = data.get("payload", {})
            self.send_json({"accepted": True})
        elif path == "/v1/tick":
            self.send_json({"actions": []})
        elif path == "/v1/reply":
            merchant = record("merchants", "merchant_id", data.get("merchant_id"))
            self.send_json(handle_reply(data, merchant))
        else:
            self.send_json({"error": "Not found"}, 404)
