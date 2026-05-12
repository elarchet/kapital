# Kapital

Kapital is a scalable financial SaaS platform for wealth management and analysis. Key features include:

- **Institution Syncing**: Connects to banks and brokers for an aggregated net worth view.
- **Goal-Based Portfolios**: Divides assets by purpose (e.g., pension, loans, high-risk trading).
- **Trade Optimization**: Analyzes opportunity costs (e.g., comparing selling Apple vs. buying Amazon).

## 🛠 Tech Stack

- **Frontend Dashboard**: [Marimo](https://marimo.io/) (Phase 1)
- **Frontend Framework**: [Vue.js](https://vuejs.org/) (Phase 2)
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) + [Alembic](https://alembic.sqlalchemy.org/)
- **Data Handling**: [Polars](https://pola.rs/)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/) (Strict mode)
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv)
- **Code Quality**:
  - `prek` workflow orchestrating:
  - `ruff` (Linting/Formatting)
  - `ty` (Type Checking)
  - `commitizen` (Commit Standardization)

## 🚀 Getting Started

### Prerequisites
- Python 3.14+
- `uv` installed

### Installation
```bash
# Clone the repository
git clone <repo-url>
cd kapital

# Install dependencies
uv sync
```

### Running the Dashboard
```bash
uv run marimo edit
```

## 🧑‍💻 Maintainer Setup

```bash
uv sync --all-groups
uv run prek install
uv run prek install --hook-type commit-msg
```

## ⚖️ License
This project is licensed under the [MIT License](LICENSE).
