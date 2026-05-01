from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import query_all, query_one, execute
from routes.auth import login_required, role_required
from werkzeug.security import generate_password_hash

web_bp = Blueprint("web", __name__)

VALID_STATUSES = ["Pending", "In Progress", "Completed"]


# ---------------- HOME ----------------
@web_bp.route("/")
def home():
    return render_template("home.html")


# ---------------- DASHBOARD ----------------
@web_bp.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    user_id = session.get("user_id")

    if role == "Admin":
        all_tasks = query_all("""
            SELECT t.*, p.name AS project_name
            FROM tasks t
            JOIN projects p ON p.id = t.project_id
            ORDER BY t.id DESC
        """)
    else:
        all_tasks = query_all("""
            SELECT t.*, p.name AS project_name
            FROM tasks t
            JOIN projects p ON p.id = t.project_id
            WHERE t.assigned_to = ?
            ORDER BY t.id DESC
        """, (user_id,))

    total_tasks = len(all_tasks)
    completed_tasks = sum(1 for t in all_tasks if t["status"] == "Completed")
    pending_tasks = sum(1 for t in all_tasks if t["status"] == "Pending")
    in_progress_tasks = sum(1 for t in all_tasks if t["status"] == "In Progress")

    today = date.today().isoformat()
    overdue_tasks = sum(
        1 for t in all_tasks
        if t["due_date"] and t["status"] != "Completed" and t["due_date"] < today
    )

    completion_percentage = int((completed_tasks / total_tasks) * 100) if total_tasks else 0

    overdue_list = [
        t for t in all_tasks
        if t["due_date"] and t["status"] != "Completed" and t["due_date"] < today
    ][:5]

    return render_template(
        "dashboard.html",
        tasks=all_tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        overdue_tasks=overdue_tasks,
        completion_percentage=completion_percentage,
        overdue_list=overdue_list,
    )


# ---------------- TASK LIST (PAGINATION + FILTER) ----------------
@web_bp.route("/tasks")
@login_required
def tasks():
    role = session.get("role")
    user_id = session.get("user_id")

    page = int(request.args.get("page", 1))
    per_page = 5
    offset = (page - 1) * per_page

    status = request.args.get("status", "").strip()

    filters = []
    params = []

    if role != "Admin":
        filters.append("t.assigned_to = ?")
        params.append(user_id)

    if status in VALID_STATUSES:
        filters.append("t.status = ?")
        params.append(status)

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    total = query_one(f"""
        SELECT COUNT(*) as count FROM tasks t {where_clause}
    """, tuple(params))["count"]

    tasks = query_all(f"""
        SELECT t.*, u.name AS assigned_name, p.name AS project_name
        FROM tasks t
        JOIN users u ON u.id = t.assigned_to
        JOIN projects p ON p.id = t.project_id
        {where_clause}
        ORDER BY t.id DESC
        LIMIT ? OFFSET ?
    """, tuple(params + [per_page, offset]))

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "tasks.html",
        tasks=tasks,
        statuses=VALID_STATUSES,
        current_page=page,
        total_pages=total_pages,
        selected_status=status,
    )


# ---------------- MEMBER TASKS ----------------
@web_bp.route("/member-tasks")
@login_required
def member_tasks():
    return redirect(url_for("web.tasks"))


# ---------------- PROFILE ----------------
@web_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = query_one("SELECT * FROM users WHERE id = ?", (session["user_id"],))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()

        if not name:
            flash("Name is required.", "danger")
            return redirect(url_for("web.profile"))

        if password:
            if len(password) < 6:
                flash("Password must be at least 6 characters.", "danger")
                return redirect(url_for("web.profile"))

            hashed = generate_password_hash(password)

            execute(
                "UPDATE users SET name = ?, password = ? WHERE id = ?",
                (name, hashed, session["user_id"]),
            )
        else:
            execute(
                "UPDATE users SET name = ? WHERE id = ?",
                (name, session["user_id"]),
            )

        flash("Profile updated successfully.", "success")
        return redirect(url_for("web.profile"))

    return render_template("profile.html", user=user)


# ---------------- USERS (SEARCH + PAGINATION) ----------------
@web_bp.route("/users")
@login_required
@role_required("Admin")
def manage_users():
    page = int(request.args.get("page", 1))
    per_page = 5
    offset = (page - 1) * per_page

    search = request.args.get("q", "").strip()

    filters = []
    params = []

    if search:
        filters.append("(name LIKE ? OR email LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    total = query_one(f"""
        SELECT COUNT(*) as count FROM users {where_clause}
    """, tuple(params))["count"]

    users = query_all(f"""
        SELECT id, name, email, role
        FROM users
        {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, tuple(params + [per_page, offset]))

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "users.html",
        users=users,
        current_page=page,
        total_pages=total_pages,
        search=search,
    )


# ---------------- DELETE USER ----------------
@web_bp.route("/users/delete/<int:id>", methods=["POST"])
@login_required
@role_required("Admin")
def delete_user(id):
    if id == session.get("user_id"):
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for("web.manage_users"))

    execute("DELETE FROM users WHERE id = ?", (id,))
    flash("User deleted successfully.", "success")
    return redirect(url_for("web.manage_users"))


# ---------------- TOGGLE ROLE ----------------
@web_bp.route("/users/toggle-role/<int:id>", methods=["POST"])
@login_required
@role_required("Admin")
def toggle_role(id):
    user = query_one("SELECT role FROM users WHERE id = ?", (id,))
    new_role = "Admin" if user["role"] == "Member" else "Member"

    execute("UPDATE users SET role = ? WHERE id = ?", (new_role, id))
    flash("User role updated.", "success")
    return redirect(url_for("web.manage_users"))


# ---------------- RESET PASSWORD ----------------
@web_bp.route("/users/reset-password/<int:id>", methods=["POST"])
@login_required
@role_required("Admin")
def reset_password(id):
    hashed = generate_password_hash("123456")
    execute("UPDATE users SET password = ? WHERE id = ?", (hashed, id))

    flash("Password reset to 123456", "warning")
    return redirect(url_for("web.manage_users"))