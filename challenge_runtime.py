import json
import os
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from bot import compose

SCOPES = ("category", "merchant", "customer", "trigger")
contexts = {scope: {} for scope in SCOPES}
_sent_suppression_keys = set()
_started_at = time.monotonic()


def _kv_settings():
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("VERA_KV_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("VERA_KV_REST_TOKEN")
    return url.rstrip("/") if url else "", token or ""


def _shared_store_enabled():
    url, token = _kv_settings()
    if bool(url) != bool(token):
        raise RuntimeError("Configure both KV_REST_API_URL and KV_REST_API_TOKEN for shared context storage.")
    return bool(url and token)


def _kv_command(*command):
    url, token = _kv_settings()
    if not url or not token:
        raise RuntimeError("Shared context storage is not configured.")
    request = Request(
        url,
        data=json.dumps(list(command)).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=3) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Shared context storage request failed: {error}") from error
    if result.get("error"):
        raise RuntimeError(f"Shared context storage error: {result['error']}")
    return result.get("result")


def _context_key(scope, context_id):
    return f"vera:context:{scope}:{quote(context_id, safe='')}"


def _load_context_record(scope, context_id):
    if _shared_store_enabled():
        stored = _kv_command("GET", _context_key(scope, context_id))
        return json.loads(stored) if isinstance(stored, str) else stored
    return contexts[scope].get(context_id)


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

    current = _load_context_record(scope, context_id)
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
    record = {
        "version": version,
        "payload": payload,
        "stored_at": stored_at,
        "ack_id": f"ack_{context_id}_v{version}",
    }
    if _shared_store_enabled():
        script = (
            "local old=redis.call('GET',KEYS[1]); "
            "if old then local current=cjson.decode(old); "
            "if tonumber(ARGV[1]) < tonumber(current.version) then "
            "return cjson.encode({accepted=false,reason='stale_version',current_version=current.version}); "
            "elseif tonumber(ARGV[1]) == tonumber(current.version) then return old; end; "
            "else redis.call('INCR',KEYS[2]); end; "
            "redis.call('SET',KEYS[1],ARGV[2]); return ARGV[2]"
        )
        result = _kv_command(
            "EVAL",
            script,
            "2",
            _context_key(scope, context_id),
            f"vera:context-count:{scope}",
            str(version),
            json.dumps(record, ensure_ascii=False),
        )
        if isinstance(result, str):
            saved = json.loads(result)
        else:
            saved = result
        if isinstance(saved, dict) and saved.get("accepted") is False:
            return saved, 409
        record = saved
    contexts[scope][context_id] = record
    return {
        "accepted": True,
        "ack_id": contexts[scope][context_id]["ack_id"],
        "stored_at": stored_at,
    }, 200


def health_status():
    shared_store = _shared_store_enabled()
    if shared_store:
        counts = {
            scope: int(_kv_command("GET", f"vera:context-count:{scope}") or 0)
            for scope in SCOPES
        }
    else:
        counts = {scope: len(records) for scope, records in contexts.items()}
    return {
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - _started_at),
        "contexts_loaded": counts,
        "context_store": "shared" if shared_store else "instance-memory",
    }


def _find_context(scope, context_id):
    if not context_id:
        return None
    record = _load_context_record(scope, context_id)
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


def _claim_suppression(key):
    if not key:
        return True
    if _shared_store_enabled():
        return _kv_command("SET", f"vera:suppression:{quote(key, safe='')}", "1", "NX") == "OK"
    if key in _sent_suppression_keys:
        return False
    _sent_suppression_keys.add(key)
    return True


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
        if not _claim_suppression(suppression_key):
            continue

        message = compose(category, merchant, trigger, customer)
        if not message or not message.get("body"):
            continue
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
