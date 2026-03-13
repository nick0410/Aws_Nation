"""
AWS AutoNation – User Authentication Service
Simple file-based user store with hashed passwords.
Each user supplies their own AWS credentials at signup.
"""

import json
import os
import hashlib
import secrets
from pathlib import Path

# Vercel serverless has read-only filesystem; use /tmp for writable storage
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    USERS_FILE = Path("/tmp/users.json")
else:
    USERS_FILE = Path(__file__).parent / "users.json"

# In-memory session store: token -> username
_sessions: dict[str, str] = {}


def _load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def signup(
    username: str,
    password: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    aws_region: str = "ap-south-1",
) -> dict:
    """Register a new user with their AWS credentials."""
    users = _load_users()

    if username.lower() in users:
        return {"success": False, "error": "Username already exists."}

    if len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters."}

    if len(password) < 4:
        return {"success": False, "error": "Password must be at least 4 characters."}

    if not aws_access_key_id or not aws_secret_access_key:
        return {"success": False, "error": "AWS credentials are required."}

    users[username.lower()] = {
        "username": username,
        "password_hash": _hash_password(password),
        "aws_access_key_id": aws_access_key_id,
        "aws_secret_access_key": aws_secret_access_key,
        "aws_region": aws_region,
    }

    _save_users(users)

    # Auto-login after signup
    token = secrets.token_hex(32)
    _sessions[token] = username.lower()

    return {
        "success": True,
        "message": f"User '{username}' registered successfully.",
        "token": token,
        "username": username,
        "aws_region": aws_region,
    }


def login(username: str, password: str) -> dict:
    """Authenticate a user and return a session token."""
    users = _load_users()
    user = users.get(username.lower())

    if not user:
        return {"success": False, "error": "User not found."}

    if user["password_hash"] != _hash_password(password):
        return {"success": False, "error": "Incorrect password."}

    token = secrets.token_hex(32)
    _sessions[token] = username.lower()

    return {
        "success": True,
        "token": token,
        "username": user["username"],
        "aws_region": user["aws_region"],
    }


def get_user_from_token(token: str) -> dict | None:
    """Look up user data from a session token."""
    username = _sessions.get(token)
    if not username:
        return None

    users = _load_users()
    user = users.get(username)
    if not user:
        return None

    return {
        "username": user["username"],
        "aws_access_key_id": user["aws_access_key_id"],
        "aws_secret_access_key": user["aws_secret_access_key"],
        "aws_region": user["aws_region"],
    }


def logout(token: str) -> dict:
    """Invalidate a session token."""
    if token in _sessions:
        del _sessions[token]
    return {"success": True, "message": "Logged out."}
