"""Whoop sleep provider.

Auth: OAuth 2.0 authorization-code with PKCE. Whoop's developer portal
requires registering an app (https://developer.whoop.com/) and setting a
redirect URI. For a local CLI the convention is `http://localhost:<port>/callback`
— this module spins up a one-shot http.server during `connect`, captures
the code, exchanges it for tokens, and stores them at ~/.burnout-guard/auth/whoop.json.

Endpoint: GET /developer/v1/cycle (recent cycles) + /developer/v1/activity/sleep
(per-sleep details). We use the cycle's `score.sleep_performance_percentage`
as quality (0-100, matches our axis directly).

Stdlib only — urllib + http.server + secrets + hashlib for PKCE.

To set this up, the user registers an app once:
  1. https://developer.whoop.com/ → "Create app"
  2. Redirect URI: http://localhost:8765/callback
  3. Scopes: read:sleep read:cycles offline
  4. Run: burnout.py sleep connect whoop --client-id <id> --client-secret <secret>
  5. Browser opens, log into Whoop, approve.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import date as date_cls, datetime, timedelta, timezone
from typing import Optional

from .base import AUTH_DIR, SleepRecord, _read_json, _write_json, cache_get, cache_put


NAME = "whoop"
TOKEN_FILE = AUTH_DIR / "whoop.json"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
API_BASE = "https://api.prod.whoop.com/developer/v1"
DEFAULT_PORT = 8765
DEFAULT_SCOPES = "read:sleep read:cycles offline"
TIMEOUT_S = 10


# ---------------------------------------------------------------- token store

def _load_tokens() -> dict:
    return _read_json(TOKEN_FILE)


def _save_tokens(t: dict) -> None:
    _write_json(TOKEN_FILE, t)


def _is_expired(t: dict) -> bool:
    exp = t.get("expires_at", 0)
    return time.time() >= exp - 30


# ---------------------------------------------------------------- OAuth flow

def connect(client_id: str, client_secret: str, port: int = DEFAULT_PORT) -> dict:
    """Run the one-shot OAuth flow. Blocks until the user completes the
    browser step or the server times out. Returns the token dict."""
    redirect_uri = f"http://localhost:{port}/callback"
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": DEFAULT_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{AUTH_URL}?{params}"
    received: dict = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404); self.end_headers(); return
            q = urllib.parse.parse_qs(parsed.query)
            if q.get("state", [""])[0] != state:
                self.send_response(400); self.end_headers()
                self.wfile.write(b"State mismatch")
                received["error"] = "state mismatch"
                return
            received["code"] = q.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Burnout Guard connected to Whoop.</h2>"
                             b"<p>You can close this tab.</p>")

        def log_message(self, *a, **kw):  # silence default stderr noise
            pass

    server = http.server.HTTPServer(("localhost", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    webbrowser.open(auth_url)
    print(f"Open this URL if the browser didn't pop:\n  {auth_url}")
    deadline = time.time() + 300  # 5-minute wait
    while "code" not in received and "error" not in received and time.time() < deadline:
        time.sleep(0.25)
    server.shutdown()
    if "error" in received or "code" not in received:
        raise RuntimeError(f"OAuth flow failed: {received.get('error', 'timeout')}")

    tokens = _exchange_code(client_id, client_secret, received["code"],
                            redirect_uri, verifier)
    tokens["client_id"] = client_id
    tokens["client_secret"] = client_secret
    _save_tokens(tokens)
    return tokens


def _exchange_code(client_id: str, client_secret: str, code: str,
                   redirect_uri: str, verifier: str) -> dict:
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": verifier,
    }).encode()
    return _token_request(body)


def _refresh(t: dict) -> Optional[dict]:
    refresh = t.get("refresh_token")
    if not refresh or not t.get("client_id"):
        return None
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": t["client_id"],
        "client_secret": t.get("client_secret", ""),
        "scope": DEFAULT_SCOPES,
    }).encode()
    try:
        new = _token_request(body)
    except RuntimeError:
        return None
    new["client_id"] = t["client_id"]
    new["client_secret"] = t.get("client_secret", "")
    _save_tokens(new)
    return new


def _token_request(body: bytes) -> dict:
    req = urllib.request.Request(TOKEN_URL, data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        raise RuntimeError(f"whoop token request failed: {e}") from e
    if "access_token" not in data:
        raise RuntimeError(f"whoop token response missing access_token: {data}")
    data["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
    return data


# ---------------------------------------------------------------- fetch

def fetch(target: date_cls) -> Optional[SleepRecord]:
    day = target.isoformat()
    cached = cache_get(NAME, day)
    if cached:
        return cached
    tokens = _load_tokens()
    if not tokens.get("access_token"):
        return None
    if _is_expired(tokens):
        tokens = _refresh(tokens) or tokens
        if _is_expired(tokens):
            return None
    rec = _fetch_live(target, tokens["access_token"])
    cache_put(NAME, day, rec)
    return rec


def _fetch_live(target: date_cls, token: str) -> Optional[SleepRecord]:
    # Whoop cycles wrap a sleep + day. Pull cycles whose end overlaps `target`.
    start_dt = datetime.combine(target - timedelta(days=1),
                                datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(target + timedelta(days=1),
                              datetime.min.time(), tzinfo=timezone.utc)
    q = urllib.parse.urlencode({
        "start": start_dt.isoformat().replace("+00:00", "Z"),
        "end": end_dt.isoformat().replace("+00:00", "Z"),
        "limit": 5,
    })
    cycles = _api_get(f"/cycle?{q}", token)
    if not cycles:
        return None
    chosen = None
    for c in cycles:
        end_iso = c.get("end")
        if not end_iso:
            continue
        try:
            end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        except ValueError:
            continue
        if end.date() == target:
            chosen = c
            break
    if not chosen:
        return None

    # Sleep detail by cycle id
    cycle_id = chosen.get("id")
    sleep = _api_get(f"/activity/sleep?cycle_id={cycle_id}&limit=1", token)
    if not sleep:
        return None
    s = sleep[0]
    stage = s.get("score", {}).get("stage_summary", {}) or {}
    in_bed_ms = stage.get("total_in_bed_time_milli", 0)
    awake_ms = stage.get("total_awake_time_milli", 0)
    hours = max(0.0, (in_bed_ms - awake_ms) / 3_600_000.0)
    if hours <= 0:
        return None
    quality_pct = s.get("score", {}).get("sleep_performance_percentage")
    quality = float(quality_pct) if quality_pct is not None else 65.0

    return SleepRecord(date=target.isoformat(), hours=round(hours, 2),
                       quality=round(quality, 1), source=NAME)


def _api_get(path: str, token: str) -> Optional[list]:
    req = urllib.request.Request(API_BASE + path,
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return data["records"]
    if isinstance(data, list):
        return data
    return None
