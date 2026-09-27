import hashlib
import re
from difflib import SequenceMatcher

from challenge_runtime import (
    context_payload,
    conversation_state,
    save_conversation_state,
)


def _normalize(message):
    return " ".join(re.sub(r"[^a-z0-9']+", " ", message.lower()).split())


def _contains_phrase(message, phrase):
    return re.search(
        rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
        message,
    ) is not None


def _is_stop(message):
    explicit_opt_outs = (
        "stop messaging",
        "don't message me",
        "do not message me",
        "don't contact",
        "do not contact",
        "unsubscribe",
        "remove me",
        "no thanks",
        "no thank you",
    )
    if message in ("no", "stop") or any(
        _contains_phrase(message, phrase) for phrase in explicit_opt_outs
    ):
        return True

    not_interested = re.search(r"(?<![a-z0-9])not interested(?![a-z0-9])", message)
    if not_interested:
        continuation = message[not_interested.end():]
        continuing_request = re.search(
            r"\b(?:tell me|show me|share|explain|give me|check|what(?:'s| is|s)?|how|can you|could you|let me know|current status)\b",
            continuation,
        )
        if not continuing_request:
            return True

    if message in {
        "useless",
        "this is useless",
        "that is useless",
        "this was useless",
        "that was useless",
    }:
        return True

    return message in {
        "spam",
        "this is spam",
        "that is spam",
        "that's spam",
        "this looks like spam",
    }


def _is_later(message):
    return any(term in message for term in (
        "busy",
        "not now",
        "later",
        "remind me",
        "give me time",
        "think about it",
        "get back to you",
    ))


def _is_positive(message):
    return message in {
        "yes", "yes please", "yeah", "yep", "sure", "okay", "ok",
        "do it", "send it", "go ahead", "sounds good", "lets do it",
        "let's do it", "okay lets do it", "okay let's do it",
        "ok lets do it", "ok let's do it", "whats next", "what's next",
    } or message.startswith(("yes ", "yes,", "sure ", "sure,", "go ahead "))


def _is_repeat_complaint(message):
    return any(phrase in message for phrase in (
        "same reply why",
        "you already said this",
        "you keep repeating",
        "same message",
        "same reply",
        "repeating yourself",
        "you repeated",
    ))


def _is_canned_auto_reply(message):
    return any(phrase in message for phrase in (
        "thank you for contacting us",
        "thank you for reaching out",
        "our team will respond shortly",
        "we will get back to you",
        "we'll get back to you",
        "business hours",
        "currently away",
        "automated response",
        "auto reply",
    ))


def _same_or_near_message(first, second):
    if not first or not second:
        return False
    if first == second:
        return True
    if min(len(first), len(second)) < 12:
        return False
    return SequenceMatcher(None, first, second).ratio() >= 0.9


def _response(action, rationale, body=None, cta=None, wait_seconds=None):
    result = {"action": action, "rationale": rationale}
    if action == "send":
        result.update({"body": body, "cta": cta or "open_ended"})
    elif action == "wait":
        result["wait_seconds"] = wait_seconds or 1800
    return result


