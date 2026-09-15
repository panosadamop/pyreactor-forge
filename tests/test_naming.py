"""Tests for entity pluralisation and its effect on generated projects."""

import pytest

from pyreactor_forge import entities
from pyreactor_forge.naming import legacy_plural, pluralize, table_name_for


class TestPluralize:
    @pytest.mark.parametrize(
        "singular,plural",
        [
            ("category", "categories"),
            ("city", "cities"),
            ("company", "companies"),
            ("country", "countries"),
            ("day", "days"),           # vowel + y
            ("key", "keys"),
            ("box", "boxes"),
            ("tax", "taxes"),
            ("address", "addresses"),
            ("status", "statuses"),
            ("bus", "buses"),
            ("church", "churches"),
            ("dish", "dishes"),
            ("quiz", "quizzes"),
            ("analysis", "analyses"),
            ("knife", "knives"),
            ("life", "lives"),
            ("roof", "roofs"),         # not every -f takes -ves
            ("potato", "potatoes"),
            ("photo", "photos"),
            ("person", "people"),
            ("child", "children"),
            ("sheep", "sheep"),        # uncountable
            ("series", "series"),
            ("product", "products"),
            ("tag", "tags"),
            ("user", "users"),
            ("invoice", "invoices"),
            ("order_item", "order_items"),
        ],
    )
    def test_rules(self, singular, plural):
        assert pluralize(singular) == plural

    def test_is_idempotent_for_uncountables(self):
        assert pluralize(pluralize("sheep")) == "sheep"

    def test_table_name_uses_the_plural(self):
        assert table_name_for("Category") == "categories"
        assert table_name_for("User") == "users"

    def test_legacy_plural_is_the_old_behaviour(self):
        assert legacy_plural("category") == "categorys"


class TestGeneratedNames:
    def test_category_uses_categories_everywhere(self, tmp_path):
        from pyreactor_forge.generators.app import AppGenerator
        from pyreactor_forge.generators.entity import EntityGenerator

        AppGenerator(
            {
                "name": "shop",
                "backend": "fastapi",
                "frontend": "react-ts",
                "database": "sqlite",
                "auth": "jwt",
                "docker": False,
                "ci": "none",
                "output_dir": str(tmp_path),
            }
        ).generate()
        project = tmp_path / "shop"
        config = entities.load_config(project)

        generator = EntityGenerator(
            "Category", [{"name": "name", "type": "string", "required": True}], config, project
        )
        generator.generate()

        assert (project / "backend" / "app" / "routers" / "categories.py").exists()
        assert not (project / "backend" / "app" / "routers" / "categorys.py").exists()

        model = (project / "backend" / "app" / "models" / "category.py").read_text(
            encoding="utf-8"
        )
        assert '__tablename__ = "categories"' in model

        main = (project / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        assert 'prefix="/api/categories"' in main

        app_tsx = (project / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        assert '<Route path="/categories"' in app_tsx

        assert generator.spec()["plural"] == "categories"


class TestLegacyProjects:
    """Projects generated before pluralisation was fixed keep their old paths."""

    def _legacy_project(self, tmp_path):
        from pyreactor_forge.generators.app import AppGenerator

        AppGenerator(
            {
                "name": "old",
                "backend": "fastapi",
                "frontend": "react-ts",
                "database": "sqlite",
                "auth": "jwt",
                "docker": False,
                "ci": "none",
                "output_dir": str(tmp_path),
            }
        ).generate()
        project = tmp_path / "old"

        # What 0.1.0 would have written for Category.
        (project / "backend" / "app" / "models" / "category.py").write_text("x = 1\n", "utf-8")
        (project / "backend" / "app" / "schemas" / "category.py").write_text("x = 1\n", "utf-8")
        (project / "backend" / "app" / "routers" / "categorys.py").write_text("x = 1\n", "utf-8")
        (project / "frontend" / "src" / "services" / "categoryService.ts").write_text("//", "utf-8")
        (project / "frontend" / "src" / "pages" / "CategoryPage.tsx").write_text("//", "utf-8")

        main = project / "backend" / "app" / "main.py"
        main.write_text(
            main.read_text(encoding="utf-8")
            + "from app.routers import categorys\n"
            + 'app.include_router(categorys.router, prefix="/api/categorys")\n',
            encoding="utf-8",
        )
        app_tsx = project / "frontend" / "src" / "App.tsx"
        app_tsx.write_text(
            'import CategoryPage from "./pages/CategoryPage";\n'
            + app_tsx.read_text(encoding="utf-8").replace(
                "          <Route index element={<DashboardPage />} />",
                "          <Route index element={<DashboardPage />} />\n"
                '          <Route path="/categorys" element={<CategoryPage />} />',
            ),
            encoding="utf-8",
        )
        return project

    def test_plural_is_resolved_from_the_existing_files(self, tmp_path):
        project = self._legacy_project(tmp_path)
        config = entities.load_config(project)
        assert entities.resolve_plural(project, config, "Category") == "categorys"

    def test_removal_finds_and_cleans_the_old_names(self, tmp_path):
        project = self._legacy_project(tmp_path)
        config = entities.load_config(project)

        plan = entities.removal_plan(project, config, "Category")
        assert "backend/app/routers/categorys.py" in plan["delete"]
        assert "backend/app/main.py" in plan["update"]

        entities.remove_entity(project, config, "Category")

        assert not (project / "backend" / "app" / "routers" / "categorys.py").exists()
        main = (project / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        assert "categorys" not in main
        app_tsx = (project / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        assert "CategoryPage" not in app_tsx
