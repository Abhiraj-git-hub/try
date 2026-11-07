"""Consent-based Android browser diagnostics collector.

This app does NOT remotely control Android, inspect installed apps/accounts,
read messages/files, or bypass Android permissions. It only stores a small
browser/device report after the visitor explicitly consents and submits it.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_file, url_for

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", str(APP_DIR / "reports.sqlite3")))
REPORT_TOKEN = os.environ.get("REPORT_TOKEN", "")
DASHBOARD_TOKEN = os.environ.get("DASHBOARD_TOKEN", "")
AGENT_APK_PATH = Path(os.environ.get("AGENT_APK_PATH", str(APP_DIR / "downloads" / "android-remote-support.apk")))

if not REPORT_TOKEN:
    REPORT_TOKEN = secrets.token_urlsafe(24)
if not DASHBOARD_TOKEN:
    DASHBOARD_TOKEN = secrets.token_urlsafe(32)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 24 * 1024  # limit incoming JSON to 24 KB

PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>Android Remote Support — Install</title>
  <style>
    :root { color-scheme: light dark; --bg:#101827; --panel:#182438; --text:#edf3fc; --muted:#aab8cc; --line:#33445e; --accent:#72a7ff; --warning:#f3c969; }
    * { box-sizing:border-box; }
    body { margin:0; padding:24px 14px; background:var(--bg); color:var(--text); font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
    main { max-width:720px; margin:0 auto; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:22px; margin:14px 0; }
    h1 { margin:0 0 8px; font-size:1.55rem; }
    h2 { margin:0 0 10px; font-size:1.1rem; }
    p { margin:8px 0; }
    .muted { color:var(--muted); }
    .notice { border-left:4px solid var(--accent); padding:10px 12px; background:#24344c; border-radius:8px; }
    .warning { border-left:4px solid var(--warning); padding:10px 12px; background:#3a3324; border-radius:8px; }
    ul { padding-left:22px; }
    button { width:100%; border:0; border-radius:10px; padding:14px 16px; background:var(--accent); color:#081426; font-weight:700; font-size:1rem; cursor:pointer; margin-top:12px; }
    button:disabled { opacity:.55; cursor:not-allowed; }
    .check { display:flex; gap:10px; align-items:flex-start; margin-top:16px; }
    .check input { margin-top:5px; transform:scale(1.2); }
    #status { white-space:pre-wrap; overflow-wrap:anywhere; }
    .small { font-size:.88rem; }
  </style>
</head>
<body>
<main>
  <section class="card">
    <h1>Android Remote Support</h1>
    <p class="muted">Download the clearly identified Android support app to set up an authorised support session with your computer.</p>
    <div class="notice">
      <strong>Before installing:</strong> This page only offers an APK download. It cannot silently install the app or grant Android permissions. Android will show its own installation and permission prompts.
    </div>
  </section>
  <section class="card">
    <h2>What the support app is designed to do</h2>
    <ul>
      <li>Connect to a paired PC dashboard using an authenticated, encrypted session.</li>
      <li>Share the phone screen only after Android's screen-capture approval.</li>
      <li>Offer remote interaction only after the user explicitly enables the required Android accessibility permission.</li>
      <li>Show a visible app identity and a clear way to disconnect or revoke access.</li>
    </ul>
    <h2>What installation does not do</h2>
    <ul>
      <li>It does not silently read email, messages, contacts, passwords or other apps' private data.</li>
      <li>It does not hide its app icon or disguise itself as another application.</li>
      <li>It does not silently enable Accessibility, screen sharing or device administrator access.</li>
      <li>It does not bypass Android's installer or permission controls.</li>
    </ul>
    <div class="warning small"><strong>Android approval required:</strong> After downloading, Android may ask you to allow installation from this browser. You must then confirm installation and separately approve any requested support permissions. A touchscreen that cannot respond may prevent these steps unless an already-authorised input method is available.</div>
    <label class="check">
      <input id="consent" type="checkbox">
      <span>I understand that this downloads a visible remote-support app, that Android will ask me to approve installation and permissions, and that an active support session must remain visible and can be disconnected.</span>
    </label>
    <button id="install" disabled>Install Android support app</button>
    <p id="status" class="small muted" role="status" aria-live="polite"></p>
  </section>
  <section class="card small muted">
    <strong>Availability:</strong> The APK must be built, signed and uploaded by the project owner before this button can deliver it. If it is not yet available, this page will say so. Do not install APKs from unknown sources or share account passwords or one-time codes.
  </section>
</main>
<script>
(() => {
  const consent = document.getElementById('consent');
  const install = document.getElementById('install');
  const status = document.getElementById('status');
  consent.addEventListener('change', () => { install.disabled = !consent.checked; });
  install.addEventListener('click', () => {
    if (!consent.checked) return;
    install.disabled = true;
    status.textContent = 'Checking whether the signed Android APK is available…';
    window.location.assign(location.pathname + '/install');
  });
})();
</script>
</body>
</html>'''

DASHBOARD = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Diagnostic dashboard</title>
<style>
body{margin:0;padding:24px 14px;background:#101827;color:#edf3fc;font:15px/1.5 system-ui,sans-serif}main{max-width:1100px;margin:auto}.card{background:#182438;border:1px solid #33445e;border-radius:14px;padding:18px;margin:14px 0}h1{margin-top:0}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid #33445e;overflow-wrap:anywhere}th{width:220px;color:#aab8cc}.muted{color:#aab8cc}.button{padding:10px 14px;border:0;border-radius:8px;background:#72a7ff;color:#081426;font-weight:700;cursor:pointer}a{color:#72a7ff}.report{margin-top:12px;padding-top:12px;border-top:1px solid #33445e}code{overflow-wrap:anywhere}
</style></head><body><main>
<div class="card"><h1>Android browser diagnostics</h1><p class="muted">Reports appear only after the visitor explicitly consents and submits them. This dashboard does not provide phone control.</p>
<p><strong>Diagnostic link to share:</strong><br><code>{{ diagnostic_url }}</code></p>
<button class="button" onclick="navigator.clipboard.writeText({{ diagnostic_url|tojson }})">Copy diagnostic link</button>
<form method="post" action="{{ url_for('clear_reports', token=dashboard_token) }}" onsubmit="return confirm('Permanently delete all collected diagnostic reports?')" style="display:inline-block;margin-left:8px"><button class="button" type="submit">Delete all reports</button></form>
</div>
{% if reports %}
{% for r in reports %}<section class="card report"><h2>Report #{{ r['id'] }}</h2><p class="muted">Received: {{ r['created_utc'] }}</p>
<table>
{% for label, value in r['fields'].items() %}<tr><th>{{ label }}</th><td>{{ value if value is not none else 'Not exposed by browser' }}</td></tr>{% endfor %}
</table></section>{% endfor %}
{% else %}<section class="card"><p>No reports received yet.</p></section>{% endif %}
</main></body></html>'''


def db_connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_utc TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )""")


