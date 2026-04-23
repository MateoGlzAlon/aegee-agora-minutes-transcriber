# AEGEE Agora Transcriber

> [!NOTE]
> Based on the original private repo to ensure that no private AEGEE information is leaked: https://github.com/MateoGlzAlon/agora-transcriber


A fully local, four-stage audio transcription pipeline for AEGEE Agora meeting recordings.  
No external APIs are required — everything runs inside Docker.

---

## Prerequisites

Before running the pipeline, you only need to have the following installed:

* Docker
* Docker Compose

---

## Quick Start

```bash
# 1. Build the Docker image (first time only, or after code changes)
make build

# 2. Place your audio file(s) in  data/03_audio/
#    or your video file(s)    in  data/01_video/

# 3. Create a segments file (stage 2) for having different sections (optional but much better)

# 4. Run the full pipeline (You can also run it by stages, check futher down in the README)
make all

# 5. Collect results from  data/05_output/
```

The pipeline is **idempotent** — already-completed files are skipped on every run.  
You can re-run any stage at any time without duplicating work.

---

## All Make Targets

| Command | Description |
|---|---|
| `make build` | Build the Docker image |
| `make extract` | Stage 1 — convert video files to audio (fast) |
| `make segment` | Stage 2 — split audio by time-segment definitions (fast) |
| `make transcribe` | Stage 3 — transcribe audio with Whisper (slow, CPU-heavy) |
| `make enhance` | Stage 4 — apply substitution rules to raw transcripts (fast) |
| `make all` | Run all four stages in order (skips already-done files) |
| `make run` | Run the full pipeline in a single Docker container invocation |
| `make status` | Show which files have been processed in each stage |
| `make logs` | Follow all service logs |
| `make clean` | Remove final output files (`data/05_output/`) |
| `make clean-status` | Remove status markers — forces all stages to re-run |
| `make clean-raw` | Remove raw transcripts (`data/04_raw/`) |
| `make reset` | Full cleanup: stop containers + remove all generated files |
| `make purge` | Reset + remove Docker volumes and images |
| `make everything` | Clean slate → build → run all stages |

---

## Configuration

Edit `.env` before building:

```env
# Whisper model for transcription (default: medium)
# Options: tiny | base | small | medium | large-v3
# Larger models are slower but more accurate.
WHISPER_MODEL=medium
```

---

## Data Directory Layout

```
data/
├── 03_audio/           # Input: audio files to transcribe
│   └── <name>_02_segments/# Auto-created: split audio chunks (from Stage 2)
├── 01_video/              # Input: video files to extract audio from
├── 02_segments/           # Input: time-segment definition files
├── substitutions.txt   # Input: substitution rules for Stage 4
├── 04_raw/                # Output: raw Whisper transcripts
├── 05_output/             # Output: final transcripts after substitution
└── status/             # Internal: completion markers for each stage
```

---

## Substitution Rules (`data/substitutions.txt`)

The Enhance stage applies text replacements to correct systematic Whisper errors (names, acronyms, antenna names, etc.).  
Rules are defined one per line in `data/substitutions.txt`.

### Format

```
wrong>correct           # optional inline comment
# full-line comment (ignored)
                        # blank lines are ignored
```

- Everything to the **left** of `>` is the text to find.
- Everything to the **right** of `>` is the replacement (up to `#`).
- Matching is **whole-word** (word boundaries) and **case-sensitive**.
- Multi-word phrases are supported on both sides.
- Rules are applied **in order** — put more specific rules before general ones if they overlap.

### Example

```
IJ>AEGEE                # Whisper commonly mishears "AEGEE" as "IJ"
Cijan>Ceyhan            # CD name correction
Clarity Director>Comité Directeur
```

### When the file is missing

If `data/substitutions.txt` does not exist, the Enhance stage still runs — it simply copies the raw transcripts to `data/05_output/` without any substitutions.

---

## Stage 1 — Extract (video → audio)

Converts video files to mono 16 kHz WAV audio using ffmpeg.

### Input

Place video files in `data/01_video/`.  
Supported formats: `.mp4`, `.mkv`, `.avi`, `.mov`, `.m4v`, `.ts`, `.wmv`

### Output

`data/03_audio/<name>.wav` — one WAV file per video, same stem as the source.

### Skipped when

`data/status/<name>.extracted` already exists.

### Notes

- This stage is fast and requires no GPU.
- If you already have audio files, skip this stage and place them directly in `data/03_audio/`.

---

## Stage 2 — Segment (split audio by time definitions)

Splits audio files into named chunks according to time-segment definition files.  
This is optional — files without a matching segment definition are not touched.

### Input

- Audio file: `data/03_audio/<name>.<ext>`
- Segment file: `data/02_segments/<name>.txt` (must share the same stem as the audio file)

### Segment file format

```
Label -> MM:SS - MM:SS
Label -> H:MM:SS - H:MM:SS
# This is a comment and is ignored
```

- Each line defines one chunk: a label and a start/end time.
- Both `MM:SS` and `H:MM:SS` formats are accepted.
- Lines starting with `#` and blank lines are ignored.
- Labels may contain spaces; they are converted to underscores in filenames.

Example (`data/02_segments/prytania_IA.txt`):

```
Activity Plan CD63 -> 18:00 - 19:45
Alumni -> 21:15 - 29:55
Communications -> 34:40 - 42:10
External relations -> 45:00 - 49:10
Fundraising and partnerships -> 51:50 - 53:10
Financial tools management -> 56:15 - 1:07:10
Network development -> 1:10:10 - 1:14:40
Statutes management -> 1:15:50 - 1:19:40
Entirety of the plan -> 1:19:50 - 1:23:00
```

### Output

