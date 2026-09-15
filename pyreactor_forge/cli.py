"""PyReactor Forge CLI - JHipster-inspired full-stack generator for Python + React."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pyreactor_forge import __version__, entities, pydl
from pyreactor_forge.generators.app import AppGenerator
from pyreactor_forge.generators.entity import EntityGenerator
from pyreactor_forge.utils.display import print_banner, print_error, print_success


def _force_utf8_stdio():
    """Windows defaults stdio to the legacy ANSI code page (cp1252 on most
    installs), which cannot encode the Unicode we print. It only bites when
    output is redirected -- a bare terminal goes through WriteConsoleW and
    works fine -- so piping to a file or running under CI would otherwise
    crash with UnicodeEncodeError.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_force_utf8_stdio()

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="PyReactor Forge")
def cli():
    """
    \b
    ██████╗ ██╗   ██╗██████╗ ███████╗ █████╗  ██████╗████████╗ ██████╗ ██████╗
    ██╔══██╗╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
    ██████╔╝ ╚████╔╝ ██████╔╝█████╗  ███████║██║        ██║   ██║   ██║██████╔╝
    ██╔═══╝   ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██║██║        ██║   ██║   ██║██╔══██╗
    ██║        ██║   ██║  ██║███████╗██║  ██║╚██████╗   ██║   ╚██████╔╝██║  ██║
    ╚═╝        ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝

    Full-stack Python + React application generator.
    Inspired by JHipster. Built for the Python ecosystem.
    """
    pass


@cli.command()
@click.option("--name", "-n", prompt="Application name", help="Name of the application")
@click.option(
    "--backend",
    "-b",
    type=click.Choice(["fastapi", "django", "flask"], case_sensitive=False),
    default="fastapi",
    prompt="Backend framework",
    show_default=True,
    help="Python backend framework",
)
@click.option(
    "--frontend",
    "-f",
    type=click.Choice(["react", "react-ts"], case_sensitive=False),
    default="react-ts",
    prompt="Frontend framework",
    show_default=True,
    help="Frontend framework",
)
@click.option(
    "--database",
    "-d",
    type=click.Choice(["postgresql", "mysql", "sqlite"], case_sensitive=False),
    default="postgresql",
    prompt="Database",
    show_default=True,
    help="Database engine",
)
@click.option(
    "--auth",
    "-a",
    type=click.Choice(["jwt", "session", "oauth2"], case_sensitive=False),
    default="jwt",
    prompt="Authentication type",
    show_default=True,
    help="Authentication strategy",
)
@click.option(
    "--output-dir",
    "-o",
    default=".",
    help="Output directory (default: current directory)",
)
@click.option(
    "--docker/--no-docker",
    default=True,
    prompt="Include Docker configuration?",
    help="Generate Docker and docker-compose files",
)
@click.option(
    "--ci",
    type=click.Choice(["github-actions", "gitlab-ci", "none"], case_sensitive=False),
    default="github-actions",
    prompt="CI/CD pipeline",
    show_default=True,
    help="CI/CD pipeline configuration",
)
def new(name, backend, frontend, database, auth, output_dir, docker, ci):
    """Generate a new full-stack Python + React application."""
    print_banner()

    config = {
        "name": name,
        "backend": backend,
        "frontend": frontend,
        "database": database,
        "auth": auth,
        "docker": docker,
        "ci": ci,
        "output_dir": output_dir,
    }

    console.print(
        Panel.fit(
            f"[bold cyan]Generating application:[/bold cyan] [yellow]{name}[/yellow]\n"
            f"  Backend:  [green]{backend}[/green]\n"
            f"  Frontend: [green]{frontend}[/green]\n"
            f"  Database: [green]{database}[/green]\n"
            f"  Auth:     [green]{auth}[/green]\n"
            f"  Docker:   [green]{'yes' if docker else 'no'}[/green]\n"
            f"  CI/CD:    [green]{ci}[/green]",
            title="⚡ PyReactor Forge",
            border_style="cyan",
        )
    )

    generator = AppGenerator(config)
    try:
        generator.generate()
        print_success(name, config)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