@app.get("/")
def home():
    return "Diagnostic service is running. Use the private diagnostic link provided in the dashboard URL." 


@app.get("/d/<token>")
def diagnostic_page(token: str):
    if not secrets.compare_digest(token, REPORT_TOKEN):
        abort(404)
    return render_template_string(PAGE)


@app.get("/d/<token>/install")
def download_agent(token: str):
    if not secrets.compare_digest(token, REPORT_TOKEN):
        abort(404)
    if not AGENT_APK_PATH.is_file():
        return render_template_string(
            """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>App not available yet</title><body style="font:16px system-ui;max-width:640px;margin:48px auto;padding:0 18px;background:#101827;color:#edf3fc"><h1>Android app not available yet</h1><p>The installation page is ready, but the signed APK has not been uploaded to the server.</p><p>No app was installed and no device permissions were changed. Return to the support page later or contact the project owner.</p></body></html>""",
            503,
        )
    return send_file(
        AGENT_APK_PATH,
        mimetype="application/vnd.android.package-archive",
        as_attachment=True,
        download_name="android-remote-support.apk",
        max_age=0,
    )


@app.post("/d/<token>/submit")
def submit_report(token: str):
    if not secrets.compare_digest(token, REPORT_TOKEN):
        abort(404)
    if not request.is_json:
        return jsonify(error="JSON report required"), 415
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Invalid report"), 400

    # Allow-list fields. Never store arbitrary submitted properties.
    allowed = {
        "publicIp", "ipLookupStatus", "userAgent", "platform", "browserMobileHint",
        "language", "languages", "timezone", "screen", "viewport", "online",
        "connection", "hardwareConcurrency", "deviceMemoryGb", "maxTouchPoints",
        "cookiesEnabled", "submittedAtClient"
    }
    clean = {key: payload.get(key) for key in allowed if key in payload}
    # Bound strings and nested JSON size to keep reports small.
    for key, value in list(clean.items()):
        if isinstance(value, str):
            clean[key] = value[:1200]
    if len(json.dumps(clean, ensure_ascii=False)) > 12000:
        return jsonify(error="Report is too large"), 413

    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_connect() as conn:
        cursor = conn.execute(
            "INSERT INTO reports (created_utc, payload_json) VALUES (?, ?)",
            (created, json.dumps(clean, ensure_ascii=False))
        )
        report_id = cursor.lastrowid
    return jsonify(ok=True, reportId=report_id)


