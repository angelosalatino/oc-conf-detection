#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import configparser
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import requests
import pymongo

from classes.visualiser import ConferenceVisualiser

# Ensure configuration is loaded
if 'config' not in st.session_state:
    st.session_state['config'] = configparser.ConfigParser()
    st.session_state['config'].read('config.ini')

config = st.session_state['config']
vis = ConferenceVisualiser()


def check_page_change(page_name):
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = page_name
    elif st.session_state['current_page'] != page_name:
        st.session_state['current_page'] = page_name
        keys_to_clear = [
            'selected_event_id', 'selected_organiser_key',
            'search_mode', 'search_term',
            'org_search_mode', 'org_search_term',
            'selected_openalex_author', 'openalex_search_query'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]


check_page_change("status")

st.set_page_config(
    layout="wide",
    page_title=f"System Status - {config['APP']['app_acronym']}",
    page_icon="🌐",
)

# Load CSS styles
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()


def mask_key(key: str) -> str:
    if not key or "ADD HERE" in key.upper():
        return "Not configured"
    k = key.strip()
    if len(k) <= 8:
        return "••••"
    return f"{k[:4]}••••{k[-4:]}"


def format_seconds(seconds) -> str:
    try:
        secs = int(float(seconds))
        if secs < 0:
            return "Soon"
        hrs, rem = divmod(secs, 3600)
        mins, _ = divmod(rem, 60)
        if hrs > 0:
            return f"{hrs}h {mins}m"
        return f"{mins}m"
    except Exception:
        return "—"


def check_mongodb(cfg) -> dict:
    storage_type = cfg.get('STORAGE', 'type', fallback='file').split('#')[0].split(';')[0].strip()
    uri = cfg.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
    db_name = cfg.get('MONGODB', 'db_name', fallback='coci')
    dest_folder = cfg.get('FOLDERS', 'destination_folder', fallback='processed_cfps')

    result = {
        "name": "Database (MongoDB)",
        "storage_type": storage_type,
        "uri": uri,
        "db_name": db_name,
        "status": "unknown",
        "latency_ms": None,
        "details": "",
        "events_count": None,
        "index_count": None,
        "mongo_version": None,
        "local_json_count": None,
    }

    # Count local JSON files if folder exists
    local_dir = Path(dest_folder)
    if not local_dir.is_dir():
        alt = Path("service") / dest_folder
        if alt.is_dir():
            local_dir = alt
    if local_dir.is_dir():
        result["local_json_count"] = len(list(local_dir.glob("*.json")))

    if storage_type == "file":
        result["status"] = "disabled"
        result["details"] = f"Storage mode is set to 'file' (MongoDB disabled). Local folder has {result['local_json_count'] or 0} JSON files."
        return result

    t0 = time.perf_counter()
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
        info = client.server_info()
        db = client[db_name]
        events_count = db["events"].count_documents({})
        index_count = db["events_index"].count_documents({})
        latency = round((time.perf_counter() - t0) * 1000)

        result["status"] = "online"
        result["latency_ms"] = latency
        result["mongo_version"] = info.get("version", "unknown")
        result["events_count"] = events_count
        result["index_count"] = index_count
        result["details"] = f"Connected to '{db_name}' (v{result['mongo_version']}) — {events_count} events indexed."
    except Exception as e:
        result["status"] = "offline"
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        result["details"] = f"Connection failed: {e}"

    return result


