"""Django backend generator."""

from pathlib import Path


class DjangoGenerator:
    def __init__(self, config: dict, output_dir: Path):
        self.config = config
        self.out = output_dir
        self.name = config["name"]
        self.slug = self.name.lower().replace("-", "_").replace(" ", "_")
        self.db = config["database"]

    def generate(self):
        app = self.out / self.slug
        app.mkdir(parents=True)
        (self.out / "tests").mkdir()
        (self.out / "api").mkdir()
        (self.out / "api" / "v1").mkdir()

        self._write_manage()
        self._write_settings()
        self._write_app()
        self._write_requirements()
        self._write_env()

    def _write_manage(self):
        (self.out / "manage.py").write_text(f'''#!/usr/bin/env python
"""Django\'s command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{self.slug}.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn\'t import Django.") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
''')

    def _write_settings(self):
        db_engine = {
            "postgresql": "django.db.backends.postgresql",
            "mysql": "django.db.backends.mysql",
            "sqlite": "django.db.backends.sqlite3",
        }[self.db]

        (self.out / self.slug / "__init__.py").write_text("")
        (self.out / self.slug / "settings.py").write_text(f'''"""Django settings for {self.name}."""

from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-in-production")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "{self.slug}.urls"

DATABASES = {{
    "default": {{
        "ENGINE": "{db_engine}",
        "NAME": os.environ.get("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }}
}}

REST_FRAMEWORK = {{
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}}

SIMPLE_JWT = {{
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
''')

        (self.out / self.slug / "urls.py").write_text(f'''"""URL configuration for {self.name}."""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("api.v1.urls")),
]
''')

    def _write_app(self):
        (self.out / "api" / "__init__.py").write_text("")
        (self.out / "api" / "v1" / "__init__.py").write_text("")
        (self.out / "api" / "v1" / "urls.py").write_text('''from django.urls import path
from . import views

urlpatterns = [
    path("users/me/", views.MeView.as_view(), name="me"),
    path("health/", views.HealthView.as_view(), name="health"),
]
''')
        (self.out / "api" / "v1" / "views.py").write_text('''"""API Views."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "date_joined"]


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})
''')

    def _write_requirements(self):
        db_pkg = {
            "postgresql": "psycopg2-binary",
            "mysql": "mysqlclient",
            "sqlite": "",
        }[self.db]

        (self.out / "requirements.txt").write_text(f"""Django>=5.0.0
djangorestframework>=3.15.0
djangorestframework-simplejwt>=5.3.0
django-cors-headers>=4.3.0
python-decouple>=3.8
{db_pkg}
pytest-django>=4.8.0
ruff>=0.4.0
""")

    def _write_env(self):
        (self.out / ".env.example").write_text(f"""DEBUG=True
SECRET_KEY=your-secret-key-here
DB_NAME={self.slug}
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
""")