@cli.command()
@click.option(
    "--name",
    "-n",
    prompt="Entity name (singular, PascalCase)",
    help="Entity name, e.g. Product",
)
@click.option(
    "--app-dir",
    "-a",
    default=".",
    help="Path to the generated app directory",
)
def entity(name, app_dir):
    """Add a new entity (model + API + UI) to an existing app."""
    app_path = Path(app_dir)
    try:
        app_config = entities.load_config(app_path)
    except entities.ProjectError as exc:
        print_error(str(exc))
        sys.exit(1)

    console.print(f"\n[bold cyan]⚡ Adding entity:[/bold cyan] [yellow]{name}[/yellow]\n")

    # Interactively collect fields
    fields = []
    console.print("[dim]Define fields (press Enter with no name to finish):[/dim]\n")

    while True:
        field_name = click.prompt("  Field name", default="", show_default=False)
        if not field_name:
            break

        field_type = click.prompt(
            "  Field type",
            type=click.Choice(list(entities.FIELD_TYPES)),
            default="string",
        )
        required = click.confirm("  Required?", default=True)
        fields.append({"name": field_name, "type": field_type, "required": required})
        console.print()

    if not fields:
        console.print("[yellow]No fields defined. Aborting.[/yellow]")
        sys.exit(0)

    gen = EntityGenerator(
        name,
        fields,
        app_config,
        app_path,
        table_names=entities.table_names(app_config),
        plural=entities.resolve_plural(app_path, app_config, name),
    )
    gen.generate()
    entities.upsert_entity(app_config, gen.spec())
    entities.save_config(app_path, app_config)

    console.print(
        f"\n[bold green]✓ Entity [yellow]{name}[/yellow] added successfully![/bold green]"
    )
    console.print("\nFiles created/updated:")
    for f in gen.created_files:
        console.print(f"  [cyan]→[/cyan] {f}")
    _print_migration_hint(app_config)


@cli.command()
def info():
    """Display information about the PyReactor Forge generator."""
    print_banner()
    console.print(
        Panel(
            "[bold]PyReactor Forge[/bold] is a full-stack code generator inspired by JHipster.\n\n"
            "[bold cyan]Supported backends:[/bold cyan]\n"
            "  • [green]FastAPI[/green]  — Modern, fast async Python API framework\n"
            "  • [green]Django[/green]   — Batteries-included Python web framework\n"
            "  • [green]Flask[/green]    — Lightweight Python micro-framework\n\n"
            "[bold cyan]Supported frontends:[/bold cyan]\n"
            "  • [green]React[/green]         — JavaScript (Vite + React)\n"
            "  • [green]React-TS[/green]      — TypeScript (Vite + React + TypeScript)\n\n"
            "[bold cyan]Supported databases:[/bold cyan]\n"
            "  • [green]PostgreSQL[/green] • [green]MySQL[/green] • [green]SQLite[/green]\n\n"
            "[bold cyan]Supported authentication:[/bold cyan]\n"
            "  • [green]JWT[/green] • [green]Session[/green] • [green]OAuth2[/green]\n\n"
            "[bold cyan]Commands:[/bold cyan]\n"
            "  • [yellow]pyforge new[/yellow]     — Scaffold a new application\n"
            "  • [yellow]pyforge entity[/yellow]  — Add a new entity to an existing app\n"
            "  • [yellow]pyforge entity-list[/yellow]   — List the entities in a project\n"
            "  • [yellow]pyforge entity-edit[/yellow]   — Edit an entity and regenerate it\n"
            "  • [yellow]pyforge entity-remove[/yellow] — Safely remove an entity\n"
            "  • [yellow]pyforge import-pydl[/yellow]   — Apply a .pydl model file\n"
            "  • [yellow]pyforge info[/yellow]    — Show this information\n"
            "  • [yellow]pyforge windows[/yellow] — How to install and run on Windows",
            title="ℹ️  About PyReactor Forge",
            border_style="blue",
        )
    )


