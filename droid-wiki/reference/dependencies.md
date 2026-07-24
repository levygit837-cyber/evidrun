# Dependencies

Evidrun's dependency set is deliberately small. Python deps are in `pyproject.toml`; Node deps are in `package.json`. The offline benchmark needs none of the provider stack.

## Python runtime dependencies

Twelve runtime dependencies, installed by `uv sync`.

| Package | Purpose |
| --- | --- |
| `alembic>=1.16.0` | Database migrations against the SQLAlchemy models |
| `cryptography>=45.0.0` | AES-256-GCM for the sensitive artifact vault and ES256 for the local authenticator |
| `fastapi>=0.116.0` | The loopback HTTP API |
| `httpx>=0.28.1` | Async HTTP client for the OpenAI Responses provider adapter |
| `keyring>=25.6.0` | System Keychain access for provider credentials and artifact keys |
| `platformdirs>=4.3.0` | Resolving the default data directory per OS |
| `pydantic>=2.11.0` | The frozen contract models and validation |
| `pyyaml>=6.0.2` | Parsing experiment and contract YAML |
| `rich>=14.0.0` | CLI tables and JSON output |
| `sqlalchemy>=2.0.41` | The SQLite/WAL persistence layer |
| `typer>=0.16.0` | The CLI framework |
| `uvicorn>=0.35.0` | ASGI server for the FastAPI app |

## Python dev and package extras

The `dev` extra (`uv sync --extra dev`) adds five tools:

| Package | Purpose |
| --- | --- |
| `hypothesis>=6.135.0` | Property-based tests |
| `pyright>=1.1.402` | Strict type checking |
| `pytest>=8.4.0` | Test runner |
| `pytest-asyncio>=1.0.0` | Async test support |
| `ruff>=0.12.0` | Linter and formatter |

The `package` extra adds `pyinstaller>=6.14.0`, used to build the standalone desktop backend binary.

## Node dependencies

Runtime dependencies (`package.json`) are the renderer stack:

| Package | Purpose |
| --- | --- |
| `react` / `react-dom` `19.2.7` | The renderer UI |
| `@tanstack/react-query` `5.101.3` | Server-state and data fetching against the API |
| `@tanstack/react-router` `^1.131.35` | Client-side routing |
| `@radix-ui/react-tabs`, `@radix-ui/react-tooltip` | Accessible UI primitives |
| `lucide-react` `^0.468.0` | Icon set |

## Node dev dependencies

The dev set covers Electron, the build toolchain, and testing:

| Package | Purpose |
| --- | --- |
| `electron` `43.2.0` | The desktop shell |
| `@electron-forge/cli`, `maker-dmg`, `maker-zip` | Packaging and installers |
| `vite` `8.1.5`, `@vitejs/plugin-react` | Renderer dev server and build |
| `typescript` `^6.0.0` | Type checking for web and desktop |
| `@tailwindcss/vite`, `tailwindcss` `4.3.3` | Styling |
| `vitest` `^4.0.0`, `jsdom` | Test runner and DOM environment |
| `@testing-library/react`, `/dom`, `/jest-dom` | Component testing utilities |
| `json-schema-to-typescript` `^15.0.4` | Generating `contracts.ts` from the contract catalog |
| `playwright` `^1.59.0` | Browser automation |
| `concurrently`, `cross-env`, `wait-on` | Orchestrating `desktop:dev` |
| `@types/node`, `@types/react`, `@types/react-dom` | Type definitions |

## The provider dependency

The default provider is a local CLIProxyAPI process at `http://127.0.0.1:8318/v1`, OpenAI Responses-compatible, serving `deepseek-v4-flash`. It is an external runtime dependency, not a package: Evidrun talks to it over HTTP through the adapter behind `ProviderPort`, and the API key lives in the Keychain. The offline `CRL-CTX-002` benchmark does not need it. See [reference: configuration](configuration.md) and [systems: providers](../systems/providers.md).
