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
| **PyDL models** | Declare entities in JHipster JDL syntax and import them |
| **Entity lifecycle** | List, edit and safely remove entities from the CLI |
| **Naming** | Real English pluralisation — `Category` → `categories` |
| **Admin seeding** | `make seed` creates the first superuser account |
| **Docker** | Multi-stage Dockerfile + docker-compose for dev & prod |
| **CI/CD** | GitHub Actions or GitLab CI pipelines |
| **Code quality** | Ruff, mypy, ESLint, Vitest pre-configured |

---

## 🆕 What's new

Everything below is in the current version; each entry links to its section.

**[PyDL model files](#-pydl--model-your-domain-in-one-file)** — declare your
whole domain in JHipster's JDL syntax in a `.pydl` file and apply it with
`pyforge import-pydl`. Entities, enums, relationships, validations and options
all parse; errors are reported together with line numbers and nothing is
written until the file is valid. `--dry-run` shows the plan first.

**[Entity lifecycle commands](#-managing-entities)** — `pyforge entity-list`,
`pyforge entity-edit` and `pyforge entity-remove`. Editing regenerates an
entity's model, schemas, router, API client and page while keeping its
relationships and options. Removal deletes the files *and* unregisters the
entity (router include, React route, Django router, Flask blueprint), refuses
while another entity still references it, and snapshots everything it touches
to `.pyforge-backups/` first.

**Entity registry** — `.pyforge.json` now records every entity: its fields,
relationships, options, table, plural and the files it owns. That is what makes
editing and safe removal possible, and it is written by `pyforge entity` and
`pyforge import-pydl` alike. Projects created before the registry existed are
handled by rediscovering their files from the naming conventions.

**[Correct pluralisation](#naming-and-pluralisation)** — `Category` now maps to
`categories` (table, API prefix, router module and React route), with irregular
and uncountable nouns handled. Projects generated with 0.1.0 keep their original
paths.

**[Admin seeding](#3-create-the-admin-user)** — a generated app ships with a
seed command (`make seed`, or `python -m scripts.seed` / `python manage.py
seed`) that creates the first superuser. No password is hardcoded: supply one,
or let it generate and print a random one once. Re-running it resets the
password, so it doubles as a recovery tool.

**[Windows support](#-running-on-windows)** — `pyforge windows` prints the
PowerShell equivalent of every setup step, the CLI's "get started" panel adapts
to the host OS, and console output is forced to UTF-8 so redirecting to a file
no longer fails on the legacy code page.

**Django fixes** — generated Django projects now include the `TEMPLATES` and
`WSGI_APPLICATION` settings plus a `wsgi.py`, without which every `manage.py`
command failed the system check. Entities generated for Django are also
registered in the app's model registry and DRF router instead of sitting unused.

---

## 📦 Installation

```bash
pip install pyreactor-forge
```

> Installs as **`pyreactor-forge`**. The terminal command is **`pyforge`** and the
> import package is `pyreactor_forge`.

> On Windows, see [Running on Windows](#-running-on-windows) for the PowerShell
> equivalents (or run `pyforge windows`).

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

### 3. Create the admin user

A freshly generated app has **no users** — seed the first superuser account:

```bash
make seed

# or, from the backend directory
python -m scripts.seed          # FastAPI / Flask
python manage.py seed           # Django
```

Defaults to email `admin@example.com` / username `admin`. Override with
`--email`, `--username`, `--password`, or the `ADMIN_EMAIL`, `ADMIN_USERNAME`
and `ADMIN_PASSWORD` environment variables. When no password is supplied a
random one is generated and printed once:

```
Admin user created.
  email:    admin@example.com
  username: admin
  password: L-TaVKlZRUMncDuA
This password is shown once - store it now.
```

Re-running the command resets the password and re-applies superuser rights, so
it doubles as a password reset. Log in with the **email** (FastAPI/Flask) or the
**username** (Django admin at `/admin/`).

### 4. Add an entity

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

## 🪟 Running on Windows

Everything above works on Windows — the paths and shell syntax just differ. The
same instructions are available offline from the CLI:

```powershell
pyforge windows
```

### Install

```powershell
# Python 3.11+ from python.org or the Microsoft Store
py -3 -m pip install --upgrade pyreactor-forge

# or, isolated:
py -3 -m pip install pipx
pipx install pyreactor-forge
```

**`pyforge` is not recognized?** The Scripts folder isn't on `PATH`. Either call
the module directly, or add that folder to `PATH`:

```powershell
py -3 -m pyreactor_forge.cli --help
py -3 -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

### Generate and run an app

```powershell
pyforge new --name my-saas --backend fastapi --database postgresql

# Backend
cd my-saas\backend
py -3 -m venv .venv
.venv\Scripts\Activate.ps1      # cmd.exe: .venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
python -m scripts.seed          # creates the admin user
uvicorn app.main:app --reload   # Django backend: python manage.py runserver

# Frontend (second terminal)
cd my-saas\frontend
npm install
npm run dev
```

If PowerShell refuses to run the activation script, allow local scripts once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Or skip the local toolchain entirely and use Docker Desktop (WSL 2 backend
recommended):

```powershell
docker compose up --build
```

### Notes

- Windows PowerShell 5.1 has no `&&` chain operator — separate commands with `;`.
- Use `py -3` rather than `python`; the Microsoft Store alias can shadow it.
- `npm install` on deeply nested paths may need long paths enabled:
  `git config --system core.longpaths true`.
- CLI output is forced to UTF-8, so `pyforge info > out.txt` keeps the box
  drawing intact instead of failing on the legacy cp1252 code page.
- `make` isn't available by default, so run the backend and frontend commands
  above instead of the Makefile targets (or install `make` via
  `winget install GnuWin32.Make` / use WSL).

---

## 🧩 PyDL — model your domain in one file

PyDL is JHipster's JDL, unchanged: the same `entity`, `enum`, `relationship`
and option declarations, the same validations, the same type names. Files use
the **`.pydl`** extension and are applied with `pyforge import-pydl`.

```pydl
// shop.pydl
entity Category {
  name String required unique maxlength(50)
  description TextBlob
}

entity Product(products_tbl) {
  name String required minlength(2) maxlength(100) pattern(/^[A-Za-z0-9 -]+$/)
  sku String required unique
  price BigDecimal required min(0) max(999999)
  stock Integer
  status Status required
  releasedOn LocalDate
}

enum Status {
  DRAFT, ACTIVE, DISCONTINUED
}

entity Tag {
  label String required
}

relationship ManyToOne {
  Product{category(name) required} to Category{products}
}

relationship ManyToMany {
  Product{tags} to Tag{products}
}

paginate Product, Category with pagination
```

```bash
pyforge import-pydl shop.pydl --dry-run   # show the plan, change nothing
pyforge import-pydl shop.pydl             # generate model + API + UI per entity
```

Each entity produces the same files `pyforge entity` does — model, schemas,
CRUD router, typed API client and a React page — plus the foreign keys,
relationships and validations declared in the file. Re-importing an existing
entity overwrites it (the previous version is copied to `.pyforge-backups/`).

### Naming and pluralisation

Entity names are singular PascalCase (`Category`, `OrderItem`). Everything
plural is derived with real English rules, so `Category` becomes
**`categories`** — never `categorys`:

| Entity | Table | API prefix | Router module | React route |
|---|---|---|---|---|
| `Category` | `categories` | `/api/categories` | `routers/categories.py` | `/categories` |
| `Box` | `boxes` | `/api/boxes` | `routers/boxes.py` | `/boxes` |
| `Person` | `people` | `/api/people` | `routers/people.py` | `/people` |
| `Analysis` | `analyses` | `/api/analyses` | `routers/analyses.py` | `/analyses` |
| `Sheep` | `sheep` | `/api/sheep` | `routers/sheep.py` | `/sheep` |

The rules cover `-y → -ies`, `-s/-x/-z/-ch/-sh → -es`, `-is → -es`,
`-f/-fe → -ves` for the words that take it (`knife → knives`, but
`roof → roofs`), the common `-o → -oes` words, irregulars (`person → people`,
`child → children`, `index → indices`) and uncountables (`sheep`, `series`,
`news`, `data`). A compound name is lowercased into one word and pluralised on
its ending, so `OrderItem` gives `orderitems`.

Override the table name only — the API path and file names keep the derived
plural — with JDL's parenthesised form:

```pydl
entity Category(product_categories) {
  name String required
}
```

> **Projects generated with 0.1.0** used `name + "s"` (`categorys`). They keep
> working: the plural each entity actually uses is recorded in `.pyforge.json`,
> and for entities generated before that field existed it is detected from the
> files on disk. `entity-edit` regenerates them in place and `entity-remove`
> finds and unregisters them under their original names — nothing is renamed
> behind your back. To adopt the new spelling for an existing entity, remove it
> and re-import it.

### Types

| PyDL type | Python / column |
|---|---|
| `String`, `UUID`, `Duration` | `str` — `String(maxlength or 255)` |
| `TextBlob`, `Blob`, `AnyBlob`, `ImageBlob` | `str` — `Text` |
| `Integer`, `Long` | `int` |
| `BigDecimal`, `Float`, `Double` | `float` |
| `Boolean` | `bool` |
| `LocalDate` | `date` |
| `Instant`, `ZonedDateTime` | `datetime` |
| an `enum` you declared | `str` column + `Literal[...]` schema + TS union |

### Validations

`required`, `unique`, `minlength(n)`, `maxlength(n)`, `min(n)`, `max(n)`,
`pattern(/regex/)`. They become column constraints (`nullable`, `unique`,
`String(n)`) **and** Pydantic constraints (`min_length`, `max_length`, `ge`,
`le`, `pattern`), so bad input is rejected with a 422 before it reaches the
database.

### Relationships

`OneToMany`, `ManyToOne`, `OneToOne` and `ManyToMany` work as in JDL — the
foreign key lands on the same side JHipster puts it on, injected field names
and `(displayField)` are honoured, and `required` inside the braces makes the
key non-nullable. `ManyToMany` generates the association table. A relationship
may target the built-in `User`.

### Options

`paginate`, `readOnly` and `skipClient` are applied (`readOnly` generates no
write endpoints; `skipClient` generates no React files). `dto`, `service`,
`filter`, `microservice` and friends are Java/JHipster concepts with no
equivalent here: they parse, and the import reports them as ignored rather
than failing. `application { … }` blocks are skipped with a note — use
`pyforge new` to configure the application itself.

Syntax and semantic errors are reported together, with line numbers, and
nothing is written until the file is valid:

```
shop.pydl has 2 problem(s):

  • line 7: unknown type 'Money' for Product.price (known types: ...)
  • line 21: relationship references unknown entity 'Categorie'
```

---

## ✏️ Managing entities

```bash
pyforge entity-list                          # what exists, and what is tracked
pyforge entity-edit --name Product           # interactive field editor
pyforge entity-remove --name Product         # safe removal
```

### Editing

`pyforge entity-edit` opens an interactive editor (add, remove, toggle
required) and regenerates the entity's model, schemas, router, service and
page. Relationships and options declared in PyDL are preserved. For scripts,
skip the prompts:

```bash
pyforge entity-edit -n Product --add-field weight:float --remove-field createdBy --yes
```

The previous version of every file is copied to `.pyforge-backups/` first.

### Removing

`pyforge entity-remove` deletes the entity's files **and** unregisters it —
the router import and `include_router` line in `main.py`, the import and
`<Route>` in `App.tsx` (or the Django model/router registration, or the Flask
blueprint), plus its `.pyforge.json` entry.

It is deliberately cautious:

- `--dry-run` prints exactly what would be deleted and stripped.
- Removal is **refused** while another entity has a relationship pointing at
  it, naming the entities that do.
- `--force` removes anyway and regenerates those entities without the dangling
  relationship, so the project still compiles.
- Everything it touches is backed up to `.pyforge-backups/<timestamp>-remove-<Entity>/`
  unless you pass `--no-backup`.
- The database table is **not** dropped — the command tells you to write that
  migration yourself.

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
│   ├── scripts/                # seed.py — creates the admin user
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
├── .pyforge.json             # Project metadata + entity registry
├── .pyforge-backups/         # Snapshots taken before edits/removals
└── README.md
```

---

## 🛠 Commands

| Command | Description |
|---|---|
| `pyforge new` | Scaffold a new full-stack application |
| `pyforge entity` | Add a new entity (model + API + UI) to an existing app |
| `pyforge import-pydl FILE.pydl` | Create/update entities from a PyDL model file |
| `pyforge entity-list` | List the entities in a project |
| `pyforge entity-edit` | Edit an entity's fields and regenerate it |
| `pyforge entity-remove` | Safely remove an entity and its registrations |
| `pyforge info` | Show supported technologies and commands |
| `pyforge windows` | Show Windows install/run instructions |
| `pyforge --version` | Display the PyReactor Forge version |

### Makefile targets (inside generated project)

| Target | Description |
|---|---|
| `make dev` | Start backend + frontend concurrently |
| `make install` | Install all dependencies |
| `make migrate` | Run database migrations |
| `make seed` | Create/update the admin superuser |
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
