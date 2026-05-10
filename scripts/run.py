"""
Cross-platform helper invoked by the Makefile.
Runs pipeline stages directly (no Docker).
"""
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

PYTHON   = str(ROOT / ".venv" / "bin" / "python")
PID_FILE = Path("/tmp/agora-daemon.pid")
LOG_FILE = ROOT / "daemon.log"
CMD_IN   = "/tmp/cmd_in"
CMD_DONE = "/tmp/cmd_done"
READY    = "/tmp/daemon_ready"

STAGES = {"extract", "segment", "transcribe", "enhance", "all"}


# ── Daemon helpers ────────────────────────────────────────────────────────────

def _daemon_pid():
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return None


def _daemon_running():
    return _daemon_pid() is not None


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_up():
    if _daemon_running():
        print("Daemon already running.")
        return
    print("Starting daemon (loading Whisper model)...")
    log = open(LOG_FILE, "a")
    proc = subprocess.Popen([PYTHON, "app/daemon.py"], stdout=log, stderr=log)
    PID_FILE.write_text(str(proc.pid))
    print(f"Daemon started (PID {proc.pid}). Logs: {LOG_FILE}")
    print("Waiting for Whisper model to load", end="", flush=True)
    while True:
        if proc.poll() is not None:
            print(f"\nDaemon exited unexpectedly. Check {LOG_FILE}")
            PID_FILE.unlink(missing_ok=True)
            sys.exit(1)
        if os.path.exists(READY):
            break
        time.sleep(2)
        print(".", end="", flush=True)
    print()
    print("Daemon ready! Run 'make transcribe' (or any stage) — no reload needed.")


def cmd_down():
    pid = _daemon_pid()
    if pid is None:
        print("Daemon not running.")
        return
    try:
        with open(CMD_IN, "w") as f:
            f.write("stop")
        time.sleep(1)
    except Exception:
        pass
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    PID_FILE.unlink(missing_ok=True)
    for f in (CMD_IN, CMD_DONE, READY):
        if os.path.exists(f):
            os.remove(f)
    print("Daemon stopped.")


def cmd_stage(stage):
    if _daemon_running():
        log_offset = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

        if os.path.exists(CMD_DONE):
            os.remove(CMD_DONE)
        with open(CMD_IN, "w") as f:
            f.write(stage)

        log = open(LOG_FILE, "r")
        log.seek(log_offset)
        try:
            while True:
                line = log.readline()
                if line:
                    print(line, end="", flush=True)
                elif os.path.exists(CMD_DONE):
                    break
                else:
                    time.sleep(0.3)
        finally:
            log.close()
    else:
        args = [PYTHON, "app/main.py"] + ([stage] if stage != "all" else [])
        subprocess.run(args, check=True)


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


def cmd_help():
    print("""
  AEGEE Agora Transcriber - Pipeline Stages
  ==========================================

  First-time setup:

    make setup        Install Python 3.10 (via pyenv if needed) + dependencies
                      Note: ffmpeg must be installed separately
                        Ubuntu/Debian:  sudo apt install ffmpeg
                        macOS:          brew install ffmpeg

  Recommended workflow (fastest - Whisper loads once):

    make up           Start the persistent daemon
    make extract      Convert video files to audio
    make segment      Split audio by segment definitions
    make transcribe   Transcribe audio with Whisper
    make enhance      Apply substitution rules to raw transcripts
    make all          Run all stages in order
    make down         Stop the daemon

  Each stage also works without the daemon (Whisper reloads each time).

  Status and monitoring:

    make status       Show which files have been processed in each stage
    make logs         Follow daemon logs

  Cleanup:

    make clean        Remove final output files (data/05_output/)
    make clean-status Remove stage status markers (re-run stages from scratch)
    make clean-raw    Remove raw transcripts (data/04_raw/)
    make reset        Stop daemon + remove all generated files
    make everything   Full one-shot: reset -> run all stages
""")


COMMANDS = {
    "help":         cmd_help,
    "up":           cmd_up,
    "down":         cmd_down,
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
