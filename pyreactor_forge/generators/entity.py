"""Entity generator - adds model, CRUD API, and React UI to an existing app."""

from pathlib import Path

from pyreactor_forge.naming import pluralize, table_name_for

PYTHON_TYPE_MAP = {
    "string": ("str", "String(255)"),
    "text": ("str", "Text"),
    "integer": ("int", "Integer"),
    "float": ("float", "Float"),
    "boolean": ("bool", "Boolean"),
    "date": ("date", "Date"),
    "datetime": ("datetime", "DateTime(timezone=True)"),
}

TS_TYPE_MAP = {
    "string": "string",
    "text": "string",
    "integer": "number",
    "float": "number",
    "boolean": "boolean",
    "date": "string",
    "datetime": "string",
}

DJANGO_TYPE_MAP = {
    "string": "CharField",
    "text": "TextField",
    "integer": "IntegerField",
    "float": "FloatField",
    "boolean": "BooleanField",
    "date": "DateField",
    "datetime": "DateTimeField",
}

FLASK_TYPE_MAP = {
    "string": "String(255)",
    "text": "Text",
    "integer": "Integer",
    "float": "Float",
    "boolean": "Boolean",
    "date": "Date",
    "datetime": "DateTime(timezone=True)",
}

# Relationship kinds, as produced by pydl.to_entity_specs.
TO_ONE = ("many-to-one", "one-to-one", "one-to-one-inverse")
TO_MANY = ("one-to-many", "many-to-many", "many-to-many-inverse")


