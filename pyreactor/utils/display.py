"""Display utilities for PyReactor CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_banner():
    console.print()
    console.print(
        "[bold cyan]⚡ PyReactor[/bold cyan] [dim]— Full-stack Python + React Generator[/dim]"
    )
    console.print()


def print_success(name: str, config: dict):
    slug = name.lower().replace(" ", "-")
    backend = config["backend"]
    run_cmd = (
        "python manage.py runserver"
        if backend == "django"
        else "uvicorn app.main:app --reload"
    )

    console.print()
    console.print(
        Panel(
            f"[bold green]Application '{name}' generated successfully![/bold green]\n\n"
            f"[bold]Get started:[/bold]\n\n"
            f"  [cyan]cd {slug}[/cyan]\n\n"
            f"  [dim]# Backend[/dim]\n"
            f"  [cyan]cd backend && python -m venv .venv && source .venv/bin/activate[/cyan]\n"
            f"  [cyan]pip install -r requirements.txt[/cyan]\n"
            f"  [cyan]cp .env.example .env[/cyan]\n"
            f"  [cyan]{run_cmd}[/cyan]\n\n"
            f"  [dim]# Frontend (new terminal)[/dim]\n"
            f"  [cyan]cd frontend && npm install && npm run dev[/cyan]\n\n"
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
        "[dim]Tip: Add entities with [/dim][cyan]pyreactor entity[/cyan][dim] inside your project.[/dim]"
    )
    console.print()


def print_error(message: str):
    console.print()
    console.print(f"[bold red]Error:[/bold red] {message}")
    console.print()
