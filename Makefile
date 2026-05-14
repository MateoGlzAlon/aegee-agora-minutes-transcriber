PROJECT        = agora-transcriber
PYTHON_VERSION = 3.10.14
VENV           = .venv
PYTHON         = $(VENV)/bin/python
PIP            = $(VENV)/bin/pip

.PHONY: help setup up down extract segment transcribe enhance all run status \
        logs clean clean-status clean-raw reset everything lint_segments

help: $(VENV)/.deps
	$(PYTHON) scripts/run.py help

# ── Setup ─────────────────────────────────────────────────────────────────────

$(VENV):
	@PYENV_ROOT="$${PYENV_ROOT:-$$HOME/.pyenv}"; \
	if command -v python3.10 >/dev/null 2>&1; then \
	    PYTHON_BIN=$$(command -v python3.10); \
	    echo "Found Python 3.10 at $$PYTHON_BIN"; \
	elif [ -x "$$PYENV_ROOT/versions/$(PYTHON_VERSION)/bin/python" ]; then \
	    PYTHON_BIN="$$PYENV_ROOT/versions/$(PYTHON_VERSION)/bin/python"; \
	    echo "Found Python $(PYTHON_VERSION) via pyenv at $$PYTHON_BIN"; \
	elif command -v apt-get >/dev/null 2>&1; then \
	    echo "Installing Python 3.10 via deadsnakes PPA..."; \
	    sudo apt-get install -y software-properties-common; \
	    sudo add-apt-repository -y ppa:deadsnakes/ppa; \
	    sudo apt-get install -y python3.10 python3.10-venv; \
	    PYTHON_BIN=$$(command -v python3.10); \
	    echo "Installed Python 3.10 at $$PYTHON_BIN"; \
	else \
	    PYENV_ROOT="$${PYENV_ROOT:-$$HOME/.pyenv}"; \
	    if ! command -v pyenv >/dev/null 2>&1 && [ ! -x "$$PYENV_ROOT/bin/pyenv" ]; then \
	        echo "Python 3.10 not found — installing pyenv..."; \
	        curl -fsSL https://pyenv.run | bash; \
	        echo ""; \
	        echo "NOTE: Add pyenv to your shell profile for future terminals:"; \
	        echo "  export PYENV_ROOT=\"\$$HOME/.pyenv\""; \
	        echo "  export PATH=\"\$$PYENV_ROOT/bin:\$$PATH\""; \
	        echo "  eval \"\$$(pyenv init -)\""; \
	        echo ""; \
	    fi; \
	    export PATH="$$PYENV_ROOT/bin:$$PATH"; \
	    echo "Installing Python $(PYTHON_VERSION) via pyenv..."; \
	    CONFIGURE_OPTS="--with-openssl=/usr --with-openssl-rpath=auto" \
	        "$$PYENV_ROOT/bin/pyenv" install -s $(PYTHON_VERSION); \
	    PYTHON_BIN="$$PYENV_ROOT/versions/$(PYTHON_VERSION)/bin/python"; \
	fi; \
	echo "Creating virtual environment in $(VENV)/..."; \
	"$$PYTHON_BIN" -m venv $(VENV)

$(VENV)/.deps: app/requirements.txt | $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -r app/requirements.txt
	@touch $@

lint_segments: $(VENV)/.deps
	$(PYTHON) scripts/lint_segments.py $(FILES)

setup: $(VENV)/.deps
	@echo ""
	@echo "Setup complete. Python $(PYTHON_VERSION) environment ready at $(VENV)/"
	@echo "Note: ffmpeg must be installed separately (apt install ffmpeg / brew install ffmpeg)"

# ── Daemon lifecycle ──────────────────────────────────────────────────────────

# Start the persistent daemon. Whisper is loaded once and stays in memory.
# Subsequent stage commands reuse the loaded model, avoiding repeated load cost.
up: $(VENV)/.deps
	$(PYTHON) scripts/run.py up

down:
	@[ -f "$(PYTHON)" ] && $(PYTHON) scripts/run.py down || true

# ── Pipeline stages ───────────────────────────────────────────────────────────
# Each target dispatches to the daemon if it is running, otherwise runs
# directly (slower — Whisper reloads each time).

extract: $(VENV)/.deps
	$(PYTHON) scripts/run.py extract

segment: $(VENV)/.deps
	$(PYTHON) scripts/run.py segment

transcribe: $(VENV)/.deps
	$(PYTHON) scripts/run.py transcribe

enhance: $(VENV)/.deps
	$(PYTHON) scripts/run.py enhance

all: $(VENV)/.deps
	$(PYTHON) scripts/run.py all

# Run the full pipeline directly (no daemon)
run: $(VENV)/.deps
	$(PYTHON) scripts/run.py all

# ── Status ────────────────────────────────────────────────────────────────────

status: $(VENV)/.deps
	$(PYTHON) scripts/run.py status

# ── Utilities ─────────────────────────────────────────────────────────────────

logs:
	@tail -f daemon.log 2>/dev/null || echo "No daemon log found. Start the daemon with: make up"

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: $(VENV)/.deps
	$(PYTHON) scripts/run.py clean

clean-status: $(VENV)/.deps
	$(PYTHON) scripts/run.py clean-status

clean-raw: $(VENV)/.deps
	$(PYTHON) scripts/run.py clean-raw

reset: down clean clean-status clean-raw

# Full one-shot workflow: clean slate -> run all stages
everything: reset run
