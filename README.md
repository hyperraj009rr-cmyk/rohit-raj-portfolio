# Rohit Raj — Creator Portfolio

## Features
- Premium responsive dark-blue design with animated intro and reveal effects
- Public portfolio and dynamic categories for projects, e-books, websites, apps, photos, videos, audio, trading and other creations
- Admin login/dashboard; upload cover and asset files; edit/delete; public/private; publish/unpublish
- Hire Me / Contact form with inbox and request status tracking
- Database fields reserved for future paid e-books; payment processing is NOT yet enabled

## Run on Windows PowerShell
1. Extract the ZIP and open PowerShell in this folder.
2. `py -m venv .venv`
3. `\.venv\Scripts\Activate.ps1`
4. `py -m pip install -r requirements.txt`
5. `py app.py`
6. Open http://127.0.0.1:5000
7. Admin: http://127.0.0.1:5000/admin/login

Local starter credentials: `admin` / `ChangeMe-123!`. Change them before deploying publicly by setting `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and a long random `SECRET_KEY` as environment variables. The `.env.example` is a reference file; this starter does not automatically load `.env`.

## Deployment notes
- Use HTTPS and a persistent disk/database for uploads and database. Some free hosts erase local files when restarting/redeploying.
- Before enabling paid e-books, implement buyer accounts, verified server-side payment webhooks, purchase entitlements, and protected/private storage. The current Paid setting intentionally locks an item rather than granting access.
- A website cannot guarantee blocking screenshots, screen recording, or photography from another device. Watermarks/access controls can discourage copying but not eliminate it.
- Before a broad public launch, add CSRF protection, rate limiting, backup strategy, and email/Telegram notifications.
