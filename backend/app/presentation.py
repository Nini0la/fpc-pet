"""Natural confirmations from validated domain outcomes; technical receipts remain in trace."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo


def confirmation(result):
    if result.get("status") == "rejected":
        return (
            {
                "write_permission_required": "I need your permission to save or change that.",
                "version_conflict": "That changed since I last checked. Please let me refresh it.",
            }.get(result.get("reason"))
            or result.get("question")
            or "I couldn't make that change. What should I change?"
        )
    if result.get("kind") == "proposal":
        effect = result.get("execution")
        if effect and effect.get("status") in {"saved", "updated"}:
            return confirmation(effect)
        state = result.get("context", {}).get("state")
        if state in {"paused", "cancelled"}:
            return f"I've {state} that proposed change."
        if state == "needs_clarification":
            question = result.get("question") or (
                "I've kept that request. What details should I use?")
            return f"For “{result.get('context', {}).get('title', 'that request')}”: {question}"
        if effect and effect.get("status") == "rejected":
            return confirmation(effect)
        details = result.get("context", {})
        if details.get("tool_name") == "create_commitment":
            title = details.get("arguments", {}).get("title", details.get("title", "that plan"))
            return f"Would you like me to save “{title}” as a commitment?"
        return "I've kept that suggestion for you to confirm; it hasn't been carried out."
    if result.get("kind") == "commitment":
        item = result["context"]
        if result.get("already_completed"):
            return (f"“{item['title']}” is already recorded as completed. "
                    "No new completion was added.")
        action = result.get("action")
        verb = {
            "complete": "Completed",
            "cancel": "Cancelled",
            "pause": "Paused",
            "resume": "Resumed",
            "reopen": "Reopened",
        }.get(action, "Saved" if result["status"] == "saved" else "Updated")
        answer = (f"Marked “{item['title']}” as completed." if action == "complete"
                  else f"{verb} “{item['title']}”.")
        if action == "complete" and (item.get("completion_report") or {}).get("timing_text"):
            report = item["completion_report"]
            answer += f" You reported finishing it “{report['timing_text']}”."
        elif item.get("due_at") and item["state"] in {"open", "in_progress", "waiting"}:
            answer += " " + item["deadline_display"].rstrip(".") + "."
        if item.get("next_action") and item["state"] in {"open", "in_progress", "waiting"}:
            answer += f" Next step: {item['next_action'].rstrip('.')}."
        status = item.get("monitoring_status", "saved_only")
        if status == "scheduled":
            when = datetime.fromisoformat(item["next_check_local"]).astimezone(
                ZoneInfo(item["timezone"])
            )
            answer += f" Your next check-in is {when.strftime('%d %b %Y at %H:%M %Z')}."
        else:
            answer += " " + {
                "checkins_disabled": "Automatic check-ins are disabled in your settings.",
                "paused": "Check-ins are paused.",
                "closed": "No further check-ins are scheduled.",
                "limit_reached": "The agreed check-ins are finished; no more are scheduled.",
                "deadline_unclear": "The deadline needs clarification before check-ins can run.",
            }.get(status, "No automatic check-in is scheduled yet.")
        if result.get("followup_question"):
            answer += " " + result["followup_question"]
        return answer
    if result.get("kind") == "reminder":
        plan = result["context"]
        if plan["state"] != "active":
            return f"Your reminder to {plan['topic']} is {plan['state']}."
        when = (
            datetime.fromisoformat(plan["next_due_at"]).astimezone(ZoneInfo(plan["timezone"]))
            if plan.get("next_due_at")
            else None
        )
        timing = (
            f"Next: {when.strftime('%Y-%m-%d %H:%M:%S %Z')}."
            if when
            else "No check-in is scheduled."
        )
        if plan["mode"] == "once":
            return f"I'll remind you once to {plan['topic']}. {timing}"
        interval = plan["interval_seconds"]
        cadence = f"{interval // 60} minutes" if interval % 60 == 0 else f"{interval} seconds"
        remaining = plan["max_occurrences"] - plan["occurrences"]
        return f"Check-ins for {plan['topic']} every {cadence}, {remaining} remaining. {timing}"
    if result.get("kind") == "workflow":
        context = result.get("context", {})
        kind = context.get("activity") or result.get("transition", {}).get("type")
        action = context.get("action")
        if action == "start" and context.get("started") is False:
            return f"Your {kind} is already {context.get('state', 'available')}."
        if action in {"pause", "resume", "cancel"}:
            verb = {"pause": "paused", "resume": "resumed", "cancel": "cancelled"}[action]
            return f"I've {verb} your {kind} activity."
        if kind == "reflection" and context.get("journal_id"):
            verb = "corrected" if action == "correct" else "added that to"
            return f"I've {verb} your reflection for {context['local_date']}."
        if kind == "vocabulary" and action in {"respond", "correct"}:
            return (
                f"I've recorded your vocabulary response for “{context.get('word', 'that word')}”."
            )
        return (
            context.get("prompt") or "Your reflection is ready."
            if kind == "reflection"
            else "Your vocabulary practice is ready."
        )
    if result.get("status") == "read":
        records = result.get("context", {}).get("commitments")
        if records is not None:
            if not records:
                return (
                    "I don't have a matching saved commitment. "
                    "That doesn't mean you never mentioned it."
                )
            lines = ["Your saved commitments:"]
            for item in records:
                line = (
                    f"• {recorded_title(item)} — "
                    f"{item.get('deadline_display', 'Deadline not confirmed.')}"
                )
                if item.get("next_action"):
                    line += f" Next: {item['next_action']}."
                lines.append(line)
            if result.get("has_more"):
                lines.append("There are more; which would you like to look at next?")
            return "\n".join(lines)
        return "I've checked the available context."
    if result.get("kind") == "responsibility":
        return "I've drafted that plan. Review it in Today before any contact is authorized."
    verb = "Saved" if result.get("status") == "saved" else "Updated"
    return f"{verb} your {result.get('kind', 'request')}."


def recorded_title(item):
    title = item["title"]
    if item.get("title_recorded_at") and re.search(
        r"\b(today|tomorrow|tonight|yesterday|next\s+\w+)\b", title, re.I
    ):
        day = datetime.fromisoformat(item["title_recorded_at"]).astimezone(
            ZoneInfo(item.get("timezone", "UTC"))
        ).strftime("%d %b %Y")
        return f"“{title}” (wording recorded {day})"
    return title


def for_wording(value):
    if isinstance(value, list):
        return [for_wording(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        key: for_wording(item)
        for key, item in value.items()
        if key not in {"id", "version", "source_message_ids", "transition", "derivation"}
        and not key.endswith("_id")
    }


def identifiers(value):
    if isinstance(value, list):
        return set().union(*(identifiers(item) for item in value))
    if not isinstance(value, dict):
        return set()
    found = {
        item
        for key, item in value.items()
        if (key == "id" or key.endswith("_id")) and isinstance(item, str) and len(item) >= 16
    }
    return found | set().union(*(identifiers(item) for item in value.values()))


def context_explanation(context):
    """Fallback for a response that exposes internal metadata instead of explaining evidence."""
    mentions = context.get("conversation_mentions", [])
    if mentions:
        return (
            f"In an earlier message you said: “{mentions[0]['content']}” "
            "This is conversation history, not proof of a saved task or reminder."
        )
    for operation in context.get("recent_operations", []):
        for outcome in operation.get("operation_outcomes", []):
            current = outcome.get("current_record") or {}
            if outcome.get("status") not in {"saved", "updated"}:
                continue
            if current.get("activity") == "reflection":
                return f"I recorded an evening reflection for {current['local_date']}." + (
                    f" It currently says: “{current['current_reflection']}”"
                    if current.get("current_reflection")
                    else ""
                )
            if current.get("title"):
                return (
                    f"The recorded change concerned “{current['title']}”. "
                    f"Its current state is {current['state']}."
                )
    return (
        "Your message is in our conversation, but I can't verify "
        "a separate saved change from the available evidence."
    )
