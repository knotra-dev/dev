# Knotra development workspace

Develop the engine, desktop and documentation while each keeps its own history, checks and releases.

| Repository                                       | Owns                                                               |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| [engine](https://github.com/knotra-dev/engine)   | Go engine, River runtime, CLI, API, schemas and examples           |
| [desktop](https://github.com/knotra-dev/desktop) | Tauri app, browser preview and a pinned engine asset snapshot      |
| [docs](https://github.com/knotra-dev/docs)       | Project documentation and guides, published with GitHub Pages      |
| [dev](https://github.com/knotra-dev/dev)         | Local setup, tested revision pairs and cross-repository acceptance |

## Set up

Install Git, Make, Python 3, Go from engine's `go.mod`, Bun 1.3.10, Node.js 24, pnpm 11.25.0,
Rust/rustup and
[Tauri prerequisites](https://v2.tauri.app/start/prerequisites/). Docker with Compose is needed for
PostgreSQL and sandboxes. Native desktop development needs its platform toolchain; these Make
commands target macOS/Linux (use WSL for the engine on Windows).

```sh
git clone https://github.com/knotra-dev/dev.git knotra-dev
cd knotra-dev
make bootstrap
make infra
make dev
```

Save `http://127.0.0.1:8787` in desktop Settings. `make dev` stops the engine when desktop exits;
PostgreSQL persists in the `knotra-dev` Compose project's volume; engine files live in
`.state/engine`. `make stop` stops PostgreSQL without deleting data. Stop an older local stack first
if it uses port `25432`. Model credentials and profiles stay in engine. The bundled local profile
expects Ollama at `http://127.0.0.1:11434` with `qwen3.5:9b`; install/pull it explicitly before
running model workflows. Setup does not download model weights or make paid calls. See the
[engine running guide](https://github.com/knotra-dev/engine/blob/main/docs/running.md) for other
providers and databases. Override `KNOTRA_DATABASE_URL` to use an existing development DB.

Use `make engine` and `make desktop` in separate terminals for independent restarts, or
`make browser` for preview at `http://127.0.0.1:1420`. Native and browser dev servers share that
port. Open `knotra.code-workspace` in an editor for all four repositories.

## Documentation

Run `make docs` to edit the OpenDocs site in `repos/docs`. It uses Node.js 24 and pnpm 11.25.0;
`make bootstrap` installs its dependencies alongside the product dependencies. Run `make docs-check`
to lint, build, typecheck and test its static export before pushing documentation changes.
The docs repository owns its GitHub Pages deployment.

## Change both products

`repos.lock.json` records full tested commits. Bootstrap checks out new clones at those revisions
and preserves all existing checkouts and edits. It never pulls, resets or switches an existing
branch. Run `make status` to see differences from the lock.

```sh
git -C repos/engine switch -c codex/my-change
git -C repos/desktop switch -c codex/my-change
```

Commit the engine change first. Sync the canonical schema, OpenAPI, fixtures and starters into
desktop, then commit the desktop change:

```sh
cd repos/desktop
python3 scripts/sync-engine.py ../engine "$(git -C ../engine rev-parse HEAD)"
cd ../..
make check
```

Run native/browser checks from desktop as described in its README. After installing Playwright
Chromium (`cd repos/desktop && bunx playwright install chromium`), run `make integration` with the
infrastructure from `make infra`. It tests native receipts/SSE and browser workflows against real
River, PostgreSQL and Docker, with a fixed model provider. No Ollama or paid calls are needed. Use a
development database; tests isolate their own schema.

Push changed repository commits before recording their revisions with `make lock`, then commit/push
`repos.lock.json` here. The lock command refuses dirty engine, desktop or docs trees, or an
engine/snapshot mismatch.
CI bootstraps those exact revisions and runs the paired acceptance suite. It does not silently
follow product `main` branches. Single-repository work can use each product's own checkout and CI.

There are no Git submodules, shared source imports or separate runtime repository. Contract assets
have one canonical source in engine; desktop builds independently from its committed copy.

## Migration

Engine retains the original project's full Git history. Desktop retains the extracted `app/` history
with its files promoted to the repository root. The original
[repository](https://github.com/michael-bill/knotra) remains available for historical issues,
releases and links. Existing local work and database volumes are not migrated or removed.

[MIT license](LICENSE)
