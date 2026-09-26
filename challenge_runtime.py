import time
import uuid
from datetime import datetime, timezone

from bot import compose

SCOPES = ("category", "merchant", "customer", "trigger")
contexts = {scope: {} for scope in SCOPES}
_sent_suppression_keys = set()
_started_at = time.monotonic()


def store_context(data):
    if not isinstance(data, dict):
        return {"accepted": False, "reason": "invalid_payload", "details": "Expected a JSON object."}, 400

    scope = data.get("scope")
    if scope not in contexts:
        return {"accepted": False, "reason": "invalid_scope", "details": "scope must be category, merchant, customer, or trigger."}, 400

    context_id = data.get("context_id")
    if not isinstance(context_id, str) or not context_id.strip():
        return {"accepted": False, "reason": "invalid_context_id", "details": "context_id is required."}, 400

    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        return {"accepted": False, "reason": "invalid_version", "details": "version must be a positive integer."}, 400

    payload = data.get("payload")
    if not isinstance(payload, dict):
        return {"accepted": False, "reason": "invalid_payload", "details": "payload must be a JSON object."}, 400

    current = contexts[scope].get(context_id)
    if current and version < current["version"]:
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": current["version"],
        }, 409
    if current and version == current["version"]:
        return {
            "accepted": True,
            "ack_id": current["ack_id"],
            "stored_at": current["stored_at"],
        }, 200

    stored_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    contexts[scope][context_id] = {
        "version": version,
        "payload": payload,
        "stored_at": stored_at,
        "ack_id": f"ack_{context_id}_v{version}",
    }
    return {
        "accepted": True,
        "ack_id": contexts[scope][context_id]["ack_id"],
        "stored_at": stored_at,
    }, 200


def health_status():
    return {
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - _started_at),
        "contexts_loaded": {scope: len(records) for scope, records in contexts.items()},
    }


def _find_context(scope, context_id):
    if not context_id:
        return None
    record = contexts[scope].get(context_id)
    if record:
        return record["payload"]
    for stored in contexts[scope].values():
        payload = stored["payload"]
        key = f"{scope}_id"
        if payload.get(key) == context_id:
            return payload
    return None


def context_payload(scope, context_id):
    if scope not in contexts:
        return None
    return _find_context(scope, context_id)


def _timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (AttributeError, TypeError, ValueError):
        return None


def tick_actions(data):
    if not isinstance(data, dict):
        return []
    available = data.get("available_triggers", [])
    if not isinstance(available, list):
        return []

    now = _timestamp(data.get("now")) or datetime.now(timezone.utc)
    actions = []
    for trigger_id in available:
        if not isinstance(trigger_id, str) or len(actions) >= 20:
            continue
        trigger = _find_context("trigger", trigger_id)
        if not trigger:
            continue
        trigger = {**trigger, "id": trigger.get("id", trigger_id)}
        expiry = _timestamp(trigger.get("expires_at"))
        if expiry and expiry <= now:
            continue

        merchant_id = trigger.get("merchant_id")
        merchant = _find_context("merchant", merchant_id)
        if not merchant:
            continue
        category_id = merchant.get("category_slug") or merchant.get("category_id")
        category = _find_context("category", category_id)
        if not category:
            continue

        customer_id = trigger.get("customer_id")
        customer = _find_context("customer", customer_id) if customer_id else None
        if trigger.get("scope") == "customer" and customer is None:
            continue
        suppression_key = trigger.get("suppression_key", "")
        if suppression_key and suppression_key in _sent_suppression_keys:
            continue

        message = compose(category, merchant, trigger, customer)
        if not message or not message.get("body"):
            continue
        if suppression_key:
            _sent_suppression_keys.add(suppression_key)

        actions.append({
            "conversation_id": f"conv_{uuid.uuid4().hex[:16]}",
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": message.get("send_as", "vera"),
            "trigger_id": trigger_id,
            "template_name": f"vera_{trigger.get('kind', 'message')}_v1",
            "template_params": [],
            "body": message["body"],
            "cta": message.get("cta", "open_ended"),
            "suppression_key": suppression_key,
            "rationale": message.get("rationale", ""),
        })
    return actions
