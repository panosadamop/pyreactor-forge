"""Display utilities for PyReactor Forge CLI."""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

IS_WINDOWS = sys.platform == "win32"

# Windows PowerShell 5.1 has no && chain operator, so separate commands with ;
FRONTEND_CMD = (
    "cd frontend; npm install; npm run dev"
    if IS_WINDOWS
    else "cd frontend && npm install && npm run dev"
)


def print_banner():
    console.print()
    console.print(
        "[bold cyan]⚡ PyReactor Forge[/bold cyan] [dim]— Full-stack Python + React Generator[/dim]"
    )
    console.print()


def _backend_steps(run_cmd: str, seed_cmd: str, windows: bool) -> str:
    """Backend bootstrap commands for the given platform.

    Windows ships the venv launchers under .venv\\Scripts (not .venv/bin) and
    has no `source`, so the activation line differs; `py -3` is the launcher
    that is on PATH even when `python` is not.
    """
    if windows:
        return (
            f"  [dim]# Backend (PowerShell)[/dim]\n"
            f"  [cyan]cd backend[/cyan]\n"
            f"  [cyan]py -3 -m venv .venv[/cyan]\n"
            f"  [cyan].venv\\Scripts\\Activate.ps1[/cyan]\n"
            f"  [dim]# cmd.exe: .venv\\Scripts\\activate.bat[/dim]\n"
            f"  [cyan]pip install -r requirements.txt[/cyan]\n"
            f"  [cyan]copy .env.example .env[/cyan]\n"
            f"  [cyan]{seed_cmd}[/cyan]   [dim]# creates the admin user[/dim]\n"
            f"  [cyan]{run_cmd}[/cyan]\n"
        )
    return (
        f"  [dim]# Backend[/dim]\n"
        f"  [cyan]cd backend && python -m venv .venv && source .venv/bin/activate[/cyan]\n"
        f"  [cyan]pip install -r requirements.txt[/cyan]\n"
        f"  [cyan]cp .env.example .env[/cyan]\n"
        f"  [cyan]{seed_cmd}[/cyan]   [dim]# creates the admin user[/dim]\n"
        f"  [cyan]{run_cmd}[/cyan]\n"
    )


def print_success(name: str, config: dict):
    slug = name.lower().replace(" ", "-")
    backend = config["backend"]
    run_cmd = (
        "python manage.py runserver"
        if backend == "django"
        else "uvicorn app.main:app --reload"
    )
    seed_cmd = (
        "python manage.py seed"
        if backend == "django"
        else "python -m scripts.seed"
    )

    other_platform = (
        "  [dim]# macOS/Linux: python -m venv .venv && source .venv/bin/activate[/dim]\n"
        if IS_WINDOWS
        else "  [dim]# Windows: py -3 -m venv .venv; .venv\\Scripts\\Activate.ps1[/dim]\n"
    )

    console.print()
    console.print(
        Panel(
            f"[bold green]Application '{name}' generated successfully![/bold green]\n\n"
            f"[bold]Get started:[/bold]\n\n"
            f"  [cyan]cd {slug}[/cyan]\n\n"
            f"{_backend_steps(run_cmd, seed_cmd, IS_WINDOWS)}"
            f"{other_platform}\n"
            f"  [dim]# Frontend (new terminal)[/dim]\n"
            f"  [cyan]{FRONTEND_CMD}[/cyan]\n\n"
            f"  [dim]# Or run everything with Docker:[/dim]\n"
            f"  [cyan]docker-compose up --build[/cyan]\n\n"
            f"  [bold]API docs:[/bold] http://localhost:8000/docs\n"
            f"  [bold]Frontend:[/bold] http://localhost:5173",
            title="✅ Success",
            border_style="green",
        )
    )
    console.print()
    console.print(
        "[dim]Tip: Add entities with [/dim][cyan]pyforge entity[/cyan]"
        "[dim] inside your project.[/dim]"
    )
    if IS_WINDOWS:
        console.print(
            "[dim]Running on Windows? See [/dim][cyan]pyforge windows[/cyan]"
            "[dim] for setup notes.[/dim]"
        )
    console.print()


def print_error(message: str):
    console.print()
    console.print(f"[bold red]Error:[/bold red] {message}")
    console.print()
