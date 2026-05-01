from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import query_one, execute

auth_bp = Blueprint("auth", __name__)


# ---------------- LOGIN REQUIRED ----------------
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("auth.user_login"))
        return view_func(*args, **kwargs)
    return wrapper


# ---------------- ROLE REQUIRED ----------------
def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You are not authorized.", "danger")
                return redirect(url_for("web.dashboard"))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


# ---------------- REGISTER (ADMIN ONLY) ----------------
@auth_bp.route("/register", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        role = "Member"  # 🔒 Always Member

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        existing_user = query_one("SELECT id FROM users WHERE email = ?", (email,))
        if existing_user:
            flash("Email already exists.", "warning")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(password)

        execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, role),
        )

        flash("User created successfully.", "success")
        return redirect(url_for("web.manage_users"))

    return render_template("register.html")


# ---------------- ADMIN LOGIN ----------------
@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    # 🔒 Already logged in → redirect
    if session.get("user_id"):
        if session.get("role") == "Admin":
            return redirect(url_for("web.dashboard"))
        else:
            return redirect(url_for("web.member_tasks"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Enter email and password.", "danger")
            return redirect(url_for("auth.admin_login"))

        user = query_one("SELECT * FROM users WHERE email = ?", (email,))

        if not user or user["role"] != "Admin":
            flash("Admin access only.", "danger")
            return redirect(url_for("auth.admin_login"))

        if not check_password_hash(user["password"], password):
            flash("Incorrect password.", "danger")
            return redirect(url_for("auth.admin_login"))

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["role"] = user["role"]

        flash(f"Welcome Admin {user['name']}!", "success")
        return redirect(url_for("web.dashboard"))

    return render_template("login.html", login_type="Admin")


# ---------------- USER LOGIN ----------------
@auth_bp.route("/user/login", methods=["GET", "POST"])
def user_login():

    # 🔒 Already logged in → redirect
    if session.get("user_id"):
        if session.get("role") == "Admin":
            return redirect(url_for("web.dashboard"))
        else:
            return redirect(url_for("web.member_tasks"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Enter email and password.", "danger")
            return redirect(url_for("auth.user_login"))

        user = query_one("SELECT * FROM users WHERE email = ?", (email,))

        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("auth.user_login"))

        if not check_password_hash(user["password"], password):
            flash("Incorrect password.", "danger")
            return redirect(url_for("auth.user_login"))

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["role"] = user["role"]

        flash(f"Welcome {user['name']}!", "success")
        return redirect(url_for("web.member_tasks"))

    return render_template("login.html", login_type="User")


# ---------------- LOGOUT ----------------
@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("web.home"))