def check_openalex(cfg) -> dict:
    api_key = cfg.get('OPENALEX', 'openalex_api', fallback='').strip()
    has_key = bool(api_key) and "ADD HERE" not in api_key.upper()
    email = cfg.get('TEAM', 'email', fallback='').strip()

    result = {
        "name": "OpenAlex API",
        "status": "unknown",
        "latency_ms": None,
        "details": "",
        "has_key": has_key,
        "masked_key": mask_key(api_key),
        "credits_limit": None,
        "credits_used": None,
        "credits_remaining": None,
        "reset_seconds": None,
        "raw_rate_limit": None,
    }

    headers = {"User-Agent": f"COCI/2.0 (mailto:{email})" if email else "COCI/2.0"}
    t0 = time.perf_counter()
    try:
        # 1. Query dedicated /rate-limit endpoint if API key is configured
        params = {"api_key": api_key} if has_key else {}
        resp = requests.get("https://api.openalex.org/rate-limit", params=params, headers=headers, timeout=8)
        latency = round((time.perf_counter() - t0) * 1000)
        result["latency_ms"] = latency

        if resp.status_code == 200:
            result["status"] = "online"
            data = resp.json() if resp.content else {}
            result["raw_rate_limit"] = data

            # OpenAlex /rate-limit may nest fields under "rate_limit" or at top level
            rl = data.get("rate_limit", data) if isinstance(data, dict) else {}

            def pick_num(d, *keys):
                for k in keys:
                    if isinstance(d, dict) and d.get(k) is not None:
                        try:
                            return float(d[k])
                        except Exception:
                            pass
                return None

            # Check USD budget fields first (e.g. $1.000 daily budget, $0.934 remaining)
            is_usd = False
            limit = pick_num(rl, "daily_budget_usd")
            used = pick_num(rl, "daily_used_usd")
            remaining = pick_num(rl, "daily_remaining_usd")
            if limit is not None or remaining is not None:
                is_usd = True
            else:
                limit = pick_num(rl, "credits_limit", "daily_limit", "limit")
                used = pick_num(rl, "credits_used", "daily_used", "used")
                remaining = pick_num(rl, "credits_remaining", "daily_remaining", "remaining")

            reset_raw = pick_num(rl, "resets_in_seconds", "reset_in_seconds", "reset")
            reset_s = int(reset_raw) if reset_raw is not None else None

            # Fallback to HTTP rate-limit headers
            if limit is None and resp.headers.get("X-RateLimit-Limit"):
                try:
                    limit = float(resp.headers["X-RateLimit-Limit"])
                except Exception:
                    pass
            if remaining is None and resp.headers.get("X-RateLimit-Remaining"):
                try:
                    remaining = float(resp.headers["X-RateLimit-Remaining"])
                except Exception:
                    pass
            if reset_s is None and resp.headers.get("X-RateLimit-Reset"):
                try:
                    reset_s = int(float(resp.headers["X-RateLimit-Reset"]))
                except Exception:
                    pass

            if limit is not None and remaining is not None and used is None:
                used = max(0.0, limit - remaining)
            elif limit is not None and used is not None and remaining is None:
                remaining = max(0.0, limit - used)

            result["credits_limit"] = limit
            result["credits_used"] = used
            result["credits_remaining"] = remaining
            result["is_usd"] = is_usd
            result["reset_seconds"] = reset_s
            result["details"] = "OpenAlex API is operational."
        else:
            # Fallback ping to /authors?per-page=1 in case /rate-limit requires a key
            resp2 = requests.get(
                "https://api.openalex.org/authors",
                params={**params, "per-page": 1},
                headers=headers,
                timeout=8,
            )
            result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            if resp2.status_code == 200:
                result["status"] = "online"
                if resp2.headers.get("X-RateLimit-Limit"):
                    result["credits_limit"] = float(resp2.headers["X-RateLimit-Limit"])
                if resp2.headers.get("X-RateLimit-Remaining"):
                    result["credits_remaining"] = float(resp2.headers["X-RateLimit-Remaining"])
                if resp2.headers.get("X-RateLimit-Reset"):
                    result["reset_seconds"] = int(float(resp2.headers["X-RateLimit-Reset"]))
                if result["credits_limit"] is not None and result["credits_remaining"] is not None:
                    result["credits_used"] = max(0, result["credits_limit"] - result["credits_remaining"])
                result["details"] = "OpenAlex API is operational (via authors endpoint)."
            elif resp2.status_code == 429:
                result["status"] = "degraded"
                result["details"] = "Rate limit / daily quota reached (HTTP 429)."
            elif resp2.status_code in (401, 403):
                result["status"] = "offline"
                result["details"] = f"Authentication error (HTTP {resp2.status_code}). Check openalex_api in config.ini."
            else:
                result["status"] = "offline"
                result["details"] = f"Unexpected response (HTTP {resp2.status_code})."
    except Exception as e:
        result["status"] = "offline"
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        result["details"] = f"Request failed: {e}"

    return result


