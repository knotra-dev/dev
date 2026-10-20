# Knotra development workspace

Work on [engine](https://github.com/knotra-dev/engine),
[desktop](https://github.com/knotra-dev/desktop), and
[docs](https://github.com/knotra-dev/docs) together. Each lives in `repos/` and keeps
its own Git history and releases. Open `knotra.code-workspace` to edit them together.

## Start

Install Git, Make, Python 3, Go (see engine's `go.mod`), Bun 1.3.10, Node.js 24,
Rust/rustup, Docker with Compose, and the
[Tauri prerequisites](https://v2.tauri.app/start/prerequisites/).
Workspace commands support macOS/Linux; use WSL for the engine on Windows.

```sh
git clone https://github.com/knotra-dev/dev.git knotra-dev
cd knotra-dev
make bootstrap
make infra
make dev
```

In desktop Settings, connect to `http://127.0.0.1:8787`. The local profile needs
Ollama at `http://127.0.0.1:11434` with `qwen3.5:9b` installed separately.
See the [engine running guide](https://github.com/knotra-dev/engine/blob/main/docs/running.md)
for other providers. Setup downloads no model weights and makes no paid calls.

PostgreSQL uses port `25432` and a persistent Docker volume. Engine files live in
`.state/engine`. Set `KNOTRA_DATABASE_URL` to use an existing development database.

## Commands

Run `make` for all commands.

| Command | Purpose |
| --- | --- |
| `make dev` | Run engine and native desktop; desktop exit stops engine |
| `make engine` / `make desktop` | Run either independently |
| `make browser` | Browser preview at `http://127.0.0.1:1420` (shares the native dev port) |
| `make docs` | Docs preview at `http://localhost:3000/en/` |
| `make docs-check` | Lint, build, typecheck, and test docs |
| `make check` | Check engine, frontend, and contract snapshot |
| `make integration` | Test real PostgreSQL/Docker/native/browser flows |
| `make status` / `make lock` | Compare or record repository revisions |
| `make stop` | Stop PostgreSQL and keep its data |

Before integration tests, run `make infra` and install Chromium with
`cd repos/desktop && bunx playwright install chromium`. Tests use a fixed model
provider and an isolated schema in the development database.

## Change repositories

`make bootstrap` clones revisions from `repos.lock.json` and installs dependencies.
It preserves existing checkouts and edits. Create a branch in each repo you change.

For shared contracts, commit engine first, then sync and commit desktop:

```sh
cd repos/desktop
python3 scripts/sync-engine.py ../engine "$(git -C ../engine rev-parse HEAD)"
cd ../..
make check
```

Push changed repositories, then run `make lock` and commit the lock here. All three
repos must be clean, and desktop's snapshot must match engine. CI uses those exact
revisions. For docs-only work, use the [docs README](https://github.com/knotra-dev/docs#readme).

[Original project history](https://github.com/michael-bill/knotra) · [MIT license](LICENSE)