def format_fields(payload: dict[str, Any]) -> dict[str, Any]:
    labels = [
        ("Public IP (if lookup succeeded)", "publicIp"),
        ("IP lookup status", "ipLookupStatus"),
        ("Browser user-agent", "userAgent"),
        ("Browser platform hint", "platform"),
        ("Mobile browser hint", "browserMobileHint"),
        ("Language", "language"),
        ("Other languages", "languages"),
        ("Timezone", "timezone"),
        ("Screen details", "screen"),
        ("Browser viewport", "viewport"),
        ("Browser online flag", "online"),
        ("Network hints (if exposed)", "connection"),
        ("Reported CPU cores", "hardwareConcurrency"),
        ("Reported device memory (GB)", "deviceMemoryGb"),
        ("Maximum touch points", "maxTouchPoints"),
        ("Cookies enabled flag (not cookie contents)", "cookiesEnabled"),
        ("Client submission time", "submittedAtClient"),
    ]
    result: dict[str, Any] = {}
    for label, key in labels:
        value = payload.get(key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        result[label] = value
    return result


@app.get("/dashboard/<token>")
def dashboard(token: str):
    if not secrets.compare_digest(token, DASHBOARD_TOKEN):
        abort(404)
    with db_connect() as conn:
        rows = conn.execute("SELECT id, created_utc, payload_json FROM reports ORDER BY id DESC LIMIT 100").fetchall()
    reports = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        reports.append({"id": row["id"], "created_utc": row["created_utc"], "fields": format_fields(payload)})
    base = request.url_root.rstrip("/")
    diagnostic_url = f"{base}/d/{REPORT_TOKEN}"
    return render_template_string(DASHBOARD, reports=reports, diagnostic_url=diagnostic_url, dashboard_token=token)


@app.post("/dashboard/<token>/clear")
def clear_reports(token: str):
    if not secrets.compare_digest(token, DASHBOARD_TOKEN):
        abort(404)
    with db_connect() as conn:
        conn.execute("DELETE FROM reports")
    return redirect(url_for("dashboard", token=token))


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


init_db()

if __name__ == "__main__":
    print("Android browser diagnostics is starting.")
    print("Set REPORT_TOKEN and DASHBOARD_TOKEN environment variables before public deployment.")
    print(f"Diagnostic path: /d/{REPORT_TOKEN}")
    print(f"Dashboard path:  /dashboard/{DASHBOARD_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
