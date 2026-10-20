SHELL := /bin/bash
ROOT := $(CURDIR)
export COMPOSE_PROJECT_NAME ?= knotra-dev
export KNOTRA_DATABASE_URL ?= postgres://knotra:knotra-development@127.0.0.1:25432/knotra?sslmode=disable

.PHONY: help bootstrap status lock check infra stop engine desktop browser docs docs-check dev integration

help:
	@printf '%s\n' \
	  'make bootstrap    Clone pinned repositories and install Go/Bun/pnpm dependencies' \
	  'make status       Show revisions, edits and lock differences' \
	  'make infra        Start PostgreSQL and build/pull sandbox dependencies' \
	  'make dev          Start engine and native desktop; Ctrl-C stops both' \
	  'make engine       Run engine alone' \
	  'make desktop      Run native desktop alone' \
	  'make browser      Run browser preview alone' \
	  'make docs         Run the documentation site locally' \
	  'make docs-check   Lint, build and test the documentation site' \
	  'make check        Check engine, frontend and contract snapshot' \
	  'make integration  Run real PostgreSQL/Docker/native/browser acceptance' \
	  'make lock         Record clean committed repositories after snapshot sync' \
	  'make stop         Stop PostgreSQL while preserving its volume'

bootstrap:
	python3 scripts/workspace.py bootstrap
	cd repos/engine && go mod download
	cd repos/desktop && bun install --frozen-lockfile
	pnpm --dir repos/docs install --frozen-lockfile

status:
	python3 scripts/workspace.py status

lock:
	python3 scripts/workspace.py lock

check:
	python3 -m unittest discover -s scripts -v
	$(MAKE) -C repos/engine check build
	cd repos/desktop && python3 -m unittest discover -s scripts -v
	cd repos/desktop && python3 scripts/sync-engine.py ../engine "$$(git -C ../engine rev-parse HEAD)" --check
	cd repos/desktop && bun run format:check && bun run test && bun run build

infra:
	cd repos/engine && docker compose up -d --wait
	$(MAKE) -C repos/engine helper firewall
	docker pull python:3.13-alpine
	docker pull node:22-alpine

stop:
	cd repos/engine && docker compose stop

engine:
	$(MAKE) -C repos/engine build
	cd repos/engine && bin/knotra serve --profile examples/local/profile.yaml --data-dir "$(ROOT)/.state/engine" --cors-origin http://127.0.0.1:1420

desktop:
	cd repos/desktop && bun run desktop:dev

browser:
	cd repos/desktop && bun run dev

docs:
	pnpm --dir repos/docs dev

docs-check:
	cd repos/docs && pnpm lint && pnpm build && pnpm typecheck && pnpm test

dev:
	$(MAKE) -C repos/engine build
	bash scripts/dev.sh

integration:
	cd repos/desktop && bun run build
	cd repos/desktop && cargo test --locked --manifest-path src-tauri/Cargo.toml --no-run
	cd repos/engine && KNOTRA_TEST_DESKTOP=1 \
	  KNOTRA_TEST_DESKTOP_DIR="$(ROOT)/repos/desktop" \
	  KNOTRA_TEST_DATABASE_URL="$(KNOTRA_DATABASE_URL)" \
	  KNOTRA_TEST_HELPER="$(ROOT)/repos/engine/.knotra/bin/sandbox-helper" \
	  KNOTRA_TEST_FIREWALL_IMAGE=knotra-firewall:dev \
	  go test -mod=readonly -race -count=1 -timeout=15m ./internal/integration -run '^TestDesktopLiteralClients$$' -v
