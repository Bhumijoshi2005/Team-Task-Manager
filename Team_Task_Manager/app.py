import os
from flask import Flask
from db import init_app as init_db_app, init_db
from routes.auth import auth_bp
from routes.web import web_bp
from routes.api import api_bp


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SESSION_PERMANENT"] = False
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE_PATH"] = os.getenv(
        "DATABASE_PATH",
        os.path.join(app.instance_path, "team_task_manager.db"),
    )
    init_db_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        init_db()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
