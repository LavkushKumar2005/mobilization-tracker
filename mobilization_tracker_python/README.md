# Mobilization Tracker – Python Flask + MySQL starter

This package contains the supplied HTML dashboard and a starter Flask API for shared online data.

## Important
- The supplied dashboard currently stores its workspace in browser `localStorage` and attachments in browser `IndexedDB`.
- This API provides authenticated login and a shared workspace endpoint, but the existing HTML has **not yet been wired to these endpoints**. Until the frontend integration is completed, users on different devices will not automatically share records.
- All authenticated users can read and update the shared workspace. Only an Administrator can create API user accounts.
- Large file attachments are not included in the shared JSON API. They need a separate cloud file-storage integration.

## 1. MySQL
Create a MySQL database and run `database/schema.sql` in phpMyAdmin or your MySQL client.

Set `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_EMAIL`, and `BOOTSTRAP_ADMIN_PASSWORD` on the server before the first login. On the first login attempt with those exact credentials, the API creates the first Administrator. Remove the bootstrap password environment variable immediately after successful setup.

## 2. Run locally
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```
Set the environment variables from `backend/.env.example`, then:
```bash
python app.py
```
Health check: `http://127.0.0.1:5000/api/health`

## 3. API endpoints
- `POST /api/auth/login` – JSON `{ "email": "...", "password": "..." }`
- `GET /api/auth/me` – requires `Authorization: Bearer <token>`
- `GET /api/workspace` – returns the shared workspace; requires login
- `PUT /api/workspace` – saves `{ "data": { ... } }`; requires login
- `POST /api/admin/users` – creates a user; Administrator only

Tokens expire after 7 days. Use HTTPS in production.

## 4. Hostinger VPS deployment
1. Create a VPS and point a subdomain such as `api.yourdomain.com` to its public IP.
2. Install Python, a virtual environment, and a reverse proxy (Nginx).
3. Configure Gunicorn to run `app:app` from the `backend` directory.
4. Set environment variables on the server. Never upload `.env` or passwords to GitHub.
5. Configure HTTPS (for example, with Let's Encrypt).
6. Ensure your MySQL provider allows connections from the VPS IP. Prefer private networking if available.

## 5. GitHub
Upload this project to a **private** GitHub repository. Do not commit passwords, API tokens, or database credentials.
