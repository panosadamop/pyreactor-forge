"""PyReactor CLI - JHipster-inspired full-stack generator for Python + React."""

import click
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from pyreactor import __version__
from pyreactor.generators.app import AppGenerator
from pyreactor.generators.entity import EntityGenerator
from pyreactor.utils.display import print_banner, print_success, print_error


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
@click.version_option(version=__version__, prog_name="PyReactor")
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
            title="⚡ PyReactor",
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
@click.option("--name", "-n", prompt="Entity name (singular, PascalCase)", help="Entity name, e.g. Product")
@click.option(
    "--app-dir",
    "-a",
    default=".",
    help="Path to the generated app directory",
)
def entity(name, app_dir):
    """Add a new entity (model + API + UI) to an existing app."""
    app_path = Path(app_dir)
    config_file = app_path / ".pyreactor.json"

    if not config_file.exists():
        console.print(
            "[red]Error:[/red] No .pyreactor.json found. "
            "Run this command inside a PyReactor-generated project."
        )
        sys.exit(1)

    import json
    with open(config_file, encoding="utf-8") as f:
        app_config = json.load(f)

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
            type=click.Choice(["string", "integer", "float", "boolean", "date", "datetime", "text"]),
            default="string",
        )
        required = click.confirm("  Required?", default=True)
        fields.append({"name": field_name, "type": field_type, "required": required})
        console.print()

    if not fields:
        console.print("[yellow]No fields defined. Aborting.[/yellow]")
        sys.exit(0)

    gen = EntityGenerator(name, fields, app_config, app_path)
    gen.generate()

    console.print(f"\n[bold green]✓ Entity [yellow]{name}[/yellow] added successfully![/bold green]")
    console.print("\nFiles created/updated:")
    for f in gen.created_files:
        console.print(f"  [cyan]→[/cyan] {f}")


@cli.command()
def info():
    """Display information about the PyReactor generator."""
    print_banner()
    console.print(
        Panel(
            "[bold]PyReactor[/bold] is a full-stack code generator inspired by JHipster.\n\n"
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
            "  • [yellow]pyreactor new[/yellow]     — Scaffold a new application\n"
            "  • [yellow]pyreactor entity[/yellow]  — Add a new entity to an existing app\n"
            "  • [yellow]pyreactor info[/yellow]    — Show this information",
            title="ℹ️  About PyReactor",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    cli()
