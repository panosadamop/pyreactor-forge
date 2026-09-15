"""Entity bookkeeping: the .pyforge.json registry, editing and safe removal.

Every generated entity is recorded in the project's `.pyforge.json` so that
`pyforge entity-edit` knows its current shape and `pyforge entity-remove` knows
exactly which files it owns. Projects generated before the registry existed are
handled too: their files are rediscovered from the naming conventions.
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from pyreactor_forge.naming import legacy_plural, pluralize

PROJECT_FILE = ".pyforge.json"
BACKUP_DIR = ".pyforge-backups"


class ProjectError(Exception):
    """Raised when a command is run outside a PyReactor Forge project."""


def config_path(app_dir: Path) -> Path:
    return Path(app_dir) / PROJECT_FILE


def load_config(app_dir: Path) -> dict:
    path = config_path(app_dir)
    if not path.exists():
        raise ProjectError(
            f"No {PROJECT_FILE} found in '{app_dir}'. "
            "Run this command inside a PyReactor Forge-generated project."
        )
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_config(app_dir: Path, config: dict):
    with open(config_path(app_dir), "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")


def entities_of(config: dict) -> dict[str, dict]:
    return config.setdefault("entities", {})


def upsert_entity(config: dict, spec: dict):
    entities_of(config)[spec["name"]] = spec


def forget_entity(config: dict, name: str):
    entities_of(config).pop(name, None)


def table_names(config: dict) -> dict[str, str]:
    return {
        name: spec["table"]
        for name, spec in entities_of(config).items()
        if spec.get("table")
    }


def dependents(config: dict, name: str) -> list[str]:
    """Entities whose relationships point at `name`."""
    found = []
    for other, spec in entities_of(config).items():
        if other == name:
            continue
        for relationship in spec.get("relationships", []):
            if relationship.get("target") == name:
                found.append(other)
                break
    return sorted(found)


# ── plural resolution ───────────────────────────────────────────────────


def plurals_for(name: str) -> list[str]:
    """Every plural an entity's files may use: the current one, then the legacy one."""
    slug = name.lower()
    candidates = [pluralize(slug)]
    if legacy_plural(slug) not in candidates:
        candidates.append(legacy_plural(slug))
    return candidates


def resolve_plural(app_dir: Path, config: dict, name: str) -> str:
    """The plural this project actually uses for `name`.

    New entities get the proper plural ("categories"). Entities generated
    before pluralisation was fixed keep theirs ("categorys") so regenerating
    them updates their files instead of orphaning them.
    """
    recorded = entities_of(config).get(name, {}).get("plural")
    if recorded:
        return recorded

    backend = config.get("backend", "fastapi")
    slug = name.lower()
    for candidate in plurals_for(name):
        if backend == "fastapi":
            marker = Path(app_dir) / "backend" / "app" / "routers" / f"{candidate}.py"
        elif backend == "django":
            marker = Path(app_dir) / "backend" / "api" / f"views_{slug}.py"
        else:
            marker = Path(app_dir) / "backend" / "app" / f"routes_{slug}.py"
        if marker.exists():
            if backend == "fastapi":
                return candidate
            # Django and Flask do not put the plural in a file name, so read it
            # back from the registration instead.
            return _registered_plural(app_dir, config, name) or candidate
    return plurals_for(name)[0]


