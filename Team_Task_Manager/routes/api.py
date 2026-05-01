from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from db import query_all, query_one, execute

api_bp = Blueprint("api", __name__)
VALID_STATUSES = ["Pending", "In Progress", "Completed"]


def row_dict(row):
    return dict(row) if row else None


@api_bp.route("/users", methods=["GET"])
def get_users():
    return jsonify([dict(r) for r in query_all("SELECT id, name, email, role FROM users ORDER BY id DESC")]), 200


@api_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = query_one("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,))
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(dict(user)), 200


@api_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "Member")
    if not name or not email or not password or role not in ["Admin", "Member"]:
        return jsonify({"error": "name, email, password and valid role are required"}), 400
    if query_one("SELECT id FROM users WHERE email = ?", (email,)):
        return jsonify({"error": "email already exists"}), 400
    cursor = execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        (name, email, generate_password_hash(password), role),
    )
    user = query_one("SELECT id, name, email, role FROM users WHERE id = ?", (cursor.lastrowid,))
    return jsonify(dict(user)), 201


@api_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    existing_user = query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not existing_user:
        return jsonify({"error": "user not found"}), 404
    data = request.get_json() or {}
    name = data.get("name", existing_user["name"]).strip()
    email = data.get("email", existing_user["email"]).strip().lower()
    role = data.get("role", existing_user["role"])
    password = data.get("password")
    if role not in ["Admin", "Member"]:
        return jsonify({"error": "invalid role"}), 400
    duplicate = query_one("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
    if duplicate:
        return jsonify({"error": "email already exists"}), 400
    execute("UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?", (name, email, role, user_id))
    if password:
        execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(password), user_id))
    updated = query_one("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,))
    return jsonify(dict(updated)), 200


@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if not query_one("SELECT id FROM users WHERE id = ?", (user_id,)):
        return jsonify({"error": "user not found"}), 404
    execute("DELETE FROM users WHERE id = ?", (user_id,))
    return jsonify({"message": "user deleted"}), 200


@api_bp.route("/projects", methods=["GET"])
def get_projects():
    return jsonify([dict(r) for r in query_all("SELECT * FROM projects ORDER BY id DESC")]), 200


@api_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    project = query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if not project:
        return jsonify({"error": "project not found"}), 404
    return jsonify(dict(project)), 200


@api_bp.route("/projects", methods=["POST"])
def create_project():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    created_by = data.get("created_by")
    if not name or not description or created_by is None:
        return jsonify({"error": "name, description and created_by are required"}), 400
    if not query_one("SELECT id FROM users WHERE id = ?", (created_by,)):
        return jsonify({"error": "created_by user does not exist"}), 400
    cursor = execute(
        "INSERT INTO projects (name, description, created_by) VALUES (?, ?, ?)",
        (name, description, created_by),
    )
    project = query_one("SELECT * FROM projects WHERE id = ?", (cursor.lastrowid,))
    return jsonify(dict(project)), 201


@api_bp.route("/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    project = query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if not project:
        return jsonify({"error": "project not found"}), 404
    data = request.get_json() or {}
    name = data.get("name", project["name"]).strip()
    description = data.get("description", project["description"]).strip()
    if not name or not description:
        return jsonify({"error": "name and description are required"}), 400
    execute("UPDATE projects SET name = ?, description = ? WHERE id = ?", (name, description, project_id))
    updated = query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    return jsonify(dict(updated)), 200


@api_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    if not query_one("SELECT id FROM projects WHERE id = ?", (project_id,)):
        return jsonify({"error": "project not found"}), 404
    execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return jsonify({"message": "project deleted"}), 200


@api_bp.route("/tasks", methods=["GET"])
def get_tasks():
    return jsonify([dict(r) for r in query_all("SELECT * FROM tasks ORDER BY id DESC")]), 200


@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        return jsonify({"error": "task not found"}), 404
    return jsonify(dict(task)), 200


@api_bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    status = data.get("status", "Pending")
    due_date = data.get("due_date")
    assigned_to = data.get("assigned_to")
    project_id = data.get("project_id")
    if not title or not description or assigned_to is None or project_id is None:
        return jsonify({"error": "title, description, assigned_to and project_id are required"}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": "invalid status"}), 400
    if not query_one("SELECT id FROM users WHERE id = ?", (assigned_to,)):
        return jsonify({"error": "assigned_to user does not exist"}), 400
    if not query_one("SELECT id FROM projects WHERE id = ?", (project_id,)):
        return jsonify({"error": "project_id does not exist"}), 400
    cursor = execute(
        "INSERT INTO tasks (title, description, status, due_date, assigned_to, project_id) VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, status, due_date, assigned_to, project_id),
    )
    task = query_one("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,))
    return jsonify(dict(task)), 201


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        return jsonify({"error": "task not found"}), 404
    data = request.get_json() or {}
    title = data.get("title", task["title"]).strip()
    description = data.get("description", task["description"]).strip()
    status = data.get("status", task["status"])
    due_date = data.get("due_date", task["due_date"])
    assigned_to = data.get("assigned_to", task["assigned_to"])
    project_id = data.get("project_id", task["project_id"])
    if status not in VALID_STATUSES:
        return jsonify({"error": "invalid status"}), 400
    if not query_one("SELECT id FROM users WHERE id = ?", (assigned_to,)):
        return jsonify({"error": "assigned_to user does not exist"}), 400
    if not query_one("SELECT id FROM projects WHERE id = ?", (project_id,)):
        return jsonify({"error": "project_id does not exist"}), 400
    execute(
        """
        UPDATE tasks
        SET title = ?, description = ?, status = ?, due_date = ?, assigned_to = ?, project_id = ?
        WHERE id = ?
        """,
        (title, description, status, due_date, assigned_to, project_id, task_id),
    )
    updated = query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return jsonify(dict(updated)), 200


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if not query_one("SELECT id FROM tasks WHERE id = ?", (task_id,)):
        return jsonify({"error": "task not found"}), 404
    execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return jsonify({"message": "task deleted"}), 200
