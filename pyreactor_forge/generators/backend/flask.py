"""Flask backend generator."""

from pathlib import Path


class FlaskGenerator:
    def __init__(self, config: dict, output_dir: Path):
        self.config = config
        self.out = output_dir
        self.name = config["name"]
        self.db = config["database"]

    def generate(self):
        (self.out / "app").mkdir(parents=True)
        (self.out / "tests").mkdir()

        self._write_app()
        self._write_models()
        self._write_routes()
        self._write_requirements()
        self._write_env()

    def _write_app(self):
        (self.out / "app" / "__init__.py").write_text(f'''"""Flask application factory."""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from .config import Config

db = SQLAlchemy()
jwt = JWTManager()


def create_app(config=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=config.CORS_ORIGINS)

    from .routes import auth_bp, users_bp, health_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")

    with app.app_context():
        db.create_all()

    return app
''', encoding="utf-8")

        (self.out / "app" / "config.py").write_text(f'''"""Flask configuration."""

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-in-production")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///./app.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
''', encoding="utf-8")

        (self.out / "wsgi.py").write_text('''"""WSGI entry point."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
''', encoding="utf-8")

    def _write_models(self):
        (self.out / "app" / "models.py").write_text('''"""Database models."""

from datetime import datetime, timezone
from . import db
import bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_superuser = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str):
        self.hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.hashed_password.encode())

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
''', encoding="utf-8")

    def _write_routes(self):
        (self.out / "app" / "routes.py").write_text('''"""Flask route blueprints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from . import db
from .models import User

health_bp = Blueprint("health", __name__)
auth_bp = Blueprint("auth", __name__)
users_bp = Blueprint("users", __name__)


@health_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@auth_bp.post("/register")
def register():
    data = request.get_json()
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 400
    user = User(email=data["email"], username=data["username"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "token_type": "bearer"})


@users_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(int(user_id))
    return jsonify(user.to_dict())
''', encoding="utf-8")

    def _write_requirements(self):
        (self.out / "requirements.txt").write_text("""Flask>=3.0.0
Flask-SQLAlchemy>=3.1.0
Flask-JWT-Extended>=4.6.0
Flask-Cors>=4.0.0
bcrypt>=4.1.0
python-decouple>=3.8
pytest>=8.2.0
pytest-flask>=1.3.0
ruff>=0.4.0
""", encoding="utf-8")

    def _write_env(self):
        (self.out / ".env.example").write_text("""SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-key-here
DATABASE_URL=sqlite:///./app.db
DEBUG=True
""", encoding="utf-8")
