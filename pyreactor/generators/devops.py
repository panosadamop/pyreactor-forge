"""DevOps generator - Docker, docker-compose, CI/CD."""

from pathlib import Path


class DevOpsGenerator:
    def __init__(self, config: dict, output_dir: Path):
        self.config = config
        self.out = output_dir
        self.name = config["name"]
        self.slug = self.name.lower().replace(" ", "-")
        self.backend = config["backend"]
        self.db = config["database"]
        self.ci = config.get("ci", "github-actions")

    def generate(self):
        if self.config.get("docker"):
            self._write_docker_backend()
            self._write_docker_frontend()
            self._write_compose()

        if self.ci == "github-actions":
            self._write_github_actions()
        elif self.ci == "gitlab-ci":
            self._write_gitlab_ci()

    def _write_docker_backend(self):
        run_cmd = (
            "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
            if self.backend == "django"
            else "uvicorn app.main:app --host 0.0.0.0 --port 8000"
        )
        (self.out / "backend" / "Dockerfile").write_text(f"""FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc libpq-dev curl && \\
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["/bin/sh", "-c", "{run_cmd}"]
""")

    def _write_docker_frontend(self):
        (self.out / "frontend" / "Dockerfile").write_text("""# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""")

        (self.out / "frontend" / "nginx.conf").write_text("""server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
""")

    def _write_compose(self):
        db_service = self._db_service()
        db_env = self._db_env_vars()

        (self.out / "docker-compose.yml").write_text(f"""version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
{db_env}
      - SECRET_KEY=${{SECRET_KEY:-change-in-production}}
      - DEBUG=${{DEBUG:-false}}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./backend:/app
    networks:
      - app-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - app-network

{db_service}

networks:
  app-network:
    driver: bridge

volumes:
  db-data:
""")

        (self.out / "docker-compose.dev.yml").write_text(f"""version: "3.9"

# Development override - mounts source for hot-reload
services:
  backend:
    volumes:
      - ./backend:/app
    environment:
      - DEBUG=true

  frontend:
    build:
      target: build
    command: npm run dev -- --host
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
""")

    def _db_service(self):
        if self.db == "postgresql":
            return """  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: ${DB_NAME:-appdb}
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network"""
        elif self.db == "mysql":
            return """  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD:-root}
      MYSQL_DATABASE: ${DB_NAME:-appdb}
      MYSQL_USER: ${DB_USER:-mysql}
      MYSQL_PASSWORD: ${DB_PASSWORD:-mysql}
    volumes:
      - db-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network"""
        else:
            return """  db:
    image: alpine
    command: echo "Using SQLite - no db service needed"
    healthcheck:
      test: ["CMD", "echo", "ok"]"""

    def _db_env_vars(self):
        if self.db == "postgresql":
            return (
                "      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-postgres}:${DB_PASSWORD:-postgres}"
                "@db:5432/${DB_NAME:-appdb}"
            )
        elif self.db == "mysql":
            return (
                "      - DATABASE_URL=mysql+aiomysql://${DB_USER:-mysql}:${DB_PASSWORD:-mysql}"
                "@db:3306/${DB_NAME:-appdb}"
            )
        else:
            return "      - DATABASE_URL=sqlite+aiosqlite:///./app.db"

    def _write_github_actions(self):
        ci_dir = self.out / ".github" / "workflows"
        ci_dir.mkdir(parents=True)

        (ci_dir / "ci.yml").write_text(f"""name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./backend

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint
        run: ruff check .

      - name: Run tests
        run: pytest --tb=short

  frontend-test:
    name: Frontend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint || true

      - name: Build
        run: npm run build

  docker-build:
    name: Docker Build Check
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker images
        run: docker-compose build

      - name: Smoke test
        run: |
          docker-compose up -d
          sleep 15
          curl -f http://localhost:8000/health || exit 1
          docker-compose down
""")

        (ci_dir / "release.yml").write_text(f"""name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  build-and-push:
    name: Build & Push Docker Images
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{{{ secrets.DOCKER_USERNAME }}}}
          password: ${{{{ secrets.DOCKER_TOKEN }}}}

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ${{{{ secrets.DOCKER_USERNAME }}}}/{self.slug}-backend:${{{{ github.ref_name }}}}

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ${{{{ secrets.DOCKER_USERNAME }}}}/{self.slug}-frontend:${{{{ github.ref_name }}}}
""")

    def _write_gitlab_ci(self):
        (self.out / ".gitlab-ci.yml").write_text("""stages:
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  npm_config_cache: "$CI_PROJECT_DIR/.cache/npm"

backend-test:
  stage: test
  image: python:3.12-slim
  cache:
    paths: [.cache/pip]
  script:
    - cd backend
    - pip install -r requirements.txt
    - ruff check .
    - pytest --tb=short

frontend-test:
  stage: test
  image: node:20-alpine
  cache:
    paths: [.cache/npm]
  script:
    - cd frontend
    - npm ci
    - npm run build

docker-build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  only:
    - main
  script:
    - docker-compose build
""")
