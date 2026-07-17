# Kapital

Kapital is a scalable financial SaaS platform for wealth management and analysis. Key features include:

- **Institution Syncing**: Connects to banks and brokers for an aggregated net worth view.
- **Goal-Based Portfolios**: Divides assets by purpose (e.g., pension, loans, high-risk trading).
- **Trade Optimization**: Analyzes opportunity costs (e.g., comparing selling Apple vs. buying Amazon).

## 🛠 Tech Stack

- **Frontend**: [Vue.js](https://vuejs.org/) (Decoupled SPA)
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) + [Alembic](https://alembic.sqlalchemy.org/)
- **Data Handling**: [Polars](https://pola.rs/)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/) (Strict mode)
- **Database**: PostgreSQL
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv)
- **Code Quality**:
  - `prek` workflow orchestrating:
  - `ruff` / `ruff-format` (Linting/Formatting, scoped to `backend/`)
  - `gitleaks` (Secret Scanning)
  - `validate-pyproject` (Manifest Validation)
  - `commitizen` (Commit Standardization)

## 🚀 Getting Started

To run the complete stack (Frontend, Backend, and PostgreSQL database), you must use Docker Compose. Running Docker commands on this system requires `sudo` privileges:

```bash
# Build and start all services in the background
sudo docker compose up --build -d

# Follow container logs
sudo docker compose logs -f
```

This will automatically build the images, spin up the PostgreSQL database container, execute Alembic migrations, and serve the application at `http://localhost`.

## 🧑‍💻 Maintainer Setup

To configure the repo-wide pre-commit and quality hooks (defined in `prek.toml` at the root):
```bash
uv sync --all-groups --directory backend
uv run --directory backend prek install
uv run --directory backend prek install --hook-type commit-msg
```

## ⚖️ License
This project is licensed under the [FSL-1.1-ALv2 License](LICENSE).
