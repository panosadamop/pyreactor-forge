# ⚡ PyReactor Forge

> A full-stack application generator for Python + React.

PyReactor Forge scaffolds production-ready web applications with a Python backend (FastAPI, Django, or Flask) and a React frontend — with authentication, database integration, Docker, CI/CD, and more — in under 60 seconds.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Backends** | FastAPI (async, SQLAlchemy 2), Django (DRF), Flask |
| **Frontend** | React + Vite (JavaScript or TypeScript) + Tailwind CSS |
| **Database** | PostgreSQL, MySQL, SQLite (with Alembic migrations) |
| **Auth** | JWT (Bearer token), Session, OAuth2 |
| **Entity generator** | Add models + CRUD API + React UI with one command |
| **Docker** | Multi-stage Dockerfile + docker-compose for dev & prod |
| **CI/CD** | GitHub Actions or GitLab CI pipelines |
| **Code quality** | Ruff, mypy, ESLint, Vitest pre-configured |

---

## 📦 Installation

```bash
pip install pyreactor-forge
```

> Installs as **`pyreactor-forge`**. The terminal command is **`pyforge`** and the
> import package is `pyreactor_forge`.

Or from source:

```bash
git clone https://github.com/panosadamop/pyreactor-forge
cd pyreactor-forge
pip install -e .
```

---

## 🚀 Quick Start

### 1. Generate a new application

```bash
pyforge new
```

You'll be prompted to configure your app:

```
Application name: my-saas
Backend framework: fastapi
Frontend framework: react-ts
Database: postgresql
Authentication type: jwt
Include Docker configuration? Yes
CI/CD pipeline: github-actions
```

Or pass everything as flags:

```bash
pyforge new \
  --name my-saas \
  --backend fastapi \
  --frontend react-ts \
  --database postgresql \
  --auth jwt \
  --docker \
  --ci github-actions
```

### 2. Start developing

```bash
cd my-saas
make dev          # starts backend + frontend concurrently
```

Or manually:

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Visit:
- **Frontend**: http://localhost:5173
- **API docs**: http://localhost:8000/docs

### 3. Add an entity

```bash
cd my-saas
pyforge entity
```

```
Entity name: Product
Field name: name        | type: string   | required: yes
Field name: price       | type: float    | required: yes
Field name: description | type: text     | required: no
Field name:             | (press Enter to finish)
```

This generates:
- `backend/app/models/product.py` — SQLAlchemy model
- `backend/app/schemas/product.py` — Pydantic schemas
- `backend/app/routers/products.py` — Full CRUD router
- `frontend/src/services/productService.ts` — Typed API client
- `frontend/src/pages/ProductPage.tsx` — Data table UI
- Updates `main.py` and `App.tsx` automatically

---

## 📁 Generated Project Structure

```
my-saas/
├── backend/                    # Python backend
│   ├── app/
│   │   ├── main.py             # FastAPI app factory
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic settings
│   │   │   ├── database.py     # SQLAlchemy async engine
│   │   │   ├── security.py     # JWT + bcrypt
│   │   │   └── deps.py         # FastAPI dependencies
│   │   ├── models/             # SQLAlchemy models
│   │   ├── routers/            # API route handlers
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # Business logic layer
│   ├── tests/                  # pytest + pytest-asyncio
│   ├── migrations/             # Alembic migrations
│   ├── requirements.txt
│   ├── pyproject.toml          # Ruff + mypy config
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                   # React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx             # Router + auth guard
│   │   ├── pages/             # Route-level components
│   │   ├── components/
│   │   │   ├── layout/        # Layout + sidebar
│   │   │   └── ui/            # Reusable UI components
│   │   ├── services/          # Axios API clients
│   │   ├── hooks/             # React Query hooks
│   │   ├── store/             # Zustand stores
│   │   └── types/             # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── .github/workflows/          # GitHub Actions CI/CD
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile
├── .pyforge.json             # Project metadata
└── README.md
```

---

## 🛠 Commands

| Command | Description |
|---|---|
| `pyforge new` | Scaffold a new full-stack application |
| `pyforge entity` | Add a new entity (model + API + UI) to an existing app |
| `pyforge info` | Show supported technologies and commands |
| `pyforge --version` | Display the PyReactor Forge version |

### Makefile targets (inside generated project)

| Target | Description |
|---|---|
| `make dev` | Start backend + frontend concurrently |
| `make install` | Install all dependencies |
| `make migrate` | Run database migrations |
| `make test` | Run backend + frontend tests |
| `make lint` | Lint backend (ruff + mypy) + frontend (eslint) |
| `make docker-up` | Start all services with Docker Compose |
| `make docker-down` | Stop Docker Compose services |

---

## ⚙️ Tech Stack (generated app)

### Backend (FastAPI — default)
- **FastAPI** — async Python web framework
- **SQLAlchemy 2** (async) — ORM with Alembic migrations
- **Pydantic v2** — data validation and settings
- **python-jose** — JWT tokens
- **bcrypt** — password hashing
- **pytest + pytest-asyncio** — testing
- **ruff + mypy** — linting and type checking

### Frontend
- **React 18** + **Vite** — blazing fast dev server
- **TypeScript** — full type safety
- **Tailwind CSS** — utility-first styling
- **React Router v6** — client-side routing
- **TanStack Query** — server state management
- **Zustand** — client state (with persistence)
- **React Hook Form** + **Zod** — form validation
- **Axios** — HTTP client with interceptors
- **Lucide React** — icons

---

## 🗺 Roadmap

- [ ] Interactive TUI (Textual-based) in addition to CLI
- [ ] PostgreSQL full-text search support
- [ ] Websocket support
- [ ] Admin panel generation
- [ ] Deployment presets (Railway, Fly.io, Render, AWS)
- [ ] Multi-tenancy support
- [ ] OpenAPI client auto-generation from backend schema

---

## 📄 License

MIT © Panagiotis Adamopoulos