def check_llm_api(cfg) -> dict:
    api_url = cfg.get('DEFAULT', 'api_url', fallback='https://openrouter.ai/api/v1').strip().rstrip("/")
    api_key = cfg.get('DEFAULT', 'api_key', fallback='').strip()
    model = cfg.get('DEFAULT', 'model', fallback='openai/gpt-4o').strip()
    has_key = bool(api_key) and "ADD HERE" not in api_key.upper()
    is_openrouter = "openrouter.ai" in api_url.lower()
    provider = "OpenRouter" if is_openrouter else ("OpenAI" if "openai.com" in api_url.lower() else "Custom OpenAI-Compatible")

    result = {
        "name": f"LLM API ({provider})",
        "provider": provider,
        "api_url": api_url,
        "model": model,
        "has_key": has_key,
        "masked_key": mask_key(api_key),
        "status": "unknown",
        "latency_ms": None,
        "details": "",
        "usage": None,
        "limit": None,
        "limit_remaining": None,
        "total_credits": None,
        "total_usage": None,
        "account_remaining": None,
        "key_label": None,
        "is_free_tier": None,
    }

    if not has_key:
        result["status"] = "offline"
        result["details"] = "API key is not configured in config.ini."
        return result

    headers = {"Authorization": f"Bearer {api_key}"}
    t0 = time.perf_counter()
    try:
        if is_openrouter:
            # 1. Standard key info endpoint (works with any OpenRouter API key)
            resp = requests.get(f"{api_url}/key", headers=headers, timeout=8)
            result["latency_ms"] = round((time.perf_counter() - t0) * 1000)

            if resp.status_code == 200:
                result["status"] = "online"
                data = resp.json().get("data", {})
                result["key_label"] = data.get("label")
                result["usage"] = data.get("usage")
                result["limit"] = data.get("limit")
                result["limit_remaining"] = data.get("limit_remaining")
                result["is_free_tier"] = data.get("is_free_tier")
                result["details"] = "OpenRouter API key is valid and active."

                # 2. Try account-level credits endpoint (returns total_credits & total_usage if permitted)
                try:
                    c_resp = requests.get(f"{api_url}/credits", headers=headers, timeout=6)
                    if c_resp.status_code == 200:
                        c_data = c_resp.json().get("data", {})
                        tot_c = c_data.get("total_credits")
                        tot_u = c_data.get("total_usage")
                        if tot_c is not None and tot_u is not None:
                            result["total_credits"] = float(tot_c)
                            result["total_usage"] = float(tot_u)
                            result["account_remaining"] = max(0.0, float(tot_c) - float(tot_u))
                except Exception:
                    pass
            elif resp.status_code in (401, 403):
                result["status"] = "offline"
                result["details"] = f"Invalid or unauthorized API key (HTTP {resp.status_code})."
            else:
                result["status"] = "degraded"
                result["details"] = f"Unexpected response (HTTP {resp.status_code})."
        else:
            # OpenAI or compatible provider: ping /models to verify auth and connectivity
            resp = requests.get(f"{api_url}/models", headers=headers, timeout=8)
            result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            if resp.status_code == 200:
                result["status"] = "online"
                result["details"] = f"{provider} API is reachable and key is valid. (Billing balance is managed in the provider dashboard.)"
            elif resp.status_code in (401, 403):
                result["status"] = "offline"
                result["details"] = f"Authentication failed (HTTP {resp.status_code}). Check api_key in config.ini."
            elif resp.status_code == 429:
                result["status"] = "degraded"
                result["details"] = "Rate limit or quota exceeded (HTTP 429)."
            else:
                result["status"] = "offline"
                result["details"] = f"Unexpected response (HTTP {resp.status_code})."
    except Exception as e:
        result["status"] = "offline"
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        result["details"] = f"Request failed: {e}"

    return result


def check_pubpeer() -> dict:
    result = {
        "name": "PubPeer API",
        "status": "unknown",
        "latency_ms": None,
        "details": "",
    }
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            "https://pubpeer.com/v3/publications",
            json={"dois": ["10.1038/nature12373"], "devkey": "Zotero"},
            timeout=8,
        )
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        if resp.status_code == 200:
            result["status"] = "online"
            result["details"] = "PubPeer v3 publications endpoint is operational."
        else:
            result["status"] = "degraded" if resp.status_code < 500 else "offline"
            result["details"] = f"Returned HTTP {resp.status_code}."
    except Exception as e:
        result["status"] = "offline"
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        result["details"] = f"Request failed: {e}"
    return result


