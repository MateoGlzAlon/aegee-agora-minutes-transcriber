"""
Long-lived daemon that keeps the Whisper model loaded in memory.

The Makefile's stage targets send commands to this process via a command
file (/tmp/cmd_in) and wait for a done signal (/tmp/cmd_done). Because the
Python process never exits between stages, the model load cost is paid once.
"""
import os
import sys
import time

CMD_IN   = "/tmp/cmd_in"
CMD_DONE = "/tmp/cmd_done"
READY    = "/tmp/daemon_ready"

# Eagerly load Whisper so the model is hot before the first command arrives
print("[daemon] Loading Whisper model...", flush=True)
from transcription import transcribe as _  # noqa: triggers model load
print("[daemon] Whisper model loaded.", flush=True)

import main as pipeline

STAGES = {
    "extract":    pipeline.run_extract,
    "segment":    pipeline.run_segment,
    "transcribe": pipeline.run_transcribe,
    "enhance":    pipeline.run_enhance,
    "all":        pipeline.run_all,
}

# Remove stale signal files from a previous run
for _f in (CMD_IN, CMD_DONE, READY):
    if os.path.exists(_f):
        os.remove(_f)

with open(READY, "w") as _fh:
    _fh.write("ready\n")

print("[daemon] Ready — waiting for stage commands.", flush=True)

while True:
    if os.path.exists(CMD_IN):
        with open(CMD_IN) as fh:
            cmd = fh.read().strip()
        os.remove(CMD_IN)

        if cmd == "stop":
            print("[daemon] Received stop — exiting.", flush=True)
            break

        fn = STAGES.get(cmd)
        if fn:
            print(f"[daemon] >> {cmd}", flush=True)
            try:
                fn()
            except Exception as exc:
                print(f"[daemon] ERROR in {cmd}: {exc}", flush=True)
            print(f"[daemon] << {cmd} done", flush=True)
        else:
            print(f"[daemon] Unknown command: {cmd!r}", flush=True)

        with open(CMD_DONE, "w") as fh:
            fh.write(cmd + "\n")
    else:
        time.sleep(0.3)