`data/03_audio/<name>_02_segments/` directory containing:

```
00_Activity_Plan_CD63.wav
01_Alumni.wav
02_Communications.wav
...
```

Chunks are zero-padded and ordered as defined in the segment file.

### Skipped when

- `data/status/<name>.segmented` already exists, **or**
- No `data/02_segments/<name>.txt` file exists for that audio file.

### Notes

- Audio files without a segment file are passed whole to Stage 3.
- This stage is fast and requires no GPU.
- Files whose name starts with `EXAMPLE_` are ignored by all stages and can be used as reference samples in any data directory.

---

## Stage 3 — Transcribe (audio → raw transcript)

Transcribes each audio file using [OpenAI Whisper](https://github.com/openai/whisper).

### Input

Audio files in `data/03_audio/` (`.m4a`, `.mp3`, `.wav`, `.ogg`, `.flac`, `.webm`, `.opus`).  
If a `<name>_02_segments/` directory exists (from Stage 2), each chunk is transcribed separately.

### Output

`data/04_raw/<name>.txt` — timestamped transcript, one line per Whisper segment:

```
[00:00:05 --> 00:00:12] Hello everyone, welcome
[00:00:13 --> 00:00:22] to the Agora meeting today
```

For segmented files, sections are separated by headers and dividers:

```
## 00_Activity_Plan_CD63

[00:00:01 --> 00:00:08] ...

---

## 01_Alumni

[00:00:01 --> 00:00:05] ...
```

### Skipped when

`data/status/<name>.transcribed` already exists.

### Model caching

The Whisper model is downloaded from the internet on first use and then cached in a named Docker volume (`whisper_cache`).  
Subsequent runs — including container restarts — load the model from the cache without re-downloading.

### Notes

- Language is auto-detected by Whisper; no manual language selection is needed.
- This is the slowest stage. A 1-hour audio file may take 30–90 minutes on CPU depending on the model size.
- Use a smaller model (`tiny`, `base`, `small`) for faster results at lower accuracy.

---

## Stage 4 — Enhance (raw transcript → final output)

Applies text substitution rules to correct systematic Whisper errors (names, acronyms, antenna names, etc.).

### Input

- Raw transcripts from `data/04_raw/<name>.txt`
- Substitution rules from `data/substitutions.txt`

### Output

`data/05_output/<name>.txt` — corrected transcript with a title header:

```
# Transcription: <name>

[00:00:05 --> 00:00:12] Hello everyone, welcome to the AEGEE meeting
...
```

### Skipped when

`data/status/<name>.enhanced` already exists.

### Notes

- This stage is nearly instant regardless of transcript length.
- If `data/substitutions.txt` is missing, raw transcripts are copied to output unchanged.
- Rules use whole-word matching — `IJ>AEGEE` replaces the word "IJ" but not "IJ" inside "FIJI".
- Rules are case-sensitive.

---

## Status Markers

Each stage writes a marker file to `data/status/` when it completes:

| File | Meaning |
|---|---|
| `data/status/<name>.extracted` | audio has been extracted from video |
| `data/status/<name>.segmented` | audio has been split into chunks |
| `data/status/<name>.transcribed` | audio has been transcribed |
| `data/status/<name>.enhanced` | transcript has been enhanced |

Inspect a marker for details:

```bash
cat data/status/myfile.transcribed
```

Remove all markers to force a full re-run:

```bash
make clean-status
```

Remove only the transcribe + enhance markers to re-run those stages:

```bash
rm data/status/*.transcribed data/status/*.enhanced
```

---

## Whisper Model Sizes

| Model | Size | Relative speed | Notes |
|---|---|---|---|
| `tiny` | 75 MB | ~32× faster than large | Very rough; useful for drafts |
| `base` | 145 MB | ~16× faster | |
| `small` | 465 MB | ~6× faster | |
| `medium` | 1.5 GB | ~2× faster | **Default** — good balance |
| `large-v3` | 3 GB | 1× (baseline) | Best accuracy |

Change the model in `.env` and rebuild (`make build`) to apply.

---

## Project Structure

```
.
├── app/
│   ├── main.py           # Entry point and pipeline orchestration
│   ├── transcription.py  # Whisper-based audio transcription
│   ├── video.py          # Video to audio extraction
│   ├── segmentation.py   # Audio splitting by time segments
│   ├── diarization.py    # Speaker diarization stub (not yet active)
│   ├── entrypoint.sh     # Docker entrypoint
│   ├── requirements.txt
│   └── Dockerfile
├── data/
│   ├── 01_video/            # Input video files
│   ├── 02_segments/         # Segment definition files
│   ├── 03_audio/            # Input audio files
│   ├── 04_raw/              # Generated raw transcripts
│   ├── 05_output/           # Final transcripts
│   ├── substitutions.txt    # Substitution rules for Stage 4
│   └── status/              # Stage completion markers
├── docker-compose.yml
├── Makefile
└── .env
```

---

## Troubleshooting

**Transcription is very slow**  
Whisper runs on CPU by default inside Docker. Use a smaller model (`WHISPER_MODEL=small`) or enable GPU pass-through if your host has a CUDA-capable GPU.

**Whisper model is re-downloaded every time**  
The `whisper_cache` Docker volume persists the model between runs. If you accidentally deleted it (`make purge`), the model is re-downloaded once on the next `make transcribe` or `make all`.

**Enhance produces no changes**  
Check that `data/substitutions.txt` exists and contains valid `original>replacement` lines. Run `make status` to confirm the enhance stage ran.

**Segment chunks are out of order**  
Chunks are sorted alphabetically by filename. They are named `00_Label`, `01_Label`, … so order is determined by the zero-padded index, not the label. Ensure your segment file lists entries in the correct time order.