def _positive_followup(state, merchant):
    trigger_id = state.get("trigger_id")
    trigger = context_payload("trigger", trigger_id) if trigger_id else None
    trigger = trigger or {}
    payload = trigger.get("payload") or {}
    topic = payload.get("intent_topic", "")
    cta = state.get("last_assistant_action", "")

    if topic == "kids_yoga_summer_camp" or cta == "draft_program":
        return (
            "Great — I’ll prepare an outline for the kids’ yoga program and "
            "leave the age group, session length, and schedule for your confirmation. "
            "What age range should it cover?"
        )
    if topic == "corporate_bulk_thali_package" or cta == "draft_package":
        return (
            "Great — I’ll outline the per-person price, minimum order, and "
            "delivery terms for the corporate thali package. What minimum order "
            "size should I use?"
        )
    if cta == "review_renewal_options" or trigger.get("kind") == "renewal_due":
        merchant_subscription = (merchant or {}).get("subscription") or {}
        plan = payload.get("plan") or merchant_subscription.get("plan")
        days = payload.get("days_remaining", merchant_subscription.get("days_remaining"))
        amount = payload.get("renewal_amount")
        details = []
        if plan:
            details.append(f"{plan} plan")
        if isinstance(days, (int, float)) and not isinstance(days, bool):
            details.append(f"{days:g} days remaining")
        if isinstance(amount, (int, float)) and not isinstance(amount, bool):
            details.append(f"listed amount {amount:,.0f}")
        if details:
            return "The renewal details on file are " + ", ".join(details) + ". I don’t have additional options recorded, but can help review what’s available."
    if cta == "draft_followup":
        return "Great — I’ll prepare the follow-up using the wedding details already shared, without adding unconfirmed package terms."
    if cta == "draft_match_offer":
        return "Great — I’ll draft match-night copy using the match details already shared. Any offer terms can be added once you confirm them."
    if cta == "draft_festival_offer":
        return "Great — I’ll draft a festival message using the festival details on file and leave any offer terms for your confirmation."

    previous = state.get("last_assistant_body", "")
    if previous:
        return "Thanks for confirming. I’ll take the next step from my previous message; what detail should I use first?"
    return "Thanks for confirming. What would you like me to prepare as the next step?"


def _record_turn(conversation_id, state, data, normalized, result, is_auto_reply, message_fingerprint):
    messages = state.get("messages", [])
    role = data.get("from_role") if data.get("from_role") in ("merchant", "customer") else "merchant"
    messages.append({"role": role, "body": data.get("message", ""), "turn_number": data.get("turn_number")})
    if result.get("action") == "send":
        messages.append({"role": "assistant", "body": result.get("body", ""), "action": "send", "cta": result.get("cta")})
        state["last_assistant_body"] = result.get("body", "")
        state["last_assistant_action"] = result.get("cta", "open_ended")
    else:
        messages.append({"role": "assistant", "body": "", "action": result.get("action")})

    state["messages"] = messages[-10:]
    state["last_user_message"] = normalized
    state["last_user_message_fingerprint"] = message_fingerprint
    state["last_user_was_auto_reply"] = is_auto_reply
    state["last_response"] = result
    turn_number = data.get("turn_number")
    if isinstance(turn_number, int) and not isinstance(turn_number, bool):
        state["last_turn_number"] = turn_number
    state["ended"] = result.get("action") == "end"
    save_conversation_state(conversation_id, state)
    return result


