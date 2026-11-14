"""Local accounts for the educational CardioPrognoz application.

No patient data is stored here. Only usernames, password hashes and account status.
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

import click
from flask import abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_HASHER = PasswordHasher()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


def get_db():
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
                CHECK(role IN ('user','admin')),
            active INTEGER NOT NULL DEFAULT 1
                CHECK(active IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()


def create_user(username: str, password: str, role: str = "user") -> int:
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Логин: 3–32 символа (латиница, цифры, _, - или .).")
    if not 10 <= len(password) <= 128:
        raise ValueError("Пароль должен содержать от 10 до 128 символов.")
    if role not in ("user", "admin"):
        raise ValueError("Недопустимая роль.")

    db = get_db()
    cur = db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, PASSWORD_HASHER.hash(password), role),
    )
    db.commit()
    return int(cur.lastrowid)


def verify_password(stored_hash: str, password: str) -> bool:
    """Read existing Werkzeug hashes and use Argon2id for new and upgraded accounts."""
    if stored_hash.startswith("$argon2"):
        try:
            return PASSWORD_HASHER.verify(stored_hash, password)
        except (VerificationError, InvalidHashError):
            return False
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


def upgrade_password_hash(user_id: int, stored_hash: str, password: str):
    if not stored_hash.startswith("$argon2") or PASSWORD_HASHER.check_needs_rehash(stored_hash):
        db = get_db()
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (PASSWORD_HASHER.hash(password), user_id))
        db.commit()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def require_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if not expected or not hmac.compare_digest(submitted, expected):
        abort(400, description="Недействительный токен формы")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.current_user["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def register_accounts(app):
    app.config.setdefault("DATABASE", str(Path(app.root_path) / "instance" / "cardio.sqlite3"))
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("CARDIO_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=__import__("datetime").timedelta(hours=8),
    )
    # Local-development sessions are intentionally invalidated on restart if no key is set.
    app.secret_key = os.environ.get("CARDIO_SECRET_KEY") or secrets.token_hex(32)

    @app.before_request
    def load_current_user():
        g.current_user = None
        user_id = session.get("user_id")
        if user_id is not None:
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                session.clear()
                return
            g.current_user = get_db().execute(
                "SELECT id, username, role, active FROM users WHERE id = ? AND active = 1",
                (user_id,),
            ).fetchone() if database_initialized() else None
            if g.current_user is None:
                session.clear()

    @app.teardown_appcontext
    def close_connection(exception=None):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    @app.context_processor
    def inject_user_data():
        return {"current_user": g.get("current_user"), "csrf_token": csrf_token}

    @app.cli.command("init-db")
    def init_db_command():
        """Create the local user database."""
        init_db()
        click.echo("База пользователей подготовлена.")

    @app.cli.command("create-admin")
    @click.argument("username")
    def create_admin_command(username):
        """Create the first administrator, asking for a hidden password."""
        init_db()
        password = click.prompt("Пароль администратора", hide_input=True, confirmation_prompt=True)
        try:
            create_user(username, password, "admin")
        except (ValueError, sqlite3.IntegrityError) as err:
            raise click.ClickException(str(err)) from err
        click.echo("Администратор создан.")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.current_user is not None:
            return redirect(url_for("home"))
        error = None
        if request.method == "POST":
            require_csrf()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = None
            if database_initialized():
                user = get_db().execute(
                    "SELECT id, password_hash, active FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
            if user is not None and user["active"] and verify_password(user["password_hash"], password):
                upgrade_password_hash(user["id"], user["password_hash"], password)
                session.clear()
                session["user_id"] = user["id"]
                session.permanent = True
                return redirect(url_for("home"))
            error = "Неверный логин или пароль."
        return render_template("login.html", error=error)

    @app.route("/logout", methods=["POST"])
    def logout():
        require_csrf()
        session.clear()
        return redirect(url_for("login"))

    @app.route("/admin", methods=["GET"])
    @admin_required
    def admin():
        rows = get_db().execute(
            "SELECT id, username, role, active, created_at FROM users ORDER BY id"
        ).fetchall()
        return render_template("admin.html", users=rows)

    @app.route("/admin/users", methods=["POST"])
    @admin_required
    def admin_add_user():
        require_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            create_user(username, password)
            flash("Учебная учётная запись создана.", "success")
        except sqlite3.IntegrityError:
            flash("Такой логин уже существует.", "error")
        except ValueError as err:
            flash(str(err), "error")
        return redirect(url_for("admin"))

    @app.route("/admin/users/<int:user_id>/disable", methods=["POST"])
    @admin_required
    def admin_disable_user(user_id):
        require_csrf()
        target = get_db().execute(
            "SELECT id, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if target is None:
            abort(404)
        if target["role"] != "user":
            abort(403)
        get_db().execute("UPDATE users SET active=0 WHERE id = ?", (user_id,))
        get_db().commit()
        flash("Учётная запись отключена.", "success")
        return redirect(url_for("admin"))


def database_initialized():
    """Avoid a 500 if the site is opened before the `init-db` command."""
    db_path = Path(current_app.config["DATABASE"])
    if not db_path.exists():
        return False
    db = get_db()
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone() is not None
