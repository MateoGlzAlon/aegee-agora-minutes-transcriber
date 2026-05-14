"""
Lint segment files in data/02_segments/.

Checks performed per file:
  ERROR   - non-blank, non-comment line that doesn't match expected format
  ERROR   - unrecognised timestamp format
  ERROR   - start >= end (zero- or negative-duration segment)
  WARNING - segments not in chronological order
  WARNING - overlapping segments
  WARNING - duplicate labels within a file

Exits 0 if all files pass (warnings are OK), 1 if any errors are found.
"""
import re
import sys
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
SEGMENTS_DIR = ROOT / "data" / "02_segments"
LINE_PATTERN = re.compile(r"^(.+?)\s*->\s*([\d:]+)\s*-\s*([\d:]+)\s*$")


def _parse_timestamp(ts: str) -> float:
    parts = ts.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"unrecognised timestamp format: '{ts}'")


def _fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:05.2f}"
    return f"{m}:{s:05.2f}"


def lint_file(path: Path) -> tuple[int, int]:
    """Return (error_count, warning_count) for a single segment file."""
    errors = warnings = 0
    segments: list[dict] = []
    seen_labels: set[str] = set()

    def err(lineno, msg):
        nonlocal errors
        errors += 1
        print(f"  ERROR   line {lineno:>3}: {msg}")

    def warn(lineno_or_none, msg):
        nonlocal warnings
        warnings += 1
        loc = f"line {lineno_or_none:>3}: " if lineno_or_none is not None else "          "
        print(f"  WARNING {loc}{msg}")

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        m = LINE_PATTERN.match(line)
        if not m:
            err(lineno, f"format not recognised — expected 'Label -> MM:SS - MM:SS', got: {line!r}")
            continue

        label = m.group(1).strip()

        try:
            start = _parse_timestamp(m.group(2))
        except ValueError as exc:
            err(lineno, f"invalid start timestamp: {exc}")
            continue

        try:
            end = _parse_timestamp(m.group(3))
        except ValueError as exc:
            err(lineno, f"invalid end timestamp: {exc}")
            continue

        if start >= end:
            err(lineno, f"start ({_fmt(start)}) must be before end ({_fmt(end)})")
            continue

        if label in seen_labels:
            warn(lineno, f"duplicate label: {label!r}")
        seen_labels.add(label)

        segments.append({"label": label, "start": start, "end": end, "lineno": lineno})

    for i in range(1, len(segments)):
        prev, cur = segments[i - 1], segments[i]
        if cur["start"] < prev["start"]:
            warn(cur["lineno"],
                 f"segment '{cur['label']}' starts ({_fmt(cur['start'])}) before "
                 f"previous segment '{prev['label']}' ({_fmt(prev['start'])})")
        if cur["start"] < prev["end"]:
            warn(cur["lineno"],
                 f"segment '{cur['label']}' ({_fmt(cur['start'])}) overlaps "
                 f"previous segment '{prev['label']}' (ends {_fmt(prev['end'])})")

    return errors, warnings


def main(paths: list[Path]) -> int:
    if not paths:
        print(f"No segment files found in {SEGMENTS_DIR}")
        return 0

    total_errors = total_warnings = 0
    failed: list[str] = []

    for path in sorted(paths):
        rel = path.relative_to(ROOT)
        errors, warnings = lint_file(path)
        total_errors += errors
        total_warnings += warnings
        if errors or warnings:
            status = "FAIL" if errors else "WARN"
            print(f"\n[{status}] {rel}  ({errors} error(s), {warnings} warning(s))")
            if errors:
                failed.append(str(rel))
        else:
            print(f"[ OK ] {rel}")

    print()
    print(f"{'='*50}")
    print(f"  Files checked : {len(paths)}")
    print(f"  Total errors  : {total_errors}")
    print(f"  Total warnings: {total_warnings}")

    if total_errors:
        print()
        print("Linting FAILED — fix errors above before processing.")
        return 1

    print()
    print("Linting passed.")
    return 0


if __name__ == "__main__":
    explicit = [Path(p).resolve() for p in sys.argv[1:]]
    paths = explicit if explicit else sorted(SEGMENTS_DIR.glob("*.txt"))
    sys.exit(main(paths))