def _registered_plural(app_dir: Path, config: dict, name: str) -> str | None:
    backend = config.get("backend", "fastapi")
    if backend == "django":
        path = Path(app_dir) / "backend" / "api" / "v1" / "urls.py"
        pattern = rf'router\.register\(r"([A-Za-z0-9_]+)", {name}ViewSet'
    else:
        path = Path(app_dir) / "backend" / "app" / "__init__.py"
        pattern = rf"from \.routes_{name.lower()} import ([A-Za-z0-9_]+)_bp"
    if not path.exists():
        return None
    match = re.search(pattern, path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


# ── file discovery ──────────────────────────────────────────────────────


def expected_files(config: dict, name: str) -> list[str]:
    """Files an entity owns, derived from the naming conventions.

    Both plural spellings are listed; callers filter by what exists on disk.
    """
    backend = config.get("backend", "fastapi")
    frontend = config.get("frontend", "react-ts")
    ts = frontend == "react-ts"
    ext = "tsx" if ts else "jsx"
    ext_plain = "ts" if ts else "js"
    slug = name.lower()

    if backend == "fastapi":
        files = [
            f"backend/app/models/{slug}.py",
            f"backend/app/schemas/{slug}.py",
        ]
        files += [f"backend/app/routers/{plural}.py" for plural in plurals_for(name)]
    elif backend == "django":
        files = [
            f"backend/api/models_{slug}.py",
            f"backend/api/serializers_{slug}.py",
            f"backend/api/views_{slug}.py",
        ]
    else:
        files = [
            f"backend/app/model_{slug}.py",
            f"backend/app/routes_{slug}.py",
        ]

    files += [
        f"frontend/src/services/{slug}Service.{ext_plain}",
        f"frontend/src/pages/{name}Page.{ext}",
    ]
    return files


def owned_files(app_dir: Path, config: dict, name: str) -> list[str]:
    """Recorded files for an entity, falling back to the conventional names."""
    spec = entities_of(config).get(name, {})
    recorded = [f for f in spec.get("files", []) if not f.endswith("(updated)")]
    candidates = recorded or expected_files(config, name)
    return [f for f in candidates if (Path(app_dir) / f).exists()]


def known_entity_names(app_dir: Path, config: dict) -> list[str]:
    """Registered entities, plus any discovered from files on disk."""
    names = set(entities_of(config))
    backend = config.get("backend", "fastapi")
    app_dir = Path(app_dir)

    if backend == "fastapi":
        models = app_dir / "backend" / "app" / "models"
        skip = {"user", "__init__"}
        if models.exists():
            names.update(
                path.stem.capitalize() for path in models.glob("*.py") if path.stem not in skip
            )
    elif backend == "django":
        api = app_dir / "backend" / "api"
        if api.exists():
            names.update(
                path.stem[len("models_") :].capitalize()
                for path in api.glob("models_*.py")
            )
    else:
        app = app_dir / "backend" / "app"
        if app.exists():
            names.update(path.stem[len("model_") :].capitalize() for path in app.glob("model_*.py"))

    return sorted(names)


# ── registration clean-up ───────────────────────────────────────────────


def _drop_lines(text: str, predicate) -> str:
    return "\n".join(line for line in text.split("\n") if not predicate(line))


def registration_edits(config: dict, name: str) -> dict[str, list[str]]:
    """Map of file -> substrings identifying the lines that register `name`.

    Markers are listed for every plural spelling, so an entity registered
    before pluralisation was fixed is still unregistered cleanly.
    """
    backend = config.get("backend", "fastapi")
    ts = config.get("frontend", "react-ts") == "react-ts"
    ext = "tsx" if ts else "jsx"
    slug = name.lower()
    plurals = plurals_for(name)

    edits: dict[str, list[str]] = {}
    if backend == "fastapi":
        edits["backend/app/main.py"] = [
            marker
            for plural in plurals
            for marker in (
                f"from app.routers import {plural}",
                f"app.include_router({plural}.router",
            )
        ]
    elif backend == "django":
        edits["backend/api/models.py"] = [f"from .models_{slug} import {name}"]
        edits["backend/api/v1/urls.py"] = [
            f"from ..views_{slug} import {name}ViewSet",
            f"{name}ViewSet, basename=",
        ]
    else:
        edits["backend/app/__init__.py"] = [
            marker
            for plural in plurals
            for marker in (
                f"from .routes_{slug} import {plural}_bp",
                f"app.register_blueprint({plural}_bp",
            )
        ]

    edits[f"frontend/src/App.{ext}"] = [
        f'import {name}Page from "./pages/{name}Page";',
        *[f'<Route path="/{plural}"' for plural in plurals],
    ]
    return edits


def pending_registration_edits(app_dir: Path, config: dict, name: str) -> list[str]:
    """Registration files that still mention the entity."""
    app_dir = Path(app_dir)
    pending = []
    for relative, markers in registration_edits(config, name).items():
        path = app_dir / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in markers):
            pending.append(relative)
    return pending


# ── removal ─────────────────────────────────────────────────────────────


def removal_plan(app_dir: Path, config: dict, name: str) -> dict:
    """What `remove_entity` would do, without touching anything."""
    return {
        "name": name,
        "delete": owned_files(app_dir, config, name),
        "update": pending_registration_edits(app_dir, config, name),
        "dependents": dependents(config, name),
        "registered": name in entities_of(config),
        "table": entities_of(config).get(name, {}).get(
            "table", resolve_plural(app_dir, config, name)
        ),
    }


