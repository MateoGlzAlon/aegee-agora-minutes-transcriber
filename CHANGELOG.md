# Changelog

All notable changes to this project are documented here.

## About the program

**AEGEE Agora Transcriber** is a fully local, no-external-API, no-Docker pipeline that
turns AEGEE Agora meeting recordings into corrected text transcripts. It runs four
idempotent stages — **Extract** (video → audio), **Segment** (split audio into named
time ranges), **Transcribe** (speech-to-text via OpenAI Whisper), and **Enhance** (apply
word-boundary substitution rules to fix systematic transcription errors) — orchestrated
through a `Makefile` and a Python helper (`scripts/run.py`). An optional persistent
daemon keeps the Whisper model loaded in memory across stage calls so it only pays the
model-load cost once per session instead of once per stage.

Two standalone utilities ship alongside the pipeline for auxiliary tasks: a legacy
WMA → MP3 audio converter (`01-tools/01-wma_to_mp3/`) and a plenary-PDF merger that
also builds a title-slide PPTX (`00-pdf_merger/`).

---

## [1.1.0] — 2026-08-19

Changes since `aegee-agora-transcriber-v1.0.0`.

### Added

- **Optional Tools documentation** — a new README section covering the two standalone
  utilities, each with its own `make` entry point:
  - `make wma_processing` — convert legacy `.wma` recordings to `.mp3` via
    `01-tools/01-wma_to_mp3/` (script + local Makefile).
  - `make pdf_merger` — merge plenary PDFs into a combined PDF and a title-slide PPTX
    via `00-pdf_merger/` (new local Makefile with `setup` / `merge` / `clean`).
  - Both targets, plus the previously-undocumented `make lint_segments`, are now listed
    in the README's "All Make Targets" table and in `make help`.
- **Absolute timestamps in segmented transcripts** — each line of a
  `<name>_SEGMENTS.txt` transcript now carries the segment's absolute time in the
  original recording alongside the existing chunk-relative time:
  `[00:00:00 --> 00:00:16] [00:03:15 --> 00:03:31] Thank you.`
- `.wma` added to the set of audio extensions Stage 3 (Transcribe) will pick up directly
  from `data/03_audio/`.
- Two new substitution rules in `data/substitutions.txt` (`AGI>AEGEE`, `My Eyes>MyAEGEE`).

### Changed

- Stage 1 (Extract) and Stage 2 (Segment) now output `.mp3` instead of uncompressed
  `.wav`, substantially reducing generated audio file size.

### Fixed

- `make wma_processing` was missing from the Makefile's `.PHONY` list.
- A `01-tools/` directory restructuring had silently broken `make wma_processing`
  (target pointed at a stale path) and the matching `.gitignore` rules; both corrected.
- Duplicate `.gitignore` rules removed (`daemon.log` was listed twice; `.claude/` and
  `.claude/*` were both present).

### Removed

- `app/llm.py` and `app/rag.py` — dead code from an earlier LLM/RAG-enhancement feature
  that was never wired into the pipeline; their dependencies (`chromadb`,
  `sentence-transformers`, `pypdf`, etc.) were never even in `app/requirements.txt`.
- `app/diarization.py` — unused speaker-diarization stub; nothing imported it.
- `docker-compose.yml`, `app/Dockerfile`, `app/entrypoint.sh` — the Docker path
  contradicted the README's "no Docker required" description and had drifted from the
  daemon-based local workflow; removed in favor of the single supported workflow.
- `OLLAMA_MODEL` from `.env` — configuration for the now-removed `llm.py`.
- `daemon.log` — a 351-line log file that had been committed to git; now purely local
  and gitignored.

---

## [1.0.0] — 2026-07-04

Initial tagged release: local four-stage transcription pipeline (extract / segment /
transcribe / enhance), persistent Whisper daemon, substitution-rule engine, and
segment-file linting.