class EntityGenerator:
    def __init__(
        self,
        name: str,
        fields: list[dict],
        app_config: dict,
        app_dir: Path,
        relationships: list[dict] | None = None,
        options: dict | None = None,
        table: str | None = None,
        table_names: dict[str, str] | None = None,
        plural: str | None = None,
    ):
        self.name = name  # PascalCase, e.g. "Product"
        self.slug = name.lower()  # "product"
        # "category" -> "categories"; an explicit plural keeps projects
        # generated before proper pluralisation on their original paths.
        self.slug_plural = plural or pluralize(self.slug)
        self.fields = fields
        self.relationships = relationships or []
        self.options = options or {}
        self.config = app_config
        self.app_dir = app_dir
        self.table = table or self.slug_plural
        self.table_names = dict(table_names or {})
        self.table_names.setdefault(name, self.table)
        self.backend = app_config.get("backend", "fastapi")
        self.frontend = app_config.get("frontend", "react-ts")
        self.ts = self.frontend == "react-ts"
        self.ext = "tsx" if self.ts else "jsx"
        self.ext_plain = "ts" if self.ts else "js"
        self.created_files: list[str] = []
        self.owned_files: list[str] = []

    # ─────────────────────────────────────────────
    # helpers
    # ─────────────────────────────────────────────

    @property
    def read_only(self) -> bool:
        return bool(self.options.get("readOnly"))

    @property
    def skip_client(self) -> bool:
        return bool(self.options.get("skipClient"))

    def _table_for(self, entity_name: str) -> str:
        return self.table_names.get(entity_name) or table_name_for(entity_name)

    def _record(self, path: Path, owned: bool = True):
        relative = str(path.relative_to(self.app_dir)).replace("\\", "/")
        self.created_files.append(relative)
        if owned:
            self.owned_files.append(relative)

    def _to_one(self) -> list[dict]:
        return [r for r in self.relationships if r["kind"] in TO_ONE]

    def _to_many(self) -> list[dict]:
        return [r for r in self.relationships if r["kind"] in TO_MANY]

    def _fk_name(self, relationship: dict) -> str:
        return f"{relationship['name']}_id"

    def _association_table(self, relationship: dict) -> str:
        left, right = sorted([self.table, self._table_for(relationship["target"])])
        return f"{left}_{right}"

    def spec(self) -> dict:
        """The entity definition as stored in .pyforge.json."""
        return {
            "name": self.name,
            "table": self.table,
            "plural": self.slug_plural,
            "fields": self.fields,
            "relationships": self.relationships,
            "options": self.options,
            "files": list(self.owned_files),
        }

    # ─────────────────────────────────────────────

    def generate(self):
        if self.backend == "fastapi":
            self._fastapi_model()
            self._fastapi_schema()
            self._fastapi_router()
            self._register_fastapi_router()
        elif self.backend == "django":
            self._django_model()
            self._django_serializer()
            self._django_view()
            self._register_django_entity()
        else:
            self._flask_model()
            self._flask_routes()
            self._register_flask_blueprint()

        if not self.skip_client:
            self._frontend_service()
            self._frontend_page()
            self._register_frontend_route()

    # ─────────────────────────────────────────────
    # FastAPI
    # ─────────────────────────────────────────────

    def _sa_column(self, field: dict) -> str:
        _, sa_type = PYTHON_TYPE_MAP[field["type"]]
        if field["type"] == "string":
            length = field.get("maxlength") or 255
            sa_type = f"String({int(length)})"
        args = [sa_type]
        if field.get("unique"):
            args.append("unique=True")
            args.append("index=True")
        args.append(f"nullable={str(not field['required'])}")
        return ", ".join(args)

    def _fastapi_model(self):
        imports = set()
        columns = []

        for f in self.fields:
            py_type, _ = PYTHON_TYPE_MAP[f["type"]]
            if f["type"] in ("date", "datetime"):
                imports.add(f"from datetime import {py_type}")

            optional = "" if f["required"] else " | None"
            columns.append(
                f'    {f["name"]}: Mapped[{py_type}{optional}] = '
                f"mapped_column({self._sa_column(f)})"
            )

        association_tables = []
        type_checking = []

        for rel in self._to_one():
            target = rel["target"]
            fk = self._fk_name(rel)
            nullable = not rel.get("required", False)
            optional = " | None" if nullable else ""
            unique = ", unique=True" if rel["kind"].startswith("one-to-one") else ""
            columns.append(
                f'    {fk}: Mapped[int{optional}] = mapped_column('
                f'ForeignKey("{self._table_for(target)}.id", ondelete="CASCADE")'
                f"{unique}, nullable={str(nullable)})"
            )
            back = (
                f'back_populates="{rel["back_populates"]}"' if rel.get("back_populates") else ""
            )
            columns.append(
                f'    {rel["name"]}: Mapped["{target}"] = relationship({back})'
            )
            type_checking.append(target)

        for rel in self._to_many():
            target = rel["target"]
            back = (
                f'back_populates="{rel["back_populates"]}"' if rel.get("back_populates") else ""
            )
            if rel["kind"] == "one-to-many":
                separator = ", " if back else ""
                columns.append(
                    f'    {rel["name"]}: Mapped[list["{target}"]] = '
                    f'relationship({back}{separator}cascade="all, delete-orphan")'
                )
            else:
                association = self._association_table(rel)
                if rel["kind"] == "many-to-many":
                    association_tables.append(
                        self._association_table_source(association, target)
                    )
                separator = ", " if back else ""
                columns.append(
                    f'    {rel["name"]}: Mapped[list["{target}"]] = '
                    f'relationship(secondary="{association}"{separator}{back})'
                )
            type_checking.append(target)

        sa_imports = [
            "String",
            "Integer",
            "Float",
            "Boolean",
            "Text",
            "Date",
            "DateTime",
        ]
        if self.relationships:
            sa_imports.append("ForeignKey")
        if association_tables:
            sa_imports.extend(["Table", "Column"])

        orm_imports = "Mapped, mapped_column"
        if self.relationships:
            orm_imports += ", relationship"

        type_checking_block = ""
        if type_checking:
            lines = "\n".join(
                f"    from app.models.{name.lower()} import {name}"
                for name in sorted(set(type_checking))
                if name != self.name
            )
            if lines:
                type_checking_block = (
                    "from typing import TYPE_CHECKING\n\n"
                    "if TYPE_CHECKING:  # imported for type checkers only\n"
                    f"{lines}\n\n"
                )

        imports_str = "\n".join(sorted(imports))
        if imports_str:
            imports_str += "\n"
        association_str = "\n\n".join(association_tables)
        if association_str:
            association_str += "\n\n"

        model_path = self.app_dir / "backend" / "app" / "models" / f"{self.slug}.py"
        model_path.write_text(
            f'''"""{self.name} database model - generated by PyReactor Forge."""

{imports_str}from sqlalchemy import {", ".join(sa_imports)}
from sqlalchemy.orm import {orm_imports}
from app.core.database import Base

{type_checking_block}{association_str}
class {self.name}(Base):
    __tablename__ = "{self.table}"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
{chr(10).join(columns)}

    def __repr__(self) -> str:
        return f"<{self.name} id={{self.id}}>"
''',
            encoding="utf-8",
        )
        self._record(model_path)

    def _association_table_source(self, association: str, target: str) -> str:
        return (
            f'{association} = Table(\n'
            f'    "{association}",\n'
            f"    Base.metadata,\n"
            f'    Column("{self.slug}_id", ForeignKey("{self.table}.id", '
            f'ondelete="CASCADE"), primary_key=True),\n'
            f'    Column("{target.lower()}_id", '
            f'ForeignKey("{self._table_for(target)}.id", ondelete="CASCADE"), '
            f"primary_key=True),\n"
            f")"
        )

    def _pydantic_type(self, field: dict) -> str:
        if field.get("enum_values"):
            values = ", ".join(f'"{value}"' for value in field["enum_values"])
            return f"Literal[{values}]"
        return PYTHON_TYPE_MAP[field["type"]][0]

    def _pydantic_constraints(self, field: dict) -> list[str]:
        constraints = []
        if field["type"] in ("string", "text") and not field.get("enum_values"):
            if field.get("minlength") is not None:
                constraints.append(f"min_length={int(field['minlength'])}")
            if field.get("maxlength") is not None:
                constraints.append(f"max_length={int(field['maxlength'])}")
            if field.get("pattern"):
                constraints.append(f'pattern=r"{field["pattern"]}"')
        if field["type"] in ("integer", "float"):
            if field.get("min") is not None:
                constraints.append(f"ge={field['min']}")
            if field.get("max") is not None:
                constraints.append(f"le={field['max']}")
        return constraints

    def _schema_line(self, field: dict, force_optional: bool = False) -> str:
        py_type = self._pydantic_type(field)
        constraints = self._pydantic_constraints(field)
        optional = force_optional or not field["required"]

        annotation = f"{py_type} | None" if optional else py_type
        if constraints and optional:
            arguments = ", ".join(["default=None"] + constraints)
            return f"    {field['name']}: {annotation} = Field({arguments})"
        if constraints:
            return f"    {field['name']}: {annotation} = Field({', '.join(constraints)})"
        if optional:
            return f"    {field['name']}: {annotation} = None"
        return f"    {field['name']}: {annotation}"

    def _fastapi_schema(self):
        base_lines = [self._schema_line(f) for f in self.fields]
        update_lines = [self._schema_line(f, force_optional=True) for f in self.fields]

        for rel in self._to_one():
            fk = self._fk_name(rel)
            required = rel.get("required", False)
            base_lines.append(f"    {fk}: int" if required else f"    {fk}: int | None = None")
            update_lines.append(f"    {fk}: int | None = None")

        imports = ["from pydantic import BaseModel"]
        if any(self._pydantic_constraints(f) for f in self.fields):
            imports[0] = "from pydantic import BaseModel, Field"
        typing_imports = []
        if any(f.get("enum_values") for f in self.fields):
            typing_imports.append("Literal")
        datetime_imports = sorted(
            {
                PYTHON_TYPE_MAP[f["type"]][0]
                for f in self.fields
                if f["type"] in ("date", "datetime")
            }
        )

        header = []
        if datetime_imports:
            header.append(f"from datetime import {', '.join(datetime_imports)}")
        if typing_imports:
            header.append(f"from typing import {', '.join(typing_imports)}")
        header.extend(imports)

        schema_path = self.app_dir / "backend" / "app" / "schemas" / f"{self.slug}.py"
        schema_path.write_text(
            f'''"""{self.name} Pydantic schemas - generated by PyReactor Forge."""

{chr(10).join(header)}


class {self.name}Base(BaseModel):
{chr(10).join(base_lines) or "    pass"}


class {self.name}Create({self.name}Base):
    pass


class {self.name}Update(BaseModel):
{chr(10).join(update_lines) or "    pass"}


class {self.name}Read({self.name}Base):
    id: int
    model_config = {{"from_attributes": True}}
''',
            encoding="utf-8",
        )
        self._record(schema_path)

    def _fastapi_router(self):
        read_routes = f'''

@router.get("/", response_model=list[{self.name}Read])
async def list_{self.slug_plural}(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    offset = (page - 1) * size
    result = await db.execute(select({self.name}).offset(offset).limit(size))
    return result.scalars().all()


@router.get("/{{id}}", response_model={self.name}Read)
async def get_{self.slug}(
    id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select({self.name}).where({self.name}.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="{self.name} not found")
    return obj
'''

        write_routes = f'''

@router.post("/", response_model={self.name}Read, status_code=201)
async def create_{self.slug}(
    data: {self.name}Create,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = {self.name}(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/{{id}}", response_model={self.name}Read)
async def update_{self.slug}(
    id: int,
    data: {self.name}Update,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select({self.name}).where({self.name}.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="{self.name} not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{{id}}", status_code=204)
async def delete_{self.slug}(
    id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select({self.name}).where({self.name}.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="{self.name} not found")
    await db.delete(obj)
    await db.commit()
'''

        schema_imports = f"{self.name}Read"
        if not self.read_only:
            schema_imports = f"{self.name}Create, {self.name}Update, {self.name}Read"

        body = read_routes if self.read_only else read_routes + write_routes
        note = (
            "\n# readOnly: create/update/delete routes are intentionally not generated.\n"
            if self.read_only
            else ""
        )

        router_path = self.app_dir / "backend" / "app" / "routers" / f"{self.slug_plural}.py"
        router_path.write_text(
            f'''"""{self.name} CRUD router - generated by PyReactor Forge."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.{self.slug} import {self.name}
from app.schemas.{self.slug} import {schema_imports}
{note}
router = APIRouter()
{body}''',
            encoding="utf-8",
        )
        self._record(router_path)

    def _register_fastapi_router(self):
        main_path = self.app_dir / "backend" / "app" / "main.py"
        if not main_path.exists():
            return
        content = main_path.read_text(encoding="utf-8")
        import_line = f"from app.routers import {self.slug_plural}"
        register_line = (
            f"app.include_router({self.slug_plural}.router, "
            f'prefix="/api/{self.slug_plural}", tags=["{self.slug_plural}"])'
        )
        if import_line not in content:
            lines = content.split("\n")
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith("from app.routers import"):
                    insert_at = i + 1
            lines.insert(insert_at, import_line)
            content = "\n".join(lines)

        if register_line not in content:
            content += f"\n{register_line}\n"

        main_path.write_text(content, encoding="utf-8")
        self.created_files.append("backend/app/main.py (updated)")

    # ─────────────────────────────────────────────
    # Django
    # ─────────────────────────────────────────────

    def _django_field(self, field: dict) -> str:
        kind = DJANGO_TYPE_MAP[field["type"]]
        args = []
        if field["type"] == "string":
            args.append(f"max_length={int(field.get('maxlength') or 255)}")
        if field.get("enum_values"):
            choices = ", ".join(f'("{v}", "{v}")' for v in field["enum_values"])
            args.append(f"choices=[{choices}]")
        if field.get("unique"):
            args.append("unique=True")
        args.append(f"null={str(not field['required'])}")
        args.append(f"blank={str(not field['required'])}")
        return f"    {field['name']} = models.{kind}({', '.join(args)})"

    def _django_relationship(self, rel: dict) -> str:
        target = rel["target"]
        related = f'related_name="{rel["back_populates"]}"' if rel.get("back_populates") else ""
        if rel["kind"] == "many-to-one":
            null = not rel.get("required", False)
            parts = [
                f'"{target}"',
                "on_delete=models.CASCADE",
                f"null={str(null)}",
                f"blank={str(null)}",
            ]
            if related:
                parts.append(related)
            return f"    {rel['name']} = models.ForeignKey({', '.join(parts)})"
        if rel["kind"] == "one-to-one":
            parts = [f'"{target}"', "on_delete=models.CASCADE", "null=True", "blank=True"]
            if related:
                parts.append(related)
            return f"    {rel['name']} = models.OneToOneField({', '.join(parts)})"
        if rel["kind"] == "many-to-many":
            parts = [f'"{target}"', "blank=True"]
            if related:
                parts.append(related)
            return f"    {rel['name']} = models.ManyToManyField({', '.join(parts)})"
        return ""  # inverse sides are provided by related_name

    def _django_model(self):
        lines = [self._django_field(f) for f in self.fields]
        lines += [
            line
            for line in (self._django_relationship(r) for r in self.relationships)
            if line
        ]
        out = self.app_dir / "backend" / "api" / f"models_{self.slug}.py"
        out.write_text(
            f'''"""{self.name} model - generated by PyReactor Forge."""

from django.db import models


class {self.name}(models.Model):
{chr(10).join(lines) or "    pass"}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "{self.table}"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} #{{self.pk}}"
''',
            encoding="utf-8",
        )
        self._record(out)

    def _django_serializer(self):
        out = self.app_dir / "backend" / "api" / f"serializers_{self.slug}.py"
        out.write_text(
            f'''"""{self.name} serializer - generated by PyReactor Forge."""

from rest_framework import serializers
from .models_{self.slug} import {self.name}


class {self.name}Serializer(serializers.ModelSerializer):
    class Meta:
        model = {self.name}
        fields = "__all__"
''',
            encoding="utf-8",
        )
        self._record(out)

    def _django_view(self):
        base = "ReadOnlyModelViewSet" if self.read_only else "ModelViewSet"
        out = self.app_dir / "backend" / "api" / f"views_{self.slug}.py"
        out.write_text(
            f'''"""{self.name} viewset - generated by PyReactor Forge."""

from rest_framework.viewsets import {base}
from .models_{self.slug} import {self.name}
from .serializers_{self.slug} import {self.name}Serializer


class {self.name}ViewSet({base}):
    queryset = {self.name}.objects.all()
    serializer_class = {self.name}Serializer
''',
            encoding="utf-8",
        )
        self._record(out)

    def _register_django_entity(self):
        """Wire the model into Django's app registry and the API router."""
        api_dir = self.app_dir / "backend" / "api"
        models_py = api_dir / "models.py"
        import_line = f"from .models_{self.slug} import {self.name}  # noqa: F401"
        existing = models_py.read_text(encoding="utf-8") if models_py.exists() else (
            '"""Model registry - generated by PyReactor Forge."""\n'
        )
        if import_line not in existing:
            existing = existing.rstrip("\n") + "\n" + import_line + "\n"
        models_py.write_text(existing, encoding="utf-8")
        self.created_files.append("backend/api/models.py (updated)")

        urls_py = api_dir / "v1" / "urls.py"
        if not urls_py.exists():
            return
        content = urls_py.read_text(encoding="utf-8")
        if "DefaultRouter" not in content:
            content = content.replace(
                "from django.urls import path\n",
                "from django.urls import path, include\n"
                "from rest_framework.routers import DefaultRouter\n",
                1,
            )
            content = content.replace(
                "urlpatterns = [\n",
                "router = DefaultRouter()\n\n"
                "urlpatterns = [\n"
                '    path("", include(router.urls)),\n',
                1,
            )
        view_import = f"from ..views_{self.slug} import {self.name}ViewSet"
        register = (
            f'router.register(r"{self.slug_plural}", {self.name}ViewSet, '
            f'basename="{self.slug}")'
        )
        if view_import not in content:
            content = content.replace(
                "router = DefaultRouter()", f"{view_import}\n\nrouter = DefaultRouter()", 1
            )
        if register not in content:
            content = content.replace(
                "router = DefaultRouter()", f"router = DefaultRouter()\n{register}", 1
            )
        urls_py.write_text(content, encoding="utf-8")
        self.created_files.append("backend/api/v1/urls.py (updated)")

    # ─────────────────────────────────────────────
    # Flask
    # ─────────────────────────────────────────────

    def _flask_column(self, field: dict) -> str:
        column = FLASK_TYPE_MAP[field["type"]]
        if field["type"] == "string":
            column = f"String({int(field.get('maxlength') or 255)})"
        args = [f"db.{column}"]
        if field.get("unique"):
            args.append("unique=True")
        args.append(f"nullable={str(not field['required'])}")
        return f"    {field['name']} = db.Column({', '.join(args)})"

    def _flask_model(self):
        lines = [self._flask_column(f) for f in self.fields]
        for rel in self._to_one():
            nullable = not rel.get("required", False)
            lines.append(
                f"    {self._fk_name(rel)} = db.Column(db.Integer, "
                f'db.ForeignKey("{self._table_for(rel["target"])}.id"), '
                f"nullable={str(nullable)})"
            )

        out = self.app_dir / "backend" / "app" / f"model_{self.slug}.py"
        out.write_text(
            f'''"""{self.name} model - generated by PyReactor Forge."""

from . import db


class {self.name}(db.Model):
    __tablename__ = "{self.table}"
    id = db.Column(db.Integer, primary_key=True)
{chr(10).join(lines)}

    def to_dict(self):
        return {{
            "id": self.id,
{chr(10).join(f'            "{f["name"]}": getattr(self, "{f["name"]}"),' for f in self.fields)}
        }}
''',
            encoding="utf-8",
        )
        self._record(out)

    def _flask_routes(self):
        write_routes = f'''

@{self.slug_plural}_bp.post("/")
@jwt_required()
def create_{self.slug}():
    data = request.get_json()
    obj = {self.name}(**data)
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@{self.slug_plural}_bp.delete("/<int:item_id>")
@jwt_required()
def delete_{self.slug}(item_id):
    obj = {self.name}.query.get_or_404(item_id)
    db.session.delete(obj)
    db.session.commit()
    return "", 204
'''
        out = self.app_dir / "backend" / "app" / f"routes_{self.slug}.py"
        out.write_text(
            f'''"""{self.name} routes - generated by PyReactor Forge."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from . import db
from .model_{self.slug} import {self.name}

{self.slug_plural}_bp = Blueprint("{self.slug_plural}", __name__)


@{self.slug_plural}_bp.get("/")
@jwt_required()
def list_{self.slug_plural}():
    items = {self.name}.query.all()
    return jsonify([item.to_dict() for item in items])
{"" if self.read_only else write_routes}''',
            encoding="utf-8",
        )
        self._record(out)

    def _register_flask_blueprint(self):
        init_py = self.app_dir / "backend" / "app" / "__init__.py"
        if not init_py.exists():
            return
        content = init_py.read_text(encoding="utf-8")
        import_line = f"    from .routes_{self.slug} import {self.slug_plural}_bp"
        register_line = (
            f"    app.register_blueprint({self.slug_plural}_bp, "
            f'url_prefix="/api/{self.slug_plural}")'
        )
        if import_line not in content:
            content = content.replace(
                "    from .routes import auth_bp, users_bp, health_bp\n",
                f"    from .routes import auth_bp, users_bp, health_bp\n{import_line}\n",
                1,
            )
        if register_line not in content:
            content = content.replace(
                '    app.register_blueprint(users_bp, url_prefix="/api/users")\n',
                '    app.register_blueprint(users_bp, url_prefix="/api/users")\n'
                f"{register_line}\n",
                1,
            )
        init_py.write_text(content, encoding="utf-8")
        self.created_files.append("backend/app/__init__.py (updated)")

    # ─────────────────────────────────────────────
    # Frontend
    # ─────────────────────────────────────────────

    def _ts_type(self, field: dict) -> str:
        if field.get("enum_values"):
            return " | ".join(f'"{value}"' for value in field["enum_values"])
        return TS_TYPE_MAP[field["type"]]

    def _interface_fields(self) -> list[str]:
        lines = []
        for f in self.fields:
            optional = "" if f["required"] else "?"
            lines.append(f"  {f['name']}{optional}: {self._ts_type(f)};")
        for rel in self._to_one():
            optional = "" if rel.get("required", False) else "?"
            lines.append(f"  {self._fk_name(rel)}{optional}: number;")
        return lines

    def _frontend_service(self):
        ts_interface = ""
        if self.ts:
            ts_interface = (
                f"export interface {self.name} {{\n"
                f"  id: number;\n"
                f"{chr(10).join(self._interface_fields())}\n"
                f"}}\n\n"
            )

        mutations = f'''
  create: async (data: {"Omit<" + self.name + ", 'id'>" if self.ts else "object"}) => {{
    const res = await api.post("/{self.slug_plural}/", data);
    return res.data{f" as {self.name}" if self.ts else ""};
  }},

  update: async (id: number, data: {"Partial<" + self.name + ">" if self.ts else "object"}) => {{
    const res = await api.patch(`/{self.slug_plural}/${{id}}`, data);
    return res.data{f" as {self.name}" if self.ts else ""};
  }},

  delete: async (id: number) => {{
    await api.delete(`/{self.slug_plural}/${{id}}`);
  }},
'''

        svc_path = (
            self.app_dir / "frontend" / "src" / "services" / f"{self.slug}Service.{self.ext_plain}"
        )
        svc_path.write_text(
            f'''{ts_interface}import api from "./api";

export const {self.slug}Service = {{
  list: async (page = 1, size = 20) => {{
    const res = await api.get("/{self.slug_plural}/", {{ params: {{ page, size }} }});
    return res.data{f" as {self.name}[]" if self.ts else ""};
  }},

  get: async (id: number) => {{
    const res = await api.get(`/{self.slug_plural}/${{id}}`);
    return res.data{f" as {self.name}" if self.ts else ""};
  }},
{"" if self.read_only else mutations}}};
''',
            encoding="utf-8",
        )
        self._record(svc_path)

    def _frontend_page(self):
        table_fields = [f["name"] for f in self.fields] + [
            self._fk_name(rel) for rel in self._to_one()
        ]
        columns_jsx = "\n".join(
            f'              <th className="px-4 py-3 text-left text-xs font-medium '
            f'text-gray-500 uppercase">{name}</th>'
            for name in table_fields
        )
        cells_jsx = "\n".join(
            f'                <td className="px-4 py-3 text-sm text-gray-700">'
            f'{{String(item.{name} ?? "-")}}</td>'
            for name in table_fields
        )
        actions_header = (
            ""
            if self.read_only
            else '\n              <th className="px-4 py-3 text-right text-xs font-medium '
            'text-gray-500 uppercase">Actions</th>'
        )
        actions_cell = (
            ""
            if self.read_only
            else '''
                <td className="px-4 py-3 text-right">
                  <button className="text-xs text-blue-600 hover:underline mr-3">Edit</button>
                  <button className="text-xs text-red-500 hover:underline">Delete</button>
                </td>'''
        )
        add_button = (
            ""
            if self.read_only
            else f'''
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          + Add {self.name}
        </button>'''
        )

        page_path = self.app_dir / "frontend" / "src" / "pages" / f"{self.name}Page.{self.ext}"
        page_path.write_text(
            f'''import {{ useQuery }} from "@tanstack/react-query";
import {{ {self.slug}Service }} from "../services/{self.slug}Service";

export default function {self.name}Page() {{
  const {{ data: items = [], isLoading, error }} = useQuery({{
    queryKey: ["{self.slug_plural}"],
    queryFn: () => {self.slug}Service.list(),
  }});

  if (isLoading) {{
    return <div className="flex items-center justify-center h-64 text-gray-400">Loading {self.slug_plural}...</div>;
  }}

  if (error) {{
    return <div className="p-8 text-red-500">Failed to load {self.slug_plural}.</div>;
  }}

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{self.name}s</h1>{add_button}
      </div>

      <div className="bg-white border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
{columns_jsx}{actions_header}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {{items.map((item) => (
              <tr key={{item.id}} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 text-sm text-gray-500">{{item.id}}</td>
{cells_jsx}{actions_cell}
              </tr>
            ))}}
            {{items.length === 0 && (
              <tr>
                <td colSpan={{99}} className="px-4 py-8 text-center text-gray-400 text-sm">
                  No {self.slug_plural} yet.
                </td>
              </tr>
            )}}
          </tbody>
        </table>
      </div>
    </div>
  );
}}
''',
            encoding="utf-8",
        )
        self._record(page_path)

    def _register_frontend_route(self):
        app_path = self.app_dir / "frontend" / "src" / f"App.{self.ext}"
        if not app_path.exists():
            return
        content = app_path.read_text(encoding="utf-8")
        import_line = f'import {self.name}Page from "./pages/{self.name}Page";'
        route_line = (
            f'          <Route path="/{self.slug_plural}" '
            f"element={{<{self.name}Page />}} />"
        )

        if import_line not in content:
            content = import_line + "\n" + content
        if route_line not in content:
            content = content.replace(
                "          <Route index element={<DashboardPage />} />",
                f"          <Route index element={{<DashboardPage />}} />\n{route_line}",
            )
        app_path.write_text(content, encoding="utf-8")
        self.created_files.append(f"frontend/src/App.{self.ext} (updated)")
