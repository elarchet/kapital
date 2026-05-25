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
- **Node.js & NPM**: A pre-packaged Node.js distribution is provided in the `.node-dist` directory. To make `node` and `npm` available in your current terminal session, run:
  ```bash
  export PATH="$PWD/.node-dist/bin:$PATH"
  ```
  For a permanent setup, you can add this line to your shell configuration file (e.g. `~/.bashrc` or `~/.zshrc`).

### Installation
Make sure Node.js/NPM are in your `PATH` (as described in Prerequisites), then run:
```bash
# Clone the repository
git clone <repo-url>
cd kapital

# Install backend dependencies
uv sync --directory backend

# Install frontend dependencies
npm install --prefix frontend
```

### Running the Application (Frontend & Backend)
You can run both the Vue.js frontend and the FastAPI backend concurrently using the provided startup script:
```bash
chmod +x start.sh
./start.sh
```
This script automatically sets the PATH to use the local `.node-dist` binaries, starts both development servers, and handles clean process termination when you stop the command (e.g., using `Ctrl+C`).

### Running the API Server Only
If you only need to run the FastAPI backend, you can run from the root:
```bash
uv run --directory backend uvicorn src.main:app --reload
```
Or navigate into `backend` and run:
```bash
cd backend
uv run uvicorn src.main:app --reload
```

## 🧑‍💻 Maintainer Setup

To configure the pre-commit and quality hooks on the backend:
```bash
uv sync --all-groups --directory backend
uv run --directory backend prek install
uv run --directory backend prek install --hook-type commit-msg
```

## ⚖️ License
This project is licensed under the [MIT License](LICENSE).
