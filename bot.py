def compose(category, merchant, trigger, customer=None):

    kind = trigger.get("kind", "")
    owner_name = merchant.get("identity", {}).get(
        "owner_first_name", "there"
    )

    # IPL MATCH TODAY
    if kind == "ipl_match_today":
        payload = trigger.get("payload", {})

        if payload.get("placeholder"):
            return {
                "body": f"Quick one, {owner_name} — there’s a match-night opportunity today. Want me to suggest a simple offer?",
                "cta": "draft_match_offer",
                "send_as": "vera",
                "suppression_key": trigger.get("suppression_key", ""),
                "rationale": "Placeholder-safe match-day opportunity."
            }

        match = payload.get("match", "today's match")
        venue = payload.get("venue", "")
        offer = payload.get("offer", {})

        body = f"Quick one, {owner_name} — {match} is on today"
        if venue:
            body += f" at {venue}"
        body += "."

        if isinstance(offer, dict):
            title = offer.get("title", "")
            price = offer.get("price", "")
            if title:
                body += f" {title}"
            if price:
                body += f" @ ₹{price}"

        body += " This could be worth pushing for match-night orders. Want me to draft the WhatsApp copy?"

        return {
            "body": body,
            "cta": "draft_match_offer",
            "send_as": "vera",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": f"Match-day trigger detected: {match} at {venue}."
        }

    # MILESTONE REACHED
    if kind == "milestone_reached":
        payload = trigger.get("payload", {})

        review_count = payload.get("value_now")
        milestone = payload.get("milestone_value")
        imminent = payload.get("is_imminent", False)

        if review_count is None or milestone is None:
            return {
                "body": (
                    f"Hi {owner_name} — you've reached an important review milestone. "
                    f"Want me to help you build on the momentum?"
                ),
                "cta": "suggest_review_growth",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key", ""
                ),
                "rationale": "Review milestone detected, but exact milestone values are unavailable."
            }

        reviews_left = max(
            milestone - review_count,
            0
        )

        if imminent and reviews_left > 0:
            body = (
                f"Hi {owner_name} — you're at {review_count} reviews, "
                f"just {reviews_left} away from {milestone}. "
                f"Want me to suggest a simple way to get there?"
            )
        else:
            body = (
                f"Hi {owner_name} — you've reached {milestone} reviews. "
                f"Want me to help you build on the momentum?"
            )

        return {
            "body": body,
            "cta": "suggest_review_growth",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key", ""
            ),
            "rationale": (
                f"Review milestone detected: "
                f"{review_count}/{milestone}."
            )
        }

    # ACTIVE PLANNING INTENT
    if kind == "active_planning_intent":
        payload = trigger.get("payload", {})

        intent_topic = payload.get(
            "intent_topic",
            ""
        )
        merchant_last_message = payload.get(
            "merchant_last_message",
            ""
        )

        if intent_topic == "corporate_bulk_thali_package":
            body = (
                f"Hi {owner_name} — for a corporate bulk thali package, "
                f"I'd structure it around a fixed per-person price, "
                f"minimum order size, and simple delivery terms. "
                f"Want me to draft a sample package?"
            )
            cta = "draft_package"
        else:
            body = (
                f"Hi {owner_name} — I can help turn that idea into "
                f"a simple offer structure. Want me to draft a sample?"
            )
            cta = "draft_offer"

        return {
            "body": body,
            "cta": cta,
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Active planning intent detected: "
                f"{intent_topic}. "
                f"Merchant message: {merchant_last_message}"
            )
        }

    # SEASONAL PERFORMANCE DIP
    if kind == "seasonal_perf_dip":
        payload = trigger.get("payload", {})

        metric = payload.get("metric", "performance")
        delta_pct = payload.get("delta_pct", 0)
        window = payload.get("window", "")
        is_expected_seasonal = payload.get(
            "is_expected_seasonal",
            False
        )
        season_note = payload.get(
            "season_note",
            ""
        )

        percent = round(abs(delta_pct) * 100)

        if is_expected_seasonal:
            body = (
                f"Hi {owner_name} — your {metric} are down "
                f"{percent}% over the last {window}. "
                f"This looks like an expected seasonal dip. "
                f"Want me to suggest a low-effort way to "
                f"maintain visibility during this period?"
            )
        else:
            body = (
                f"Hi {owner_name} — your {metric} are down "
                f"{percent}% over the last {window}. "
                f"Want me to suggest a way to improve them?"
            )

        return {
            "body": body,
            "cta": "suggest_seasonal_action",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Seasonal {metric} dip detected: "
                f"{percent}% over {window}. "
                f"Season note: {season_note}."
            )
        }

    # CUSTOMER LAPSED HARD
    if kind == "customer_lapsed_hard":
        payload = trigger.get("payload", {})

        customer_name = "there"

        if customer:
            customer_name = customer.get(
                "identity",
                {}
            ).get(
                "name",
                "there"
            )

        days_since_last_visit = payload.get(
            "days_since_last_visit",
            0
        )
        previous_focus = payload.get(
            "previous_focus",
            ""
        )
        previous_membership_months = payload.get(
            "previous_membership_months",
            0
        )

        focus_text = previous_focus.replace(
            "_",
            " "
        )

        body = (
            f"Hi {customer_name} — it’s been "
            f"{days_since_last_visit} days since your last visit. "
            f"You previously focused on {focus_text} and had a "
            f"{previous_membership_months}-month membership. "
            f"Would you like to explore getting back into a routine?"
        )

        return {
            "body": body,
            "cta": "explore_return",
            "send_as": "merchant_on_behalf",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Customer win-back triggered after "
                f"{days_since_last_visit} days since last visit."
            )
        }

    # CUSTOMER LAPSED SOFT

    if kind == "customer_lapsed_soft":
        customer_name = "there"

        if customer:
            customer_name = customer.get(
                "identity",
                {}
            ).get(
                "name",
                "there"
            )

        return {
            "body": (
                f"Hi {customer_name} — we haven’t seen you in a while. "
                "Would you like to explore getting back into your routine?"
            ),
            "cta": "explore_return",
            "send_as": "merchant_on_behalf",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                "Customer re-engagement prompt; the trigger does not provide "
                "specific lapse details."
            )
        }

    # TRIAL FOLLOW-UP
    if kind == "trial_followup":
        payload = trigger.get("payload", {})

        trial_date = payload.get(
            "trial_date",
            ""
        )
        next_session_options = payload.get(
            "next_session_options",
            []
        )

        customer_name = "there"

        if customer:
            customer_name = customer.get(
                "identity",
                {}
            ).get(
                "name",
                "there"
            )

        if next_session_options:
            first_option = next_session_options[0]

            session_label = first_option.get(
                "label",
                ""
            )

            body = (
                f"Hi {customer_name} — following up after your trial "
                f"on {trial_date}. The next session option is "
                f"{session_label}. Would you like to book it?"
            )
        else:
            body = (
                f"Hi {customer_name} — following up after your trial "
                f"on {trial_date}. Would you like to book your next session?"
            )

        return {
            "body": body,
            "cta": "book_trial_followup",
            "send_as": "merchant_on_behalf",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Trial follow-up triggered after trial "
                f"on {trial_date}."
            )
        }

    # SUPPLY ALERT
    if kind == "supply_alert":
        payload = trigger.get("payload", {})

        molecule = payload.get(
            "molecule",
            "the affected medicine"
        )
        affected_batches = payload.get(
            "affected_batches",
            []
        )
        manufacturer = payload.get(
            "manufacturer",
            ""
        )

        batches_text = ", ".join(
            affected_batches
        )

        return {
            "body": (
                f"Hi {owner_name} — recall alert for {molecule} "
                f"from {manufacturer}. Affected batches: "
                f"{batches_text}. Please check these batches "
                f"in your inventory. Want me to help you make "
                f"a quick checklist?"
            ),
            "cta": "review_recall",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Supply alert for {molecule}; affected batches: "
                f"{batches_text}."
            )
        }

    # APPOINTMENT TOMORROW
    if kind == "appointment_tomorrow":
        customer_name = "there"

        if customer:
            customer_name = customer.get(
                "identity",
                {}
            ).get(
                "name",
                "there"
            )

        return {
            "body": (
                f"Hi {customer_name} — quick reminder: "
                f"you have an appointment tomorrow. "
                f"Would you like me to help you confirm the appointment?"
            ),
            "cta": "confirm_appointment",
            "send_as": "merchant_on_behalf",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                "Appointment scheduled for tomorrow."
            )
        }

    # RECALL DUE
    if kind == "recall_due":
        payload = trigger.get("payload", {})

        customer_name = "there"
        if customer:
            customer_name = customer.get(
                "identity",
                {}
            ).get(
                "name",
                "there"
            )

        if payload.get("placeholder"):
            return {
                "body": (
                    f"Hi {customer_name} — your next visit is due soon. "
                    f"Would you like to book a slot?"
                ),
                "cta": "book_slot",
                "send_as": "merchant_on_behalf",
                "suppression_key": trigger.get(
                    "suppression_key",
                    ""
                ),
                "rationale": (
                    "Recall is due, but exact service and appointment "
                    "details are unavailable."
                )
            }

        service_due = payload.get(
            "service_due",
            "your next visit"
        )
        due_date = payload.get(
            "due_date",
            ""
        )
        available_slots = payload.get(
            "available_slots",
            []
        )

        slots_text = ", ".join(
            slot.get("label", "") if isinstance(slot, dict) else str(slot)
            for slot in available_slots
        )

        body = (
            f"Hi {customer_name} — your {service_due} is due"
        )

        if due_date:
            body += f" on {due_date}"

        if slots_text:
            body += f". Available: {slots_text}"

        body += ". Would you like to book a slot?"

        return {
            "body": body,
            "cta": "book_slot",
            "send_as": "merchant_on_behalf",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Recall due for {service_due}."
            )
        }

    # CHRONIC REFILL DUE
    if kind == "chronic_refill_due":
        payload = trigger.get("payload", {})

        if payload.get("placeholder"):
            customer_name = "there"
            if customer:
                customer_name = customer.get(
                    "identity",
                    {}
                ).get(
                    "name",
                    "there"
                )

            return {
                "body": (
                    f"Hi {customer_name} — your regular refill is coming up. "
                    "Would you like to arrange your refill?"
                ),
                "cta": "arrange_refill",
                "send_as": "merchant_on_behalf",
                "suppression_key": trigger.get(
                    "suppression_key",
                    ""
                ),
                "rationale": (
                    "Chronic refill reminder; specific refill details "
                    "are not available in the trigger payload."
                )
            }

        molecule_list = payload.get(
            "molecule_list",
            []
        )
        last_refill = payload.get(
            "last_refill",
            ""
        )
        stock_runs_out_iso = payload.get(
            "stock_runs_out_iso",
            ""
        )

        stock_runs_out_display = stock_runs_out_iso
        if stock_runs_out_iso:
            try:
                from datetime import datetime
                stock_runs_out_display = datetime.fromisoformat(
                    stock_runs_out_iso
                ).strftime("%d %b %Y")
            except ValueError:
                stock_runs_out_display = stock_runs_out_iso
        delivery_address_saved = payload.get(
            "delivery_address_saved",
            False
        )

        customer_name = "there"

        if customer:
            customer_name = customer.get(
                "identity",
                {}
            ).get(
                "name",
                "there"
            )

        medicines_text = ", ".join(
            molecule_list
        )

        if delivery_address_saved:
            delivery_text = (
                "Your saved delivery address is available."
            )
        else:
            delivery_text = (
                "Please confirm your delivery address."
            )

        body = (
            f"Hi {customer_name} — your regular refill for "
            f"{medicines_text} is coming up. "
            f"Your last refill was on {last_refill}, and stock "
            f"is expected to run out around {stock_runs_out_display}. "
            f"{delivery_text} Would you like to arrange the refill?"
        )

        return {
            "body": body,
            "cta": "arrange_refill",
            "send_as": "merchant_on_behalf",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Chronic refill due for {medicines_text}; "
                f"stock expected to run out around "
                f"{stock_runs_out_iso}."
            )
        }

    # WEDDING PACKAGE FOLLOW-UP
    if kind == "wedding_package_followup":
        payload = trigger.get("payload", {})

        wedding_date = payload.get(
            "wedding_date",
            ""
        )
        trial_completed = payload.get(
            "trial_completed",
            ""
        )
        days_until = payload.get(
            "days_until_wedding",
            0
        )
        next_step = payload.get(
            "next_step_window_open",
            ""
        )

        next_step_text = next_step.replace(
            "_",
            " "
        )

        return {
            "body": (
                f"Hi {owner_name} — your client's wedding is on "
                f"{wedding_date}, {days_until} days away. "
                f"Since the trial was completed on {trial_completed}, "
                f"this is a good window to plan the "
                f"{next_step_text}. Want me to draft the follow-up?"
            ),
            "cta": "draft_followup",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Wedding follow-up triggered with next step: "
                f"{next_step_text}."
            )
        }

    # CURIOUS ASK DUE
    if kind == "curious_ask_due":
        payload = trigger.get("payload", {})

        ask_template = payload.get(
            "ask_template",
            ""
        )

        if ask_template == "what_service_in_demand_this_week":
            body = (
                f"Hi {owner_name} — want me to check what services "
                f"are in demand this week and suggest one worth promoting?"
            )
        else:
            body = (
                f"Hi {owner_name} — want me to suggest a useful trend "
                f"or service idea for your business this week?"
            )

        return {
            "body": body,
            "cta": "suggest_demand",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Curious ask triggered for template: "
                f"{ask_template}."
            )
        }

    # WINBACK ELIGIBLE
    if kind == "winback_eligible":
        payload = trigger.get("payload", {})

        days_since_expiry = payload.get(
            "days_since_expiry",
            0
        )
        perf_dip_pct = payload.get(
            "perf_dip_pct",
            0
        )

        percent = round(abs(perf_dip_pct) * 100)

        body = (
            f"Hi {owner_name} — it’s been {days_since_expiry} days since "
            f"your last active period. "
        )

        if perf_dip_pct:
            body += (
                f"Your recent performance is down {percent}%. "
            )

        body += "Want me to suggest a quick win-back offer?"

        return {
            "body": body,
            "cta": "suggest_winback_offer",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Win-back eligibility detected after {days_since_expiry} "
                f"days since expiry."
            )
        }

    if kind == "perf_dip":
        payload = trigger.get("payload", {})

        if payload.get("placeholder"):
            return {
                "body": (
                    f"Quick heads-up, {owner_name} — "
                    f"your recent performance has dipped. "
                    f"Want me to suggest a simple way to bring it back up?"
                ),
                "cta": "suggest_action",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key", ""
                ),
                "rationale": (
                    "Performance dip detected, but exact performance "
                    "metrics are unavailable."
                )
            }

        perf_dip = payload.get(
            "delta_pct",
            0
        )

        metric = payload.get(
            "metric",
            "performance"
        )

        window = payload.get(
            "window",
            ""
        )

        percent = round(
            abs(perf_dip) * 100
        )

        body = (
            f"Quick heads-up, {owner_name} — "
            f"your {metric} are down {percent}% "
            f"over the last {window}. "
            f"Want me to suggest a simple way to bring them back up?"
        )

        return {
            "body": body,
            "cta": "suggest_action",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Performance dip detected: "
                f"{percent}% over {window}."
            )
        }

    # REVIEW THEME EMERGED
    # PERF SPIKE
    if kind == "perf_spike":
        payload = trigger.get("payload", {})

        if payload.get("placeholder"):
            return {
                "body": (
                    f"Nice one, {owner_name} — "
                    f"your recent performance is showing a positive spike. "
                    f"Want me to help you build on it?"
                ),
                "cta": "build_on_growth",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key", ""
                ),
                "rationale": (
                    "Performance spike detected, but exact performance "
                    "metrics are unavailable."
                )
            }

        metric = payload.get("metric", "performance")
        delta_pct = payload.get("delta_pct", 0)
        window = payload.get("window", "recent period")
        baseline = payload.get("vs_baseline")
        likely_driver = payload.get("likely_driver", "")

        percent = round(abs(delta_pct) * 100)

        body = (
            f"Nice one, {owner_name} — your {metric} are up "
            f"{percent}% over the last {window}."
        )

        if baseline is not None:
            body += f" Your baseline is {baseline}."

        if likely_driver:
            body += f" It may be linked to {likely_driver}."

        body += " Want me to help you build on it?"

        return {
            "body": body,
            "cta": "build_on_growth",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key", ""
            ),
            "rationale": (
                f"Performance spike detected: "
                f"{percent}% over {window}."
            )
        }

    if kind == "review_theme_emerged":
        payload = trigger.get("payload", {})

        theme = payload.get(
            "theme",
            "review theme"
        )
        occurrences = payload.get(
            "occurrences_30d",
            0
        )
        trend = payload.get(
            "trend",
            ""
        )
        common_quote = payload.get(
            "common_quote",
            ""
        )

        theme_text = theme.replace(
            "_",
            " "
        )

        return {
            "body": (
                f"Hi {owner_name} — {theme_text} has come up "
                f"{occurrences} times in the last 30 days and "
                f"is {trend}. One customer said: "
                f"“{common_quote}”. "
                f"Want me to suggest a practical fix?"
            ),
            "cta": "suggest_review_action",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Rising review theme detected: "
                f"{theme_text}, {occurrences} occurrences "
                f"in 30 days."
            )
        }

    # REGULATION CHANGE
    if kind == "regulation_change":
        payload = trigger.get("payload", {})

        top_item_id = payload.get(
            "top_item_id"
        )
        deadline = payload.get(
            "deadline_iso",
            ""
        )

        digest_items = category.get(
            "digest",
            []
        )

        item = next(
            (
                d
                for d in digest_items
                if d.get("id") == top_item_id
            ),
            None
        )

        if item:
            title = item.get(
                "title",
                "a regulatory update"
            )
            source = item.get(
                "source",
                ""
            )
            summary = item.get(
                "summary",
                ""
            )
            actionable = item.get(
                "actionable",
                ""
            )

            return {
                "body": (
                    f"Hi {owner_name} — compliance update: "
                    f"{title}. {summary} Deadline: {deadline}. "
                    f"{actionable}. Want me to help you turn "
                    f"this into a quick checklist?"
                ),
                "cta": "review_compliance",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key",
                    ""
                ),
                "rationale": (
                    f"Regulation change matched category item "
                    f"{top_item_id} from {source}."
                )
            }

        return {
            "body": (
                f"Hi {owner_name} — there’s a new compliance "
                f"update relevant to your practice. "
                f"Deadline: {deadline}. "
                f"Want me to help you review what needs to change?"
            ),
            "cta": "review_compliance",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                "Regulation trigger received but matching "
                "digest item was unavailable."
            )
        }

    # RESEARCH DIGEST
    if kind == "research_digest":
        payload = trigger.get("payload", {})

        top_item_id = payload.get(
            "top_item_id"
        )

        digest_items = category.get(
            "digest",
            []
        )

        item = next(
            (
                d
                for d in digest_items
                if d.get("id") == top_item_id
            ),
            None
        )

        if item:
            title = item.get(
                "title",
                "a new research update"
            )
            source = item.get(
                "source",
                ""
            )
            summary = item.get(
                "summary",
                ""
            )
            actionable = item.get(
                "actionable",
                ""
            )

            return {
                "body": (
                    f"Hi {owner_name} — new research worth a look: "
                    f"{title}. {summary} Source: {source}. "
                    f"{actionable}. Want me to help turn this into "
                    f"a practical action for your clinic?"
                ),
                "cta": "review_research",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key",
                    ""
                ),
                "rationale": (
                    f"Research digest matched category item "
                    f"{top_item_id}."
                )
            }

        return {
            "body": (
                f"Hi {owner_name} — there’s a new research update "
                f"relevant to your practice. Want me to pull out "
                f"the practical takeaway?"
            ),
            "cta": "review_research",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                "Research trigger received but matching "
                "digest item was unavailable."
            )
        }
        # CATEGORY SEASONAL
    if kind == "category_seasonal":
        payload = trigger.get("payload", {})

        season = payload.get("season", "")
        trends = payload.get("trends", [])
        shelf_action_recommended = payload.get(
            "shelf_action_recommended",
            False
        )

        trends_text = ", ".join(
            trend.replace("_", " ")
            for trend in trends
        )

        if shelf_action_recommended:
            action_text = (
                "A shelf refresh could help you capture the shift."
            )
        else:
            action_text = (
                "It may be worth reviewing your inventory mix."
            )

        return {
            "body": (
                f"Hi {owner_name} — {season.replace('_', ' ')} "
                f"demand is shifting: {trends_text}. "
                f"{action_text} Want me to suggest what to prioritise?"
            ),
            "cta": "suggest_shelf_action",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Seasonal category demand shift detected for "
                f"{season}."
            )
        }

    # CDE OPPORTUNITY
    if kind == "cde_opportunity":
        payload = trigger.get("payload", {})
        digest_id = payload.get("digest_item_id")

        digest_item = None
        for item in category.get("digest", []):
            if item.get("id") == digest_id:
                digest_item = item
                break

        if digest_item:
            title = digest_item.get("title", "a relevant CDE opportunity")
            summary = digest_item.get("summary", "")
            credits = payload.get("credits", digest_item.get("credits", ""))
            fee = payload.get("fee", "")

            body = f"Hi {owner_name} — CDE opportunity: {title}."
            if summary:
                body += f" {summary}"
            if credits:
                body += f" It offers {credits} credits."
            if fee == "free_for_members":
                body += " Free for members."
            elif fee:
                body += f" Fee: {fee}."

            body += " Want me to help you check if it’s useful for your practice?"

            return {
                "body": body,
                "cta": "review_cde",
                "send_as": "vera",
                "suppression_key": trigger.get("suppression_key", ""),
                "rationale": "Matched the CDE trigger to the category digest item."
            }

        return {
            "body": f"Hi {owner_name} — there’s a relevant CDE opportunity. Want me to help you check if it’s useful for your practice?",
            "cta": "review_cde",
            "send_as": "vera",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": "CDE opportunity detected, but matching digest details are unavailable."
        }

    # COMPETITOR OPENED
    if kind == "competitor_opened":
        payload = trigger.get("payload", {})

        if payload.get("placeholder"):
            return {
                "body": (
                    f"Hi {owner_name} — a nearby competitor signal has come up. "
                    "Would you like me to suggest ways to strengthen your local positioning?"
                ),
                "cta": "suggest_positioning",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key",
                    ""
                ),
                "rationale": (
                    "Competitor-opened signal detected; specific competitor details "
                    "are not available in the trigger payload."
                )
            }

        competitor_name = payload.get(
            "competitor_name",
            "a nearby competitor"
        )
        distance_km = payload.get(
            "distance_km",
            ""
        )
        their_offer = payload.get(
            "their_offer",
            ""
        )
        opened_date = payload.get(
            "opened_date",
            ""
        )

        return {
            "body": (
                f"Hi {owner_name} — a nearby competitor, "
                f"{competitor_name}, opened {distance_km} km away "
                f"on {opened_date}. Their current offer is "
                f"{their_offer}. "
                f"Want me to suggest ways to strengthen your "
                f"local positioning?"
            ),
            "cta": "suggest_positioning",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Competitor opened {distance_km} km away with "
                f"offer: {their_offer}."
            )
        }

    # DORMANT WITH VERA
    if kind == "dormant_with_vera":
        payload = trigger.get("payload", {})

        if payload.get("placeholder"):
            return {
                "body": (
                    f"Hi {owner_name} — it’s been a while since we last spoke. "
                    "Want to pick up our conversation again?"
                ),
                "cta": "resume_conversation",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key",
                    ""
                ),
                "rationale": (
                    "Merchant has been inactive with Vera; specific inactivity "
                    "duration and previous topic are not available."
                )
            }

        days_since_last_message = payload.get(
            "days_since_last_merchant_message",
            0
        )
        last_topic = payload.get(
            "last_topic",
            ""
        )

        topic_text = last_topic.replace(
            "_",
            " "
        )

        return {
            "body": (
                f"Hi {owner_name} — it’s been "
                f"{days_since_last_message} days since we last "
                f"spoke. We were discussing {topic_text}. "
                f"Want to pick that back up?"
            ),
            "cta": "resume_conversation",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Merchant has been inactive with Vera for "
                f"{days_since_last_message} days."
            )
        }

    # FESTIVAL UPCOMING
    if kind == "festival_upcoming":
        payload = trigger.get("payload", {})

        if payload.get("placeholder"):
            return {
                "body": (
                    f"Quick heads-up, {owner_name} — "
                    f"a festival-related campaign opportunity is coming up. "
                    f"Want me to draft a festive offer?"
                ),
                "cta": "draft_festival_offer",
                "send_as": "vera",
                "suppression_key": trigger.get(
                    "suppression_key",
                    ""
                ),
                "rationale": (
                    "Festival opportunity detected, but exact festival "
                    "details are unavailable."
                )
            }

        festival = payload.get(
            "festival",
            "an upcoming festival"
        )
        festival_date = payload.get(
            "festival_date",
            ""
        )

        body = (
            f"Quick heads-up, {owner_name} — "
            f"{festival} is coming up. "
            "A festive campaign could be worth planning early. "
            "Want me to draft a festive offer?"
        )

        return {
            "body": body,
            "cta": "draft_festival_offer",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"Festival opportunity detected: {festival}."
            )
        }

    # GBP UNVERIFIED
    if kind == "gbp_unverified":
        payload = trigger.get("payload", {})

        verified = payload.get(
            "verified",
            False
        )
        verification_path = payload.get(
            "verification_path",
            ""
        )
        estimated_uplift_pct = payload.get(
            "estimated_uplift_pct",
            0
        )

        uplift_percent = round(
            estimated_uplift_pct * 100
        )

        if not verified:
            body = (
                f"Hi {owner_name} — your Google Business Profile "
                f"is still unverified. You can verify it via "
                f"{verification_path.replace('_', ' ')}. "
                f"This could help improve visibility; the current "
                f"estimate is around {uplift_percent}% uplift. "
                f"Want me to walk you through the next step?"
            )
        else:
            body = (
                f"Hi {owner_name} — your Google Business Profile "
                f"is verified. Want me to suggest the next step "
                f"to improve its visibility?"
            )

        return {
            "body": body,
            "cta": "verify_gbp",
            "send_as": "vera",
            "suppression_key": trigger.get(
                "suppression_key",
                ""
            ),
            "rationale": (
                f"GBP verification status checked: "
                f"verified={verified}."
            )
        }

    # DEFAULT
    return {
        "body": "Hi — I have a useful update for your business.",
        "cta": "open_ended",
        "send_as": "vera",
        "suppression_key": trigger.get(
            "suppression_key",
            ""
        ),
        "rationale": (
            "No specific trigger handler matched."
        )
    }