@cli.command()
def windows():
    """Show how to install and run PyReactor Forge (and generated apps) on Windows."""
    print_banner()
    console.print(
        Panel(
            "[bold]1. Install[/bold]\n"
            "  [dim]# Python 3.11+ from python.org or the Microsoft Store[/dim]\n"
            "  [cyan]py -3 -m pip install --upgrade pyreactor-forge[/cyan]\n"
            "  [dim]# or, isolated:[/dim]\n"
            "  [cyan]py -3 -m pip install pipx; pipx install pyreactor-forge[/cyan]\n\n"
            "[bold]2. If 'pyforge' is not recognized[/bold]\n"
            "  [dim]The Scripts folder is not on PATH. Either call the module directly:[/dim]\n"
            "  [cyan]py -3 -m pyreactor_forge.cli --help[/cyan]\n"
            "  [dim]or add the Scripts folder to PATH — find it with:[/dim]\n"
            "  [cyan]py -3 -c \"import sysconfig; print(sysconfig.get_path('scripts'))\"[/cyan]\n\n"
            "[bold]3. Scaffold an app[/bold]\n"
            "  [cyan]pyforge new --name myapp --backend fastapi --database sqlite[/cyan]\n"
            "  [dim]Paths with spaces need quotes:[/dim]\n"
            "  [cyan]pyforge new -o \"C:\\My Projects\"[/cyan]\n\n"
            "[bold]4. Run the generated backend (PowerShell)[/bold]\n"
            "  [cyan]cd myapp\\backend[/cyan]\n"
            "  [cyan]py -3 -m venv .venv[/cyan]\n"
            "  [cyan].venv\\Scripts\\Activate.ps1[/cyan]\n"
            "  [cyan]pip install -r requirements.txt[/cyan]\n"
            "  [cyan]copy .env.example .env[/cyan]\n"
            "  [cyan]python -m scripts.seed[/cyan]   [dim](creates the admin user)[/dim]\n"
            "  [cyan]uvicorn app.main:app --reload[/cyan]\n"
            "  [dim](Django backend: python manage.py runserver)[/dim]\n\n"
            "  [dim]cmd.exe instead of PowerShell:[/dim]\n"
            "  [cyan].venv\\Scripts\\activate.bat[/cyan]\n"
            "  [dim]Activation blocked? Run once:[/dim]\n"
            "  [cyan]Set-ExecutionPolicy -Scope CurrentUser"
            " -ExecutionPolicy RemoteSigned[/cyan]\n\n"
            "[bold]5. Run the frontend (second terminal)[/bold]\n"
            "  [cyan]cd myapp\\frontend[/cyan]\n"
            "  [cyan]npm install[/cyan]\n"
            "  [cyan]npm run dev[/cyan]\n"
            "  [dim]npm needs Node.js 18+ (nodejs.org or winget install OpenJS.NodeJS.LTS).[/dim]\n"
            "  [dim]If npm install fails on deep paths, enable long paths:[/dim]\n"
            "  [cyan]git config --system core.longpaths true[/cyan]\n\n"
            "[bold]6. Or use Docker Desktop[/bold]\n"
            "  [cyan]docker compose up --build[/cyan]   [dim](WSL 2 backend recommended)[/dim]\n\n"
            "[bold]Shell notes[/bold]\n"
            "  • Windows PowerShell 5.1 has no [cyan]&&[/cyan] — chain with [cyan];[/cyan].\n"
            "  • Use [cyan]py -3[/cyan] rather than [cyan]python[/cyan]"
            "; the Store alias can shadow it.\n"
            "  • Output is UTF-8, so redirecting to a file keeps the box drawing.",
            title="🪟 PyReactor Forge on Windows",
            border_style="cyan",
        )
    )


@cli.command("entity-list")
@click.option("--app-dir", "-a", default=".", help="Path to the generated app directory")
def entity_list(app_dir):
    """List the entities in a generated app."""
    app_path = Path(app_dir)
    try:
        config = entities.load_config(app_path)
    except entities.ProjectError as exc:
        print_error(str(exc))
        sys.exit(1)

    registered = entities.entities_of(config)
    names = entities.known_entity_names(app_path, config)

    if not names:
        console.print("\n[yellow]No entities yet.[/yellow] Add one with "
                      "[cyan]pyforge entity[/cyan] or [cyan]pyforge import-pydl[/cyan].\n")
        return

    table = Table(title=f"Entities in {config.get('name', app_path.name)}", border_style="cyan")
    table.add_column("Entity", style="yellow")
    table.add_column("Plural", style="dim")
    table.add_column("Fields", justify="right")
    table.add_column("Relationships", justify="right")
    table.add_column("Options")
    table.add_column("Tracked")

    for name in names:
        spec = registered.get(name)
        plural = entities.resolve_plural(app_path, config, name)
        if spec is None:
            table.add_row(name, plural, "?", "?", "", "[dim]on disk only[/dim]")
            continue
        options = ", ".join(
            f"{key}={value}" if value is not True else key
            for key, value in sorted(spec.get("options", {}).items())
        )
        table.add_row(
            name,
            plural,
            str(len(spec.get("fields", []))),
            str(len(spec.get("relationships", []))),
            options,
            "[green]yes[/green]",
        )

    console.print()
    console.print(table)
    console.print()