def backup_files(app_dir: Path, relatives: list[str], label: str) -> Path | None:
    """Copy the given files into a timestamped backup directory."""
    app_dir = Path(app_dir)
    if not relatives:
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = app_dir / BACKUP_DIR / f"{stamp}-{label}"
    for relative in relatives:
        source = app_dir / relative
        if not source.exists():
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return target


def remove_entity(
    app_dir: Path, config: dict, name: str, backup: bool = True, cascade: bool = False
) -> dict:
    """Delete an entity's files and strip its registrations. Returns the result."""
    app_dir = Path(app_dir)
    plan = removal_plan(app_dir, config, name)

    to_backup = list(plan["delete"] + plan["update"])
    if cascade:
        for dependent in plan["dependents"]:
            to_backup.extend(owned_files(app_dir, config, dependent))

    backup_path = None
    if backup:
        backup_path = backup_files(app_dir, to_backup, f"remove-{name}")

    for relative in plan["delete"]:
        path = app_dir / relative
        if path.exists():
            path.unlink()

    for relative, markers in registration_edits(config, name).items():
        path = app_dir / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        cleaned = _drop_lines(text, lambda line: any(marker in line for marker in markers))
        if cleaned != text:
            path.write_text(cleaned, encoding="utf-8")

    forget_entity(config, name)

    regenerated = []
    if cascade:
        regenerated = _drop_relationships_to(app_dir, config, name, plan["dependents"])

    save_config(app_dir, config)

    return {
        "deleted": plan["delete"],
        "updated": plan["update"],
        "regenerated": regenerated,
        "backup": str(backup_path.relative_to(app_dir)) if backup_path else None,
        "table": plan["table"],
    }


def _drop_relationships_to(
    app_dir: Path, config: dict, removed: str, dependents_of_removed: list[str]
) -> list[str]:
    """Regenerate dependent entities without their references to `removed`."""
    from pyreactor_forge.generators.entity import EntityGenerator

    regenerated = []
    for dependent in dependents_of_removed:
        spec = entities_of(config).get(dependent)
        if spec is None:
            continue
        kept = [
            relationship
            for relationship in spec.get("relationships", [])
            if relationship.get("target") != removed
        ]
        if len(kept) == len(spec.get("relationships", [])):
            continue
        spec["relationships"] = kept
        generator = EntityGenerator(
            dependent,
            spec.get("fields", []),
            config,
            app_dir,
            relationships=kept,
            options=spec.get("options"),
            table=spec.get("table"),
            table_names=table_names(config),
            plural=resolve_plural(app_dir, config, dependent),
        )
        generator.generate()
        upsert_entity(config, generator.spec())
        regenerated.append(dependent)
    return regenerated


# ── editing ─────────────────────────────────────────────────────────────

FIELD_SPEC_RE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*):(?P<type>[a-z]+)(?::(?P<required>required|optional))?$"
)

FIELD_TYPES = ("string", "text", "integer", "float", "boolean", "date", "datetime")


def parse_field_spec(raw: str) -> dict:
    """Parse a `name:type[:required]` CLI field specification."""
    match = FIELD_SPEC_RE.match(raw.strip())
    if not match:
        raise ValueError(
            f"'{raw}' is not a field specification - use name:type or name:type:required"
        )
    field_type = match.group("type")
    if field_type not in FIELD_TYPES:
        raise ValueError(
            f"unknown field type '{field_type}' in '{raw}' "
            f"(choose from {', '.join(FIELD_TYPES)})"
        )
    return {
        "name": match.group("name"),
        "type": field_type,
        "required": match.group("required") == "required",
    }


def entity_spec(app_dir: Path, config: dict, name: str) -> dict:
    """The stored spec for an entity, or a best-effort empty one."""
    spec = entities_of(config).get(name)
    if spec is not None:
        return json.loads(json.dumps(spec))  # deep copy
    plural = resolve_plural(app_dir, config, name)
    return {
        "name": name,
        "table": plural,
        "plural": plural,
        "fields": [],
        "relationships": [],
        "options": {},
        "files": owned_files(app_dir, config, name),
    }
