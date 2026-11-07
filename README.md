# Android Remote Support Installation Page

This Flask app serves a consent-based installation page and a private dashboard. The install button downloads a signed Android APK only if the project owner has placed it at `downloads/android-remote-support.apk` (or configured `AGENT_APK_PATH`). If the APK is absent, the server displays an explicit “not available yet” message.

## Important Android limitations

- A website cannot silently install an APK or grant Android permissions. The Android package installer and Android permission screens require on-device approval.
- A remote-support app must be clearly identified, obtain Android screen-capture approval, and require explicit enabling of Accessibility if that capability is used.
- This project does not implement the Android agent itself. It does not provide screen viewing, touch control, account access, message access or file access.
- Do not hide the app, disguise it, or suppress Android's indicators and permission prompts.

## Publish the APK when it exists

1. Build and sign a legitimate Android remote-support agent that follows Android permission and foreground-service requirements.
2. Review the app's permissions and provide a clear in-app disconnect/revoke control.
3. Place the release APK at `downloads/android-remote-support.apk` in the deployed app, or set `AGENT_APK_PATH` to its server-side path.
4. Redeploy. The install button will then download that APK. Android still asks the device user to confirm installation and subsequent permissions.

Do not put signing keys, passwords, access tokens or private user data in the public Git repository.

## Run locally on Windows

1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Run:

   ```cmd
   py -m venv .venv
   .venv\\Scripts\\activate
   py -m pip install -r requirements.txt
   py app.py
   ```

4. Open the local dashboard path printed by the app. For public access, deploy behind HTTPS using a production WSGI server.

## Deploy to Render

Use the existing `render.yaml` Blueprint or configure a Python Web Service with:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn --bind 0.0.0.0:$PORT app:app`
- Environment variables: secure random `REPORT_TOKEN` and `DASHBOARD_TOKEN`

The dashboard is protected by `DASHBOARD_TOKEN`; the installation page uses `REPORT_TOKEN`. Keep both secret.

## Existing diagnostic reports

Previously collected diagnostic reports remain supported by the dashboard and submit endpoint. The visitor-facing page now presents the transparent app-download workflow instead of submitting a browser report.
