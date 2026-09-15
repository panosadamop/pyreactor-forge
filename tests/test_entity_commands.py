"""Tests for import-pydl, entity-edit and entity-remove."""

import ast
import json
import shutil
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyreactor_forge import entities
from pyreactor_forge.cli import cli
from pyreactor_forge.generators.app import AppGenerator

PYDL = """
entity Category {
  name String required unique maxlength(50)
}

entity Product {
  name String required minlength(2) maxlength(100)
  price BigDecimal required min(0)
  status Status required
}

enum Status {
  DRAFT, ACTIVE
}

relationship ManyToOne {
  Product{category required} to Category{products}
}

paginate Product with pagination
"""


@pytest.fixture
def project():
    directory = Path(tempfile.mkdtemp())
    AppGenerator(
        {
            "name": "shop-app",
            "backend": "fastapi",
            "frontend": "react-ts",
            "database": "sqlite",
            "auth": "jwt",
            "docker": False,
            "ci": "none",
            "output_dir": str(directory),
        }
    ).generate()
    app = directory / "shop-app"
    (app / "model.pydl").write_text(PYDL, encoding="utf-8")
    yield app
    shutil.rmtree(directory, ignore_errors=True)


def run(*args):
    return CliRunner().invoke(cli, list(args))


def config_of(project):
    with open(project / ".pyforge.json", encoding="utf-8") as handle:
        return json.load(handle)