@cli.command("import-pydl")
@click.argument("pydl_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--app-dir", "-a", default=".", help="Path to the generated app directory")
@click.option("--dry-run", is_flag=True, help="Show what would change and stop")
@click.option("--yes", "-y", is_flag=True, help="Do not ask for confirmation")
def import_pydl(pydl_file, app_dir, dry_run, yes):
    """Create or update entities from a .pydl file (JHipster JDL syntax)."""
    app_path = Path(app_dir)
    try:
        config = entities.load_config(app_path)
    except entities.ProjectError as exc:
        print_error(str(exc))
        sys.exit(1)

    if pydl_file.suffix != ".pydl":
        console.print(
            f"[yellow]Warning:[/yellow] {pydl_file.name} does not use the .pydl extension."
        )

    try:
        model = pydl.parse_file(pydl_file)
    except pydl.PydlError as exc:
        console.print(f"\n[bold red]{pydl_file.name} has "
                      f"{len(exc.problems)} problem(s):[/bold red]\n")
        for problem in exc.problems:
            console.print(f"  [red]•[/red] {problem}")
        console.print()
        sys.exit(1)

    specs = pydl.to_entity_specs(model)
    if not specs:
        console.print("[yellow]No entities declared in this file.[/yellow]")
        return

    known = set(entities.known_entity_names(app_path, config))

    plan = Table(title=f"{pydl_file.name} → {config.get('name', app_path.name)}",
                 border_style="cyan")
    plan.add_column("Entity", style="yellow")
    plan.add_column("Action")
    plan.add_column("Fields", justify="right")
    plan.add_column("Relationships", justify="right")
    for spec in specs:
        action = "[yellow]update[/yellow]" if spec["name"] in known else "[green]create[/green]"
        plan.add_row(
            spec["name"],
            action,
            str(len(spec["fields"])),
            str(len(spec["relationships"])),
        )

    console.print()
    console.print(plan)

    notes = pydl.describe_unsupported(model)
    if notes:
        console.print()
        for note in notes:
            console.print(f"  [dim]note:[/dim] {note}")

    updates = [spec["name"] for spec in specs if spec["name"] in known]
    if updates:
        console.print(
            f"\n[yellow]Existing entities will be overwritten:[/yellow] {', '.join(updates)}"
        )

    if dry_run:
        console.print("\n[dim]Dry run - nothing was written.[/dim]\n")
        return

    if not yes and not click.confirm("\nApply these changes?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    plurals = {
        spec["name"]: entities.resolve_plural(app_path, config, spec["name"])
        for spec in specs
    }
    known_tables = entities.table_names(config)
    known_tables.update(
        {spec["name"]: spec.get("table") or plurals[spec["name"]] for spec in specs}
    )

    created = []
    for spec in specs:
        if spec["name"] in known:
            entities.backup_files(
                app_path,
                entities.owned_files(app_path, config, spec["name"]),
                f"import-{spec['name']}",
            )
        generator = EntityGenerator(
            spec["name"],
            spec["fields"],
            config,
            app_path,
            relationships=spec["relationships"],
            options=spec["options"],
            table=spec.get("table"),
            table_names=known_tables,
            plural=plurals[spec["name"]],
        )
        generator.generate()
        entities.upsert_entity(config, generator.spec())
        created.extend(generator.created_files)

    entities.save_config(app_path, config)

    console.print(f"\n[bold green]✓ {len(specs)} entit"
                  f"{'y' if len(specs) == 1 else 'ies'} applied.[/bold green]")
    for path in created:
        console.print(f"  [cyan]→[/cyan] {path}")
    _print_migration_hint(config)


@cli.command("entity-edit")
@click.option("--name", "-n", prompt="Entity name", help="Entity to edit, e.g. Product")
@click.option("--app-dir", "-a", default=".", help="Path to the generated app directory")
@click.option("--add-field", multiple=True, metavar="NAME:TYPE[:required]",
              help="Add a field (repeatable)")
