PROJECT  = agora-transcriber
COMPOSE  = docker compose

# Override on Windows if needed:  make PYTHON=python
PYTHON  ?= python3

.PHONY: help build up down extract segment transcribe enhance all run status \
        logs clean clean-status clean-raw reset purge everything

help:
	$(PYTHON) scripts/run.py help

# ── Build ─────────────────────────────────────────────────────────────────────

build:
	$(COMPOSE) build

# ── Daemon lifecycle ──────────────────────────────────────────────────────────

# Start the persistent daemon. Whisper is loaded once and stays in memory.
# Subsequent stage commands are dispatched to the running container,
# avoiding both container startup overhead and repeated model loading.
up:
	$(PYTHON) scripts/run.py up

down:
	$(COMPOSE) down

# ── Pipeline stages ───────────────────────────────────────────────────────────
# Each target dispatches to the daemon if it is running, otherwise starts
# a one-shot container (slower - Whisper reloads each time).

extract:
	$(PYTHON) scripts/run.py extract

segment:
	$(PYTHON) scripts/run.py segment

transcribe:
	$(PYTHON) scripts/run.py transcribe

enhance:
	$(PYTHON) scripts/run.py enhance

all:
	$(PYTHON) scripts/run.py all

# Full pipeline in a single one-shot container (no daemon required)
run:
	$(COMPOSE) run --rm app

# ── Status ────────────────────────────────────────────────────────────────────

status:
	$(PYTHON) scripts/run.py status

# ── Utilities ─────────────────────────────────────────────────────────────────

logs:
	$(COMPOSE) logs -f

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	$(PYTHON) scripts/run.py clean

clean-status:
	$(PYTHON) scripts/run.py clean-status

clean-raw:
	$(PYTHON) scripts/run.py clean-raw

reset: down clean clean-status clean-raw
	$(COMPOSE) down -v

purge: down
	$(COMPOSE) down -v --rmi all

# Full one-shot workflow: clean slate -> build -> run all stages
everything: reset build run
