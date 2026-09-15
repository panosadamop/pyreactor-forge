"""Tests for PyReactor Forge generators."""

import ast
import json
import shutil
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyreactor_forge.cli import cli
from pyreactor_forge.generators.app import AppGenerator


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d)


BASE_CONFIG = {
    "name": "test-app",
    "backend": "fastapi",
    "frontend": "react-ts",
    "database": "sqlite",
    "auth": "jwt",
    "docker": True,
    "ci": "github-actions",
}


class TestAppGenerator:
    def test_generates_project_structure(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        gen = AppGenerator(config)
        gen.generate()

        project = temp_dir / "test-app"
        assert project.exists()
        assert (project / "backend").exists()
        assert (project / "frontend").exists()
        assert (project / ".pyforge.json").exists()
        assert (project / "README.md").exists()
        assert (project / "Makefile").exists()

    def test_pyforge_json_content(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()

        meta_path = temp_dir / "test-app" / ".pyforge.json"
        with open(meta_path) as f:
            meta = json.load(f)

        assert meta["name"] == "test-app"
        assert meta["backend"] == "fastapi"
        assert meta["frontend"] == "react-ts"
        assert meta["database"] == "sqlite"

    def test_fastapi_generates_correct_files(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()

        backend = temp_dir / "test-app" / "backend"
        assert (backend / "app" / "main.py").exists()
        assert (backend / "app" / "core" / "config.py").exists()
        assert (backend / "app" / "core" / "database.py").exists()
        assert (backend / "app" / "core" / "security.py").exists()
        assert (backend / "app" / "models" / "user.py").exists()
        assert (backend / "app" / "routers" / "auth.py").exists()
        assert (backend / "app" / "routers" / "users.py").exists()
        assert (backend / "requirements.txt").exists()

    def test_frontend_generates_correct_files(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()

        frontend = temp_dir / "test-app" / "frontend"
        assert (frontend / "package.json").exists()
        assert (frontend / "src" / "App.tsx").exists()
        assert (frontend / "src" / "main.tsx").exists()
        assert (frontend / "src" / "pages" / "LoginPage.tsx").exists()
        assert (frontend / "src" / "pages" / "DashboardPage.tsx").exists()
        assert (frontend / "src" / "store" / "authStore.ts").exists()
        assert (frontend / "src" / "services" / "authService.ts").exists()

    def test_docker_files_generated(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()

        project = temp_dir / "test-app"
        assert (project / "docker-compose.yml").exists()
        assert (project / "backend" / "Dockerfile").exists()
        assert (project / "frontend" / "Dockerfile").exists()

    def test_github_actions_ci_generated(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()

        ci_path = temp_dir / "test-app" / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists()
        content = ci_path.read_text()
        assert "backend-test" in content
        assert "frontend-test" in content

    def test_fails_if_dir_exists(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()
        with pytest.raises(FileExistsError):
            AppGenerator(config).generate()

    def test_django_backend(self, temp_dir):
        config = {**BASE_CONFIG, "backend": "django", "output_dir": str(temp_dir)}
        AppGenerator(config).generate()
        backend = temp_dir / "test-app" / "backend"
        assert (backend / "manage.py").exists()

    def test_flask_backend(self, temp_dir):
        config = {**BASE_CONFIG, "backend": "flask", "output_dir": str(temp_dir)}
        AppGenerator(config).generate()
        backend = temp_dir / "test-app" / "backend"
        assert (backend / "wsgi.py").exists()


    @pytest.mark.parametrize("frontend", ["react", "react-ts"])
    def test_frontend_package_json_is_valid(self, temp_dir, frontend):
        config = {**BASE_CONFIG, "frontend": frontend, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()

        pkg_path = temp_dir / "test-app" / "frontend" / "package.json"
        with open(pkg_path, encoding="utf-8") as f:
            pkg = json.load(f)

        # 18.3.1 is the last published 18.x release; a higher pin makes
        # npm install fail with ETARGET before it fetches anything.
        assert pkg["dependencies"]["react"] == "^18.3.1"
        assert pkg["dependencies"]["react-dom"] == "^18.3.1"
        assert ("typescript" in pkg["devDependencies"]) == (frontend == "react-ts")


    @pytest.mark.parametrize(
        "backend,seed_path,seed_cmd",
        [
            ("fastapi", "backend/scripts/seed.py", "python -m scripts.seed"),
            ("flask", "backend/scripts/seed.py", "python -m scripts.seed"),
            ("django", "backend/api/management/commands/seed.py", "python manage.py seed"),
        ],
    )
    def test_seed_command_generated(self, temp_dir, backend, seed_path, seed_cmd):
        config = {**BASE_CONFIG, "backend": backend, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()

        project = temp_dir / "test-app"
        seed = project / seed_path
        assert seed.exists()

        source = seed.read_text(encoding="utf-8")
        ast.parse(source)  # the generated script must be valid Python
        assert "is_superuser" in source
        assert "ADMIN_PASSWORD" in source

        makefile = (project / "Makefile").read_text(encoding="utf-8")
        assert f"seed:\n\tcd backend && source .venv/bin/activate && {seed_cmd}" in makefile

        readme = (project / "README.md").read_text(encoding="utf-8")
        assert "### Create the admin user" in readme
        assert seed_cmd in readme


class TestEntityGenerator:
    def _generate_base_app(self, temp_dir):
        config = {**BASE_CONFIG, "output_dir": str(temp_dir)}
        AppGenerator(config).generate()
        return temp_dir / "test-app"

    def test_entity_generates_files(self, temp_dir):
        from pyreactor_forge.generators.entity import EntityGenerator

        project = self._generate_base_app(temp_dir)
        with open(project / ".pyforge.json") as f:
            app_config = json.load(f)

        fields = [
            {"name": "title", "type": "string", "required": True},
            {"name": "price", "type": "float", "required": True},
            {"name": "description", "type": "text", "required": False},
        ]
        gen = EntityGenerator("Product", fields, app_config, project)
        gen.generate()

        assert (project / "backend" / "app" / "models" / "product.py").exists()
        assert (project / "backend" / "app" / "schemas" / "product.py").exists()
        assert (project / "backend" / "app" / "routers" / "products.py").exists()
        assert (project / "frontend" / "src" / "services" / "productService.ts").exists()
        assert (project / "frontend" / "src" / "pages" / "ProductPage.tsx").exists()

    def test_entity_router_has_crud(self, temp_dir):
        from pyreactor_forge.generators.entity import EntityGenerator

        project = self._generate_base_app(temp_dir)
        with open(project / ".pyforge.json") as f:
            app_config = json.load(f)

        fields = [{"name": "name", "type": "string", "required": True}]
        EntityGenerator("Category", fields, app_config, project).generate()

        router = (project / "backend" / "app" / "routers" / "categorys.py").read_text()
        assert "list_categorys" in router
        assert "create_category" in router
        assert "get_category" in router
        assert "update_category" in router
        assert "delete_category" in router


class TestCLI:
    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "PyReactor Forge" in result.output

    def test_info_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "FastAPI" in result.output
        assert "Django" in result.output

    def test_windows_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["windows"])
        assert result.exit_code == 0
        assert ".venv\\Scripts\\Activate.ps1" in result.output
        assert "py -3 -m venv .venv" in result.output

    def test_new_command(self, temp_dir):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "new",
            "--name", "cli-test-app",
            "--backend", "fastapi",
            "--frontend", "react-ts",
            "--database", "sqlite",
            "--auth", "jwt",
            "--output-dir", str(temp_dir),
            "--docker",
            "--ci", "github-actions",
        ])
        assert result.exit_code == 0, result.output
        assert (temp_dir / "cli-test-app").exists()
