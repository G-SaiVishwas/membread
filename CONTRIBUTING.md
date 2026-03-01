# Contributing to Membread

Thanks for your interest in contributing! This guide covers the process for submitting changes.

---

## Getting Started

### 1. Fork & clone

```bash
git clone https://github.com/<your-username>/membread.git
cd membread
```

### 2. Set up the development environment

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install the SDK (editable)
pip install -e ./sdk

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 3. Start infrastructure

```bash
docker compose up -d   # PostgreSQL + FalkorDB
```

### 4. Run the test suite

```bash
pytest
```

---

## Development Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** — keep commits focused and atomic.

3. **Run tests** before pushing:
   ```bash
   pytest
   ```

4. **Open a pull request** against `main` with a clear description of what changed and why.

---

## Project Layout

| Directory | What lives there |
|-----------|------------------|
| `server.py` | Main FastAPI server |
| `src/` | Core backend — API, auth, memory engine, governor, connectors |
| `frontend/` | React + Vite + Tailwind SPA |
| `browser_extension/` | Chrome extension for conversation capture |
| `sdk/` | Python SDK with framework integrations |
| `ui/` | Streamlit dashboard |
| `tests/` | Pytest test suite |
| `benchmarks/` | LoCoMo benchmark runner |
| `scripts/` | Utility scripts (token generation, demo seeding) |

---

## Code Style

- **Python**: Follow PEP 8. Use type hints. Keep functions focused.
- **TypeScript/React**: Keep components small. Use functional components with hooks.
- **Commits**: Use clear, imperative-mood messages (e.g. "Add webhook retry logic").

---

## Adding a Connector

Membread's connector system is in `src/connectors/`. To add a new provider:

1. Create `src/connectors/providers/your_provider.py` — implement the `BaseProvider` interface.
2. Register it in `src/connectors/providers/registry.py`.
3. Add setup instructions in `frontend/src/pages/ConnectorsPage.tsx` under `CONNECTOR_SETUP`.
4. Add the provider to the connector list in `server.py`.

See existing providers (e.g. `hubspot.py`, `zendesk.py`) for examples.

---

## Adding an SDK Integration

SDK integrations live in `sdk/membread/integrations/`. Each integration wraps `MembreadClient` for a specific framework:

1. Create `sdk/membread/integrations/your_framework.py`.
2. Export it from `sdk/membread/__init__.py`.
3. Add usage examples to `sdk/README.md`.

---

## Reporting Issues

- Use GitHub Issues for bugs and feature requests.
- Include steps to reproduce, expected vs. actual behaviour, and your environment (OS, Python version, Node version).

---

## License

By contributing, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
