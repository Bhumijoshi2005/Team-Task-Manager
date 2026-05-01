import os
import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = os.path.join(current_app.root_path, "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())
    db.commit()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def execute(sql, params=()):
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    return cursor


def init_app(app):
    app.teardown_appcontext(close_db)