@click.option("--remove-field", multiple=True, metavar="NAME", help="Remove a field (repeatable)")
@click.option("--yes", "-y", is_flag=True, help="Do not ask for confirmation")
def entity_edit(name, app_dir, add_field, remove_field, yes):
    """Edit an entity's fields and regenerate its model, API and UI."""
    app_path = Path(app_dir)
    try:
        config = entities.load_config(app_path)
    except entities.ProjectError as exc:
        print_error(str(exc))
        sys.exit(1)

    if name not in entities.known_entity_names(app_path, config):
        print_error(
            f"Entity '{name}' not found. Run [cyan]pyforge entity-list[/cyan] to see what exists."
        )
        sys.exit(1)

    spec = entities.entity_spec(app_path, config, name)
    if not spec["fields"] and name not in entities.entities_of(config):
        console.print(
            f"\n[yellow]'{name}' predates the entity registry, "
            f"so its fields are unknown.[/yellow]\n"
            "[dim]Define them again below; the generated files will be rewritten.[/dim]"
        )

    try:
        for raw in add_field:
            field = entities.parse_field_spec(raw)
            spec["fields"] = [f for f in spec["fields"] if f["name"] != field["name"]]
            spec["fields"].append(field)
        for field_name in remove_field:
            if not any(f["name"] == field_name for f in spec["fields"]):
                print_error(f"'{name}' has no field '{field_name}'.")
                sys.exit(1)
            spec["fields"] = [f for f in spec["fields"] if f["name"] != field_name]
    except ValueError as exc:
        print_error(str(exc))
        sys.exit(1)

    if not add_field and not remove_field:
        spec["fields"] = _edit_fields_interactively(name, spec["fields"])

    if not spec["fields"]:
        console.print("[yellow]An entity needs at least one field. Aborted.[/yellow]")
        return

    _print_field_table(name, spec["fields"], spec.get("relationships", []))

    if not yes and not click.confirm("\nRegenerate this entity?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    backup = entities.backup_files(
        app_path, entities.owned_files(app_path, config, name), f"edit-{name}"
    )

    generator = EntityGenerator(
        name,
        spec["fields"],
        config,
        app_path,
        relationships=spec.get("relationships"),
        options=spec.get("options"),
        table=spec.get("table"),
        table_names=entities.table_names(config),
        plural=spec.get("plural") or entities.resolve_plural(app_path, config, name),
    )
    generator.generate()
    entities.upsert_entity(config, generator.spec())
    entities.save_config(app_path, config)

    console.print(f"\n[bold green]✓ Entity {name} updated.[/bold green]")
    for path in generator.created_files:
        console.print(f"  [cyan]→[/cyan] {path}")
    if backup is not None:
        console.print(f"\n[dim]Previous version backed up to "
                      f"{backup.relative_to(app_path)}[/dim]")
    _print_migration_hint(config)


