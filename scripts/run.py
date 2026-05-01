"""
Cross-platform helper invoked by the Makefile.

Handles two concerns that require shell logic not portable to cmd.exe:
  1. Checking whether the daemon container is already running.
  2. Dispatching stage commands to the daemon (if up) or falling back
     to a one-shot container run (if not).

Usage (called by make, not directly):
  python scripts/run.py up
  python scripts/run.py <extract|segment|transcribe|enhance|all>
  python scripts/run.py <clean|clean-status|clean-raw>
  python scripts/run.py status
"""
import glob
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Always run relative to the project root regardless of cwd.
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

CONTAINER = "agora-app"
COMPOSE   = ["docker", "compose"]

CMD_IN   = "/tmp/cmd_in"
CMD_DONE = "/tmp/cmd_done"
READY    = "/tmp/daemon_ready"

STAGES = {"extract", "segment", "transcribe", "enhance", "all"}


# ── Docker helpers ────────────────────────────────────────────────────────────

def _run(*args, **kwargs):
    return subprocess.run(list(args), **kwargs)


def _compose(*args, **kwargs):
    return _run(*COMPOSE, *args, **kwargs)


def _container_running():
    r = _run(
        "docker", "inspect", "--format", "{{.State.Running}}", CONTAINER,
        capture_output=True, text=True,
    )
    return r.returncode == 0 and r.stdout.strip() == "true"


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_up():
    if _container_running():
        print("Daemon already running.")
        return
    print("Starting daemon (building image if needed)...")
    _compose("up", "-d", "app", check=True)
    print("Waiting for Whisper model to load", end="", flush=True)
    while True:
        r = _run("docker", "exec", CONTAINER, "test", "-f", READY,
                 capture_output=True)
        if r.returncode == 0:
            break
        time.sleep(2)
        print(".", end="", flush=True)
    print()
    print("Daemon ready! Run 'make transcribe' (or any stage) — no reload needed.")


def cmd_stage(stage):
    if _container_running():
        # Record current time so we only tail logs produced by this stage.
        since = str(int(time.time()) - 1)

        # Dispatch to running daemon — Whisper stays loaded in memory.
        _run("docker", "exec", CONTAINER, "sh", "-c",
             f"rm -f {CMD_DONE} && printf '{stage}' > {CMD_IN}",
             check=True)

        # Stream the container's stdout/stderr to the terminal so the user
        # can see stage output in real time (output would otherwise only
        # appear in `docker logs`).
        log_proc = subprocess.Popen(
            ["docker", "logs", "--follow", f"--since={since}", CONTAINER],
        )
        try:
            while True:
                r = _run("docker", "exec", CONTAINER, "test", "-f", CMD_DONE,
                         capture_output=True)
                if r.returncode == 0:
                    break
                time.sleep(0.5)
        finally:
            time.sleep(0.5)   # let the last log lines flush before killing
            log_proc.terminate()
            log_proc.wait()
    else:
        # Fallback: one-shot container. Slower — Whisper reloads each time.
        if stage == "all":
            _compose("run", "--rm", "app", check=True)
        else:
            _compose("run", "--rm", "--no-deps", "app", stage, check=True)


def cmd_status():
    status_dir = ROOT / "data" / "status"
    print()
    print("  Pipeline Status")
    print("  ===============")
    if not status_dir.is_dir() or not any(status_dir.iterdir()):
        print("  (no stages completed yet)")
    else:
        print()
        for f in sorted(status_dir.iterdir()):
            if not f.name.startswith("."):
                print(f"  v {f.name}")
        print()
        print("  Marker files are in data/status/ — open any file for details.")
    print()


def cmd_clean():
    files = list((ROOT / "data" / "05_output").glob("*.txt"))
    for f in files:
        f.unlink()
    print(f"Removed {len(files)} output file(s).")


def cmd_clean_status():
    d = ROOT / "data" / "status"
    if d.is_dir():
        shutil.rmtree(d)
        print("Removed data/status/")


def cmd_clean_raw():
    d = ROOT / "data" / "04_raw"
    if d.is_dir():
        shutil.rmtree(d)
        print("Removed data/04_raw/")


# ── Entry point ───────────────────────────────────────────────────────────────

def cmd_help():
    print("""
  AEGEE Agora Transcriber - Pipeline Stages
  ==========================================

  Recommended workflow (fastest - Whisper loads once):

    make up           Start the persistent daemon (builds image if needed)
    make extract      Convert video files to audio
    make segment      Split audio by segment definitions
    make transcribe   Transcribe audio with Whisper
    make enhance      Apply substitution rules to raw transcripts
    make all          Run all stages in order
    make down         Stop the daemon

  Each stage falls back to a one-shot container when the daemon is not
  running, so all make targets work with or without make up.

  Status and monitoring:

    make status       Show which files have been processed in each stage
    make logs         Follow daemon / container logs

  Lifecycle:

    make build        (Re)build the Docker image
    make run          Run the full pipeline in a one-shot container

  Cleanup:

    make clean        Remove final output files (data/05_output/)
    make clean-status Remove stage status markers (re-run stages from scratch)
    make clean-raw    Remove raw transcripts (data/04_raw/)
    make reset        Full cleanup: stop containers + remove all generated files
    make purge        Reset + remove Docker volumes and images
    make everything   Full one-shot: reset -> build -> run all stages
""")


COMMANDS = {
    "help":         cmd_help,
    "up":           cmd_up,
    "status":       cmd_status,
    "clean":        cmd_clean,
    "clean-status": cmd_clean_status,
    "clean-raw":    cmd_clean_raw,
    **{s: (lambda s=s: cmd_stage(s)) for s in STAGES},
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: run.py <{' | '.join(COMMANDS)}>")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
