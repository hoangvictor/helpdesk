# Copyright (c) 2026
# For license information, please see license.txt
#
# Place this file at:  helpdesk/api/agent_conversation.py
#
# It exposes a single whitelisted endpoint that the Helpdesk frontend calls.
# The frontend NEVER talks to your agent API directly, because:
#   1. Browsers would block it with CORS.
#   2. The Bearer api_key would be exposed in client-side JS to anyone.
# This server-side proxy solves both: the key stays on the server.

import os

import frappe
import requests


# ---------------------------------------------------------------------------
# CONFIG -- the two values you need to control. Adjust these to your setup.
# ---------------------------------------------------------------------------

# Base URL of your custom agent service (no trailing slash).
AGENT_API_BASE = "http://api:5001"


def _get_agent_api_base() -> str:
    """
    Read the agent API base URL from site_config.json so it can be different
    per environment (dev, staging, production). Add this to your site's
    site_config.json:

        "agent_api_base": "http://localhost:5001"

    (file: sites/<your-site>/site_config.json)
    """
    agent_api_base = frappe.conf.get("agent_api_base", AGENT_API_BASE)
    if not agent_api_base:
        return os.environ.get("AGENT_API_BASE", AGENT_API_BASE)  # fallback to env var for safety
    return agent_api_base.rstrip("/")  # ensure no trailing slash


def _get_api_key() -> str:
    """
    Read the Bearer key from site_config.json so it never lives in code or
    in the browser. Add this to your site's site_config.json:

        "agent_api_key": "your-real-key-here"

    (file: sites/<your-site>/site_config.json)
    """
    key = frappe.conf.get("agent_api_key")
    if not key:
        return os.environ.get("AGENT_API_KEY", "no-key-set")  # fallback to env var for safety
    return key


@frappe.whitelist()
def get_messages(conversation_id: str, user_id: str):
    """
    Called by the frontend as:
        /api/method/helpdesk.api.agent_conversation.get_messages
            ?conversation_id=<uuid>&ticket=<ticket_name>

    Proxies to your agent:
        GET {AGENT_API_BASE}/v1/messages?user=<user>&conversation_id=<uuid>
        Authorization: Bearer <api_key>

    Returns the parsed JSON body from your agent unchanged, so the Vue side
    can shape it however your agent responds.
    """
    if not conversation_id:
        frappe.throw("conversation_id is required")

    try:
        resp = requests.get(
            f"{_get_agent_api_base()}/v1/messages",
            params={"user": user_id, "conversation_id": conversation_id},
            headers={"Authorization": f"Bearer {_get_api_key()}"},
            timeout=20,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        frappe.log_error(frappe.get_traceback(), "Agent conversation fetch failed")
        frappe.throw(f"Could not reach agent service: {e}")

    try:
        return resp.json()
    except ValueError:
        # Agent returned non-JSON; hand back raw text so it's still visible.
        return {"raw": resp.text}