def check_retraction_watch() -> dict:
    result = {
        "name": "Retraction Watch (Crossref API)",
        "status": "unknown",
        "latency_ms": None,
        "details": "",
        "total_retractions": None,
    }
    t0 = time.perf_counter()
    try:
        resp = requests.get(
            "https://api.crossref.org/v1/works",
            params={"filter": "update-type:retraction", "rows": 1},
            timeout=8,
        )
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        if resp.status_code == 200:
            total = resp.json().get("message", {}).get("total-results")
            result["status"] = "online"
            result["total_retractions"] = total
            total_str = f" ({total:,} retraction records indexed)" if isinstance(total, int) else ""
            result["details"] = f"Crossref retraction feed is operational{total_str}."
        else:
            result["status"] = "degraded" if resp.status_code < 500 else "offline"
            result["details"] = f"Returned HTTP {resp.status_code}."
    except Exception as e:
        result["status"] = "offline"
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        result["details"] = f"Request failed: {e}"
    return result


def render_status_badge(status: str) -> str:
    if status == "online":
        return "🟢 **Operational**"
    elif status == "degraded":
        return "🟡 **Degraded / Limited**"
    elif status == "disabled":
        return "⚪ **Disabled**"
    return "🔴 **Offline / Error**"


# ----------------- PAGE LAYOUT -----------------
st.markdown("<div id='top' style='height: 40px;'></div>", unsafe_allow_html=True)

head_col, btn_col = st.columns([4, 1], vertical_alignment="bottom")
with head_col:
    st.title("System Status")
    st.markdown("Live health checks for COCI's database, external scholarly APIs, and API credit / quota balances.")
with btn_col:
    if st.button("🔄 Refresh Status", type="primary", width="stretch"):
        st.rerun()

# Run all checks
with st.spinner("Checking system services and API quotas..."):
    mongo_res = check_mongodb(config)
    openalex_res = check_openalex(config)
    llm_res = check_llm_api(config)
    pubpeer_res = check_pubpeer()
    rw_res = check_retraction_watch()

checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# Overall Banner
all_services = [mongo_res, openalex_res, llm_res, pubpeer_res, rw_res]
active_services = [s for s in all_services if s["status"] != "disabled"]
offline_count = sum(1 for s in active_services if s["status"] == "offline")
degraded_count = sum(1 for s in active_services if s["status"] == "degraded")

if offline_count == 0 and degraded_count == 0:
    st.success(f"✅ **All Systems Operational** — Checked at {checked_at}")
elif offline_count == 0:
    st.warning(f"⚠️ **Partial Degradation** ({degraded_count} service limited) — Checked at {checked_at}")
else:
    st.error(f"🚨 **Service Disruption** ({offline_count} offline, {degraded_count} degraded) — Checked at {checked_at}")

st.divider()

# ----------------- 1. SERVICE HEALTH CARDS -----------------
st.subheader("📡 Service Connectivity")

row1 = st.columns(3)
row2 = st.columns(2)
cards = [
    (row1[0], mongo_res),
    (row1[1], openalex_res),
    (row1[2], llm_res),
    (row2[0], pubpeer_res),
    (row2[1], rw_res),
]

for col, svc in cards:
    with col:
        with st.container(border=True):
            st.markdown(f"#### {svc['name']}")
            latency_str = f" &nbsp;•&nbsp; ⏱️ `{svc['latency_ms']} ms`" if svc.get("latency_ms") is not None else ""
            st.markdown(f"{render_status_badge(svc['status'])}{latency_str}")
            st.caption(svc["details"])

st.divider()

# ----------------- 2. API QUOTAS & CREDITS -----------------
st.subheader("💳 API Quotas & Credits")

q_col1, q_col2 = st.columns(2)

