# Android Browser Diagnostics (consent-based)

A small Flask app with one diagnostic link and one PC dashboard. It gathers only browser-exposed diagnostics after the visitor explicitly consents and submits the report.

## What it collects

- Public IP lookup through `api.ipify.org` (only after consent; if the lookup fails, the report says unavailable)
- Browser user-agent and reported platform
- Language, timezone, screen/viewport dimensions
- Online flag and optional browser network hints
- Optional hardware-concurrency, device-memory and touch-point hints
- Submission timestamp

## What it does NOT collect

It cannot inspect email accounts, installed apps, messages, contacts, photos, files, passwords, cookies, Android settings, ADB status, accessibility permissions or device-admin settings. It does not install an agent, request sensitive Android permissions, or enable remote control.

## Run locally on Windows

1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Run:

   ```cmd
   py -m venv .venv
   .venv\Scripts\activate
   py -m pip install -r requirements.txt
   ```

4. Create long random tokens and set them in the same Command Prompt session:

   ```cmd
   py -c "import secrets; print('REPORT_TOKEN='+secrets.token_urlsafe(24)); print('DASHBOARD_TOKEN='+secrets.token_urlsafe(32))"
   set REPORT_TOKEN=PASTE_THE_FIRST_VALUE_HERE
   set DASHBOARD_TOKEN=PASTE_THE_SECOND_VALUE_HERE
   py app.py
   ```

5. Open `http://127.0.0.1:5000/dashboard/YOUR_DASHBOARD_TOKEN` to see the dashboard.

A locally running app is not publicly reachable from the phone unless you deploy it to a hosting provider with HTTPS. Do not expose the Flask development server directly to the internet.

## Deploy to Render

1. Upload this folder to a private GitHub repository.
2. In Render, create a new Blueprint and select that repository; Render will use `render.yaml`.
3. The Blueprint generates separate random `REPORT_TOKEN` and `DASHBOARD_TOKEN` values.
4. After deployment, open `https://YOUR-SERVICE.onrender.com/dashboard/YOUR_DASHBOARD_TOKEN` using the dashboard token from the Render environment settings.
5. Copy the diagnostic URL shown on the dashboard and share it only with the intended phone user.

Keep the dashboard URL private. Anyone who obtains it can view and delete stored reports. Use HTTPS; do not put passwords, one-time codes or personal account credentials into the page.

## Important limitation for this situation

The phone must actually open the diagnostic link and someone must tick the consent box and submit the report. A link cannot open itself on a remote phone with a dead touchscreen. If no authorised remote-control channel was configured beforehand, this diagnostic app cannot create one.

## Data handling

Reports are stored in `reports.sqlite3` in the app's data directory. The dashboard has a delete-all button. On ephemeral hosting, local database files may be lost when the service restarts or redeploys. For persistent hosting, attach a private persistent disk or use a managed database, and define an appropriate retention policy.
