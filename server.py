import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from bot import compose

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"
DATA = ROOT / "dataset" / "expanded"
PAIRS_FILE = DATA / "test_pairs.json"

app = FastAPI(title="Vera Merchant AI")
contexts = {
    "category": {},
    "merchant": {},
    "trigger": {},
    "customer": {},
}


def load_json(folder, name):
    with (DATA / folder / f"{name}.json").open(encoding="utf-8") as source:
        return json.load(source)


def load_demo_scenario(pair):
    merchant = load_json("merchants", pair["merchant_id"])
    trigger = load_json("triggers", pair["trigger_id"])
    customer = (
        load_json("customers", pair["customer_id"])
        if pair.get("customer_id") else None
    )
    category = load_json("categories", merchant["category_slug"])
    return merchant, trigger, customer, category


def demo_pairs():
    with PAIRS_FILE.open(encoding="utf-8") as source:
        return json.load(source)["pairs"]


@app.get("/")
async def home():
    return FileResponse(FRONTEND / "index.html")


@app.get("/app.css")
async def stylesheet():
    return FileResponse(FRONTEND / "app.css", media_type="text/css")


@app.get("/app.js")
async def javascript():
    return FileResponse(FRONTEND / "app.js", media_type="text/javascript")


@app.get("/v1/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/v1/metadata")
async def metadata():
    return {"team_name": "Dhruv Garg", "model": "Vera Merchant AI"}


@app.get("/v1/demo/scenarios")
async def scenarios():
    result = []
    for pair in demo_pairs():
        merchant, trigger, customer, _ = load_demo_scenario(pair)
        identity = merchant.get("identity", {})
        result.append({
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
            "customer_name": (
                customer.get("identity", {}).get("name") if customer else None
            ),
        })
    return {"scenarios": result}


@app.post("/v1/demo/compose")
async def demo_compose(request: Request):
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    pair = next(
        (item for item in demo_pairs() if item["test_id"] == data.get("test_id")),
        None,
    )
    if pair is None:
        return JSONResponse({"error": "Unknown demo scenario"}, status_code=404)

    merchant, trigger, customer, category = load_demo_scenario(pair)
    return {
        "message": compose(category, merchant, trigger, customer),
        "merchant": merchant,
        "trigger": trigger,
        "customer": customer,
    }


@app.post("/v1/context")
async def context(request: Request):
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError):
        data = {}

    scope = data.get("scope")
    context_id = data.get("context_id")
    if scope in contexts and context_id:
        contexts[scope][context_id] = data.get("payload", {})
    return {"accepted": True}


@app.post("/v1/tick")
async def tick():
    return {"actions": []}


@app.post("/v1/reply")
async def reply(request: Request):
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    message = data.get("message", "").strip()
    lower = message.lower()
    if any(term in lower for term in ("stop messaging", "stop", "spam", "useless")):
        return {"action": "end"}

    if any(term in lower for term in ("ok lets do it", "ok, lets do it", "whats next", "what's next")):
        return {
            "action": "send",
            "body": "Done — I’ll help you with the next step.",
        }

    return {"action": "wait", "wait_seconds": 5}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=int(os.environ.get("PORT", "8080")))