class TestImportPydl:
    def test_dry_run_writes_nothing(self, project):
        result = run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--dry-run")
        assert result.exit_code == 0, result.output
        assert not (project / "backend" / "app" / "models" / "product.py").exists()
        assert config_of(project).get("entities", {}) == {}

    def test_generates_entities_and_records_them(self, project):
        result = run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        assert result.exit_code == 0, result.output

        for relative in [
            "backend/app/models/product.py",
            "backend/app/schemas/product.py",
            "backend/app/routers/products.py",
            "backend/app/models/category.py",
            "frontend/src/services/productService.ts",
            "frontend/src/pages/ProductPage.tsx",
        ]:
            assert (project / relative).exists(), relative

        registry = config_of(project)["entities"]
        assert set(registry) == {"Category", "Product"}
        assert registry["Product"]["options"]["paginate"] == "pagination"

    def test_generated_python_is_valid(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        for path in (project / "backend" / "app").rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"))

    def test_foreign_key_and_validations_reach_the_model(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")

        model = (project / "backend" / "app" / "models" / "product.py").read_text(encoding="utf-8")
        assert 'ForeignKey("categories.id"' in model
        assert "String(100)" in model
        assert 'relationship(back_populates="products")' in model

        schema = (project / "backend" / "app" / "schemas" / "product.py").read_text(
            encoding="utf-8"
        )
        assert "min_length=2, max_length=100" in schema
        assert 'Literal["DRAFT", "ACTIVE"]' in schema
        assert "ge=0" in schema

    def test_router_is_registered_once_per_entity(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")

        main = (project / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        assert main.count("app.include_router(products.router") == 1

    def test_invalid_file_reports_problems_and_fails(self, project):
        (project / "bad.pydl").write_text("entity Product {\n  price Money\n}", encoding="utf-8")
        result = run("import-pydl", str(project / "bad.pydl"), "-a", str(project), "--yes")
        assert result.exit_code == 1
        assert "unknown type" in result.output
        assert not (project / "backend" / "app" / "models" / "product.py").exists()


class TestEntityEdit:
    def test_add_and_remove_fields(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        result = run(
            "entity-edit",
            "-n",
            "Product",
            "-a",
            str(project),
            "--add-field",
            "weight:float",
            "--remove-field",
            "status",
            "--yes",
        )
        assert result.exit_code == 0, result.output

        model = (project / "backend" / "app" / "models" / "product.py").read_text(encoding="utf-8")
        assert "weight" in model
        assert "status" not in model
        assert 'ForeignKey("categories.id"' in model  # relationships survive an edit

        fields = config_of(project)["entities"]["Product"]["fields"]
        assert [f["name"] for f in fields] == ["name", "price", "weight"]

    def test_backs_up_the_previous_version(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        run(
            "entity-edit", "-n", "Product", "-a", str(project),
            "--add-field", "weight:float", "--yes",
        )
        backups = list((project / entities.BACKUP_DIR).glob("*-edit-Product"))
        assert backups and (backups[0] / "backend/app/models/product.py").exists()

    def test_rejects_an_unknown_entity(self, project):
        result = run("entity-edit", "-n", "Nope", "-a", str(project), "--add-field", "x:string")
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_rejects_a_bad_field_specification(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        result = run(
            "entity-edit", "-n", "Product", "-a", str(project), "--add-field", "weight:money"
        )
        assert result.exit_code == 1
        assert "unknown field type" in result.output


class TestEntityRemove:
    def test_refuses_while_another_entity_references_it(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        result = run("entity-remove", "-n", "Category", "-a", str(project), "--yes")

        assert result.exit_code == 1
        assert "Referenced by" in result.output
        assert (project / "backend" / "app" / "models" / "category.py").exists()

    def test_dry_run_changes_nothing(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        result = run("entity-remove", "-n", "Product", "-a", str(project), "--dry-run")

        assert result.exit_code == 0
        assert (project / "backend" / "app" / "models" / "product.py").exists()

    def test_removes_files_registrations_and_registry_entry(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        result = run("entity-remove", "-n", "Product", "-a", str(project), "--yes", "--force")
        assert result.exit_code == 0, result.output

        for relative in [
            "backend/app/models/product.py",
            "backend/app/schemas/product.py",
            "backend/app/routers/products.py",
            "frontend/src/services/productService.ts",
            "frontend/src/pages/ProductPage.tsx",
        ]:
            assert not (project / relative).exists(), relative

        main = (project / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        assert "products" not in main
        app_tsx = (project / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        assert "ProductPage" not in app_tsx

        assert "Product" not in config_of(project)["entities"]
        ast.parse(main)

    def test_backs_up_before_deleting(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        run("entity-remove", "-n", "Product", "-a", str(project), "--yes", "--force")

        backups = list((project / entities.BACKUP_DIR).glob("*-remove-Product"))
        assert backups
        assert (backups[0] / "backend/app/models/product.py").exists()
        assert (backups[0] / "backend/app/main.py").exists()

    def test_force_regenerates_the_entities_that_referenced_it(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        result = run("entity-remove", "-n", "Category", "-a", str(project), "--yes", "--force")
        assert result.exit_code == 0, result.output

        product = (project / "backend" / "app" / "models" / "product.py").read_text(
            encoding="utf-8"
        )
        assert "Category" not in product
        assert "category_id" not in product
        ast.parse(product)

        assert config_of(project)["entities"]["Product"]["relationships"] == []


class TestEntityList:
    def test_lists_registered_entities(self, project):
        run("import-pydl", str(project / "model.pydl"), "-a", str(project), "--yes")
        result = run("entity-list", "-a", str(project))

        assert result.exit_code == 0
        assert "Product" in result.output
        assert "Category" in result.output

    def test_outside_a_project(self, tmp_path):
        result = run("entity-list", "-a", str(tmp_path))
        assert result.exit_code == 1
        assert ".pyforge.json" in result.output


class TestFieldSpecParsing:
    def test_valid(self):
        assert entities.parse_field_spec("price:float:required") == {
            "name": "price",
            "type": "float",
            "required": True,
        }
        assert entities.parse_field_spec("note:text")["required"] is False

    @pytest.mark.parametrize("raw", ["price", "price:money", "9price:string", "price float"])
    def test_invalid(self, raw):
        with pytest.raises(ValueError):
            entities.parse_field_spec(raw)