def handle_reply(data, merchant=None):
    if not isinstance(data, dict):
        data = {}
    message = data.get("message", "")
    if not isinstance(message, str):
        message = ""
    normalized = _normalize(message)
    message_fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    conversation_id = data.get("conversation_id")
    state = conversation_state(conversation_id)

    turn_number = data.get("turn_number")
    if (
        isinstance(turn_number, int)
        and not isinstance(turn_number, bool)
        and turn_number == state.get("last_turn_number")
        and (
            message_fingerprint == state.get("last_user_message_fingerprint")
            if state.get("last_user_message_fingerprint")
            else normalized == state.get("last_user_message")
        )
        and isinstance(state.get("last_response"), dict)
    ):
        return state["last_response"]

    if state.get("ended"):
        return _response("end", "This conversation has already been ended.")

    if normalized:
        state["messages"] = state.get("messages", [])[-10:]
    canned_reply = _is_canned_auto_reply(normalized)
    repeated_auto_reply = (
        canned_reply
        and state.get("last_user_was_auto_reply", False)
        and _same_or_near_message(state.get("last_user_message", ""), normalized)
    )
    auto_reply_streak = (
        state.get("auto_reply_streak", 0) + 1
        if repeated_auto_reply
        else 1 if canned_reply else 0
    )
    state["auto_reply_streak"] = auto_reply_streak
    is_repeat_complaint = _is_repeat_complaint(normalized)
    repeat_complaint_count = state.get("repeat_complaint_count", 0) + 1 if is_repeat_complaint else 0
    state["repeat_complaint_count"] = repeat_complaint_count

    if _is_stop(normalized):
        result = _response("end", "Respecting the request to stop or decline further messages.")
    elif _is_later(normalized):
        result = _response("wait", "The user asked for time; pausing instead of continuing to push.", wait_seconds=1800)
    elif is_repeat_complaint and repeat_complaint_count >= 3:
        result = _response(
            "end",
            "Ending after repeated complaints that the reply is repetitive.",
        )
    elif is_repeat_complaint and repeat_complaint_count == 2:
        result = _response(
            "send",
            "Acknowledging the repeated complaint and switching to a concise alternative.",
            "Understood — I’ll stop repeating that prompt. Tell me one specific detail you’d like me to address, and I’ll respond to that directly.",
        )
    elif is_repeat_complaint:
        previous_assistant = state.get("last_assistant_body", "")
        if "subscription expiry" in previous_assistant.lower():
            next_step = "I can switch to reviewing the subscription details on file"
        else:
            next_step = "I can switch to a different next step or answer a specific question"
        result = _response(
            "send",
            "Acknowledging the repetition complaint and changing the response direction.",
            f"You're right — I repeated myself. {next_step}. What would be most useful?",
        )
    elif canned_reply:
        if auto_reply_streak >= 2:
            result = _response("end", "Repeated identical or near-identical automated response detected; ending to avoid further repetition.")
        else:
            result = _response("wait", "The message appears automated or repeated; pausing rather than replying with another prompt.", wait_seconds=1800)
    elif any(term in normalized for term in ("you are stupid", "idiot", "shut up", "you are useless", "fuck off", "abusive")):
        result = _response("end", "Ending the exchange rather than escalating a hostile conversation.")
    elif any(term in normalized for term in ("file my gst", "gst return", "unrelated", "different topic", "off topic")):
        result = _response(
            "send",
            "Briefly setting a boundary and redirecting to the merchant-assistant scope.",
            "I can’t file or submit GST returns here. I can help with the business task we were discussing, or you can ask me a specific question about it.",
        )
    elif _is_positive(normalized):
        result = _response(
            "send",
            "Acknowledging positive intent and continuing the task associated with this conversation.",
            _positive_followup(state, merchant),
        )
    elif merchant:
        performance = merchant.get("performance") or {}
        metrics = {
            "views": ("profile views", performance.get("views")),
            "impressions": ("profile views", performance.get("views")),
            "calls": ("calls", performance.get("calls")),
            "directions": ("direction requests", performance.get("directions")),
            "leads": ("leads", performance.get("leads")),
        }
        requested_metric = next((value for key, value in metrics.items() if key in normalized), None)
        if requested_metric and isinstance(requested_metric[1], (int, float)):
            label, value = requested_metric
            period = performance.get("window_days")
            period_text = f" over the last {period} days" if period else ""
            result = _response(
                "send",
                "Answering from the selected merchant's recorded performance context.",
                f"{merchant.get('identity', {}).get('name', 'Your business')} recorded {value:,} {label}{period_text}.",
            )
        elif "offer" in normalized or "promotion" in normalized:
            active_offers = [
                offer.get("title")
                for offer in merchant.get("offers", [])
                if offer.get("title") and offer.get("status") == "active"
            ]
            if active_offers:
                result = _response(
                    "send",
                    "Answering from offers recorded in the selected merchant context.",
                    f"The active offer recorded for {merchant.get('identity', {}).get('name', 'your business')} is {', '.join(active_offers[:3])}.",
                )
            else:
                result = _response(
                    "send",
                    "No active offer is present in the selected merchant context.",
                    "I don’t have an active offer recorded for this merchant yet. Tell me what you’re considering and I can help shape it.",
                )
        else:
            name = merchant.get("identity", {}).get("name", "your business")
            result = _response(
                "send",
                "Responding to the current turn without restarting the conversation introduction.",
                f"Thanks for the detail about {name}. What specific next step should we focus on?",
            )
    else:
        result = _response(
            "send",
            "Responding to the current turn without restarting the conversation introduction.",
            "Thanks for the context. What specific next step should we focus on?",
        )

    return _record_turn(
        conversation_id,
        state,
        data,
        normalized,
        result,
        canned_reply,
        message_fingerprint,
    )