# OpenAlex Quota Card
with q_col1:
    with st.container(border=True):
        st.markdown("#### 🔬 OpenAlex Daily Quota")
        st.caption(f"API Key: `{openalex_res['masked_key']}`")

        limit = openalex_res["credits_limit"]
        used = openalex_res["credits_used"]
        remaining = openalex_res["credits_remaining"]
        reset_s = openalex_res["reset_seconds"]

        if limit is not None and remaining is not None:
            is_usd = openalex_res.get("is_usd") or (float(limit) <= 100.0)
            fmt = (lambda v: f"${float(v):,.3f}" if is_usd else f"{int(v):,}")

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Remaining", fmt(remaining))
            with m2:
                st.metric("Used Today", fmt(used) if used is not None else "—")
            with m3:
                st.metric("Daily Limit", fmt(limit))

            if limit > 0:
                pct_remaining = max(0.0, min(1.0, float(remaining) / float(limit)))
                st.progress(pct_remaining, text=f"{pct_remaining * 100:.1f}% of daily quota remaining")

            if reset_s is not None:
                st.caption(f"🕒 Quota resets in **{format_seconds(reset_s)}** (midnight UTC)")
        elif openalex_res["status"] == "online":
            st.info("OpenAlex is online, but detailed quota headers were not returned for this key.")
            if openalex_res["raw_rate_limit"]:
                with st.expander("Raw `/rate-limit` response"):
                    st.json(openalex_res["raw_rate_limit"])
        else:
            st.warning("Unable to retrieve OpenAlex quota while the API is unreachable or unauthorized.")

# LLM API Credits Card
with q_col2:
    with st.container(border=True):
        st.markdown(f"#### 🤖 {llm_res['provider']} API Credits")
        st.caption(f"Model: `{llm_res['model']}` &nbsp;•&nbsp; API Key: `{llm_res['masked_key']}`")

        if llm_res["status"] == "online" and llm_res["provider"] == "OpenRouter":
            if llm_res["account_remaining"] is not None:
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Remaining Credits", f"${llm_res['account_remaining']:,.2f}")
                with m2:
                    st.metric("Total Used", f"${llm_res['total_usage']:,.2f}")
                with m3:
                    st.metric("Total Purchased", f"${llm_res['total_credits']:,.2f}")
                if llm_res["total_credits"] > 0:
                    pct_rem = max(0.0, min(1.0, llm_res["account_remaining"] / llm_res["total_credits"]))
                    st.progress(pct_rem, text=f"{pct_rem * 100:.1f}% of account credits remaining")
            else:
                m1, m2, m3 = st.columns(3)
                with m1:
                    rem_str = f"${llm_res['limit_remaining']:,.4f}" if llm_res["limit_remaining"] is not None else "Unlimited"
                    st.metric("Key Remaining", rem_str)
                with m2:
                    use_str = f"${llm_res['usage']:,.4f}" if llm_res["usage"] is not None else "—"
                    st.metric("Key Used", use_str)
                with m3:
                    lim_str = f"${llm_res['limit']:,.2f}" if llm_res["limit"] is not None else "No Cap"
                    st.metric("Key Limit", lim_str)

                if llm_res["limit"] is not None and llm_res["limit"] > 0 and llm_res["limit_remaining"] is not None:
                    pct_rem = max(0.0, min(1.0, float(llm_res["limit_remaining"]) / float(llm_res["limit"])))
                    st.progress(pct_rem, text=f"{pct_rem * 100:.1f}% of key spending limit remaining")

            meta_parts = []
            if llm_res["key_label"]:
                meta_parts.append(f"Key label: **{llm_res['key_label']}**")
            if llm_res["is_free_tier"] is not None:
                meta_parts.append("Tier: **Free**" if llm_res["is_free_tier"] else "Tier: **Paid**")
            if meta_parts:
                st.caption(" &nbsp;•&nbsp; ".join(meta_parts))
        elif llm_res["status"] == "online":
            st.info(
                f"**{llm_res['provider']}** API key is valid and connected (`{llm_res['api_url']}`). "
                "OpenAI does not expose billing balances via standard API keys — check your balance in the "
                "[OpenAI Billing Dashboard](https://platform.openai.com/settings/organization/billing/overview)."
            )
        else:
            st.warning(llm_res["details"])

st.write("")
vis.render_footer()