@cli.command("entity-remove")
@click.option("--name", "-n", prompt="Entity name", help="Entity to remove, e.g. Product")
@click.option("--app-dir", "-a", default=".", help="Path to the generated app directory")
@click.option("--dry-run", is_flag=True, help="Show what would be removed and stop")
@click.option("--yes", "-y", is_flag=True, help="Do not ask for confirmation")
@click.option("--no-backup", is_flag=True, help="Do not copy files to .pyforge-backups first")
@click.option("--force", is_flag=True, help="Remove even if other entities reference it")
def entity_remove(name, app_dir, dry_run, yes, no_backup, force):
    """Remove an entity: its files, its routes and its registry entry."""
    app_path = Path(app_dir)
    try:
        config = entities.load_config(app_path)
    except entities.ProjectError as exc:
        print_error(str(exc))
        sys.exit(1)

    if name not in entities.known_entity_names(app_path, config):
        print_error(
            f"Entity '{name}' not found. Run [cyan]pyforge entity-list[/cyan] to see what exists."
        )
        sys.exit(1)

    plan = entities.removal_plan(app_path, config, name)

    console.print(f"\n[bold]Removing entity[/bold] [yellow]{name}[/yellow]\n")
    if plan["delete"]:
        console.print("[bold]Files to delete:[/bold]")
        for path in plan["delete"]:
            console.print(f"  [red]−[/red] {path}")
    if plan["update"]:
        console.print("\n[bold]Registrations to strip:[/bold]")
        for path in plan["update"]:
            console.print(f"  [yellow]~[/yellow] {path}")
    if not plan["delete"] and not plan["update"]:
        console.print("[yellow]Nothing to remove - no files or registrations found.[/yellow]")

    if plan["dependents"]:
        console.print(
            f"\n[bold red]Referenced by:[/bold red] {', '.join(plan['dependents'])}"
        )
        if force:
            console.print(
                "[dim]--force: those entities will be regenerated without the "
                f"relationship to {name}.[/dim]"
            )
        else:
            console.print(
                "[dim]Those entities have relationships pointing at "
                f"{name}. Edit or remove them first, or pass --force.[/dim]\n"
            )
            if not dry_run:
                sys.exit(1)

    if dry_run:
        console.print("[dim]Dry run - nothing was changed.[/dim]\n")
        return

    if not yes and not click.confirm(f"\nRemove {name}?", default=False):
        console.print("[yellow]Aborted.[/yellow]")
        return

    result = entities.remove_entity(
        app_path, config, name, backup=not no_backup, cascade=force
    )

    console.print(f"\n[bold green]✓ Entity {name} removed.[/bold green]")
    for regenerated in result.get("regenerated", []):
        console.print(f"  [cyan]~[/cyan] {regenerated} regenerated without the relationship")
    if result["backup"]:
        console.print(f"[dim]Backup: {result['backup']}[/dim]")
    console.print(
        f"\n[yellow]The database table '{result['table']}' still exists.[/yellow]\n"
        "[dim]Generate a migration to drop it when you are ready.[/dim]\n"
    )


def _print_field_table(name, fields, relationships=None):
    table = Table(title=f"{name} fields", border_style="cyan")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Field", style="yellow")
    table.add_column("Type")
    table.add_column("Required")
    for index, field in enumerate(fields, start=1):
        table.add_row(
            str(index),
            field["name"],
            field["type"],
            "[green]yes[/green]" if field.get("required") else "[dim]no[/dim]",
        )
    console.print()
    console.print(table)
    for relationship in relationships or []:
        console.print(
            f"  [dim]relationship:[/dim] {relationship['kind']} → "
            f"{relationship['target']} [dim]as[/dim] {relationship['name']}"
        )


def _edit_fields_interactively(name, fields):
    fields = [dict(field) for field in fields]
    while True:
        _print_field_table(name, fields)
        console.print(
            "\n[dim]a[/dim] add field   [dim]r[/dim] remove field   "
            "[dim]t[/dim] toggle required   [dim]d[/dim] done\n"
        )
        choice = click.prompt("  Action", type=click.Choice(["a", "r", "t", "d"]), default="d")

        if choice == "d":
            return fields

        if choice == "a":
            field_name = click.prompt("  Field name", default="", show_default=False)
            if not field_name:
                continue
            if any(f["name"] == field_name for f in fields):
                console.print(f"[yellow]'{field_name}' already exists.[/yellow]")
                continue
            field_type = click.prompt(
                "  Field type",
                type=click.Choice(list(entities.FIELD_TYPES)),
                default="string",
            )
            required = click.confirm("  Required?", default=True)
            fields.append({"name": field_name, "type": field_type, "required": required})
            continue

        if not fields:
            console.print("[yellow]No fields to change.[/yellow]")
            continue

        index = click.prompt("  Field #", type=click.IntRange(1, len(fields)))
        if choice == "r":
            removed = fields.pop(index - 1)
            console.print(f"[dim]removed {removed['name']}[/dim]")
        else:
            field = fields[index - 1]
            field["required"] = not field.get("required", False)


def _print_migration_hint(config):
    backend = config.get("backend", "fastapi")
    if backend == "django":
        command = "python manage.py makemigrations && python manage.py migrate"
    elif backend == "flask":
        console.print(
            "\n[dim]Schema changed - new tables appear on the next start "
            "(db.create_all()); altered columns need a manual migration.[/dim]\n"
        )
        return
    else:
        command = 'alembic revision --autogenerate -m "entities" && alembic upgrade head'
    console.print(
        f"\n[dim]Schema changed - update the database with:[/dim] [cyan]{command}[/cyan]\n"
    )


if __name__ == "__main__":
    cli()
