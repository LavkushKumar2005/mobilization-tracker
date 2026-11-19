import os
import json
from datetime import datetime, timezone
from functools import wraps

import mysql.connector
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "CHANGE_THIS_BEFORE_DEPLOYMENT")
CORS(app, origins=os.environ.get("CORS_ORIGINS", "*").split(","), supports_credentials=False)

serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="mobilization-api")

def db():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        autocommit=False,
        connection_timeout=10,
    )

def token_for(user):
    return serializer.dumps({"id": user["id"], "email": user["email"], "role": user["role"]})

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Login required"), 401
        try:
            payload = serializer.loads(header[7:], max_age=60 * 60 * 24 * 7)
        except SignatureExpired:
            return jsonify(error="Session expired. Please log in again."), 401
        except BadSignature:
            return jsonify(error="Invalid session"), 401

        conn = db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, role, active FROM users WHERE id=%s", (payload["id"],))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if not user or not user["active"]:
            return jsonify(error="User is inactive or unavailable"), 403
        g.user = user
        return fn(*args, **kwargs)
    return wrapper

@app.get("/api/health")
def health():
    return jsonify(status="ok", service="Mobilization Tracker API")

@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not email or not password:
        return jsonify(error="Email and password are required"), 400

    conn = db()
    # Bootstrap the first Administrator only when the users table is empty.
    # Configure BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD on the server,
    # then remove those environment variables after the first successful creation.
    cur0 = conn.cursor()
    cur0.execute("SELECT COUNT(*) FROM users")
    user_count = cur0.fetchone()[0]
    cur0.close()
    if user_count == 0:
        bootstrap_email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
        bootstrap_password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
        if bootstrap_email and bootstrap_password and email == bootstrap_email and password == bootstrap_password:
            cur0 = conn.cursor()
            cur0.execute(
                "INSERT INTO users (name,email,password_hash,role,active) VALUES (%s,%s,%s,'Administrator',1)",
                (os.environ.get("BOOTSTRAP_ADMIN_NAME", "System Administrator"), bootstrap_email, generate_password_hash(bootstrap_password))
            )
            conn.commit()
            cur0.close()

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, email, password_hash, role, active FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not user["active"] or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Incorrect email or password"), 401

    return jsonify(
        token=token_for(user),
        user={"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}
    )

@app.get("/api/auth/me")
@auth_required
def me():
    return jsonify(user=g.user)

@app.get("/api/workspace")
@auth_required
def get_workspace():
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT data_json, updated_at FROM shared_workspace WHERE id=1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify(data=None, updated_at=None)
    return jsonify(data=json.loads(row["data_json"]), updated_at=row["updated_at"].isoformat() if row["updated_at"] else None)

@app.put("/api/workspace")
@auth_required
def save_workspace():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "data" not in payload or not isinstance(payload["data"], dict):
        return jsonify(error="Expected JSON body: {data: {...}}"), 400
    encoded = json.dumps(payload["data"], ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 15 * 1024 * 1024:
        return jsonify(error="Workspace exceeds 15 MB. Store large attachments separately."), 413

    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO shared_workspace (id, data_json, updated_by, updated_at)
           VALUES (1, %s, %s, UTC_TIMESTAMP())
           ON DUPLICATE KEY UPDATE data_json=VALUES(data_json),
             updated_by=VALUES(updated_by), updated_at=UTC_TIMESTAMP()""",
        (encoded, g.user["id"])
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(success=True, saved_at=datetime.now(timezone.utc).isoformat())

@app.post("/api/admin/users")
@auth_required
def create_user():
    if g.user["role"] != "Administrator":
        return jsonify(error="Administrator access required"), 403
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = str(data.get("role", "Mobilizer"))
    if not name or not email or len(password) < 10:
        return jsonify(error="Name, email and password (at least 10 characters) are required"), 400
    if role not in ("Administrator", "Center Manager", "Mobilizer", "View Only"):
        return jsonify(error="Invalid role"), 400
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name,email,password_hash,role,active) VALUES (%s,%s,%s,%s,1)",
            (name, email, generate_password_hash(password), role)
        )
        conn.commit()
    except mysql.connector.IntegrityError:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify(error="That email already exists"), 409
    cur.close()
    conn.close()
    return jsonify(success=True), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
