 <div align="center">
  <img src="Sales Pro Logo.png" alt="Sales Pro" width="100" />
  </div>

<div align="center">

# Sales Pro

**Turn any Instagram or YouTube sales video into a live, compounding sales brain.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Claude](https://img.shields.io/badge/Powered%20by-Claude%20Sonnet-D97706?style=flat-square)](https://anthropic.com)
[![Whisper](https://img.shields.io/badge/Transcription-OpenAI%20Whisper-412991?style=flat-square)](https://github.com/openai/whisper)
[![Obsidian](https://img.shields.io/badge/Vault-Obsidian-7C3AED?style=flat-square&logo=obsidian&logoColor=white)](https://obsidian.md)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

[**Quick Start**](#quick-start) · [**How It Works**](#how-it-works) · [**Commands**](#commands) · [**Vault Structure**](#vault-structure)

</div>

---

## What It Does

Drop any Instagram reel or YouTube URL. Sales Pro downloads the video, transcribes the audio locally with Whisper, sends the transcript to Claude for deep sales intelligence extraction, and writes structured, interlinked notes directly into your Obsidian vault.

Every tactic, hook, objection handle, value frame, and CTA gets its own atomic note — linked back to the source video. After 50+ videos, run the script generator and get a complete, battle-tested sales script built from real patterns your brain has collected.

```
Instagram / YouTube URL
        ↓
   yt-dlp download
        ↓
  ffmpeg audio extract
        ↓
  Whisper transcription  ←  local, free, no API
        ↓
   Claude analysis       ←  extracts 10+ structured fields
        ↓
  Obsidian vault write   ←  tactics · hooks · objections · creators
        ↓
  Sales script generate  ←  AIDA structure · A/B hooks · objection kill list
```

---

## Quick Start

**1. Clone and install**

```bash
git clone https://github.com/thedudebro11/Sales-Pro.git
cd Sales-Pro
pip3 install -r requirements.txt
```

**2. Configure**

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=your_key_here
VAULT_PATH=/path/to/your/ObsidianVault
WHISPER_MODEL=base
```

**3. Feed a video to the brain**

```bash
python3 main.py add https://www.instagram.com/reel/XXXXX/
python3 main.py add https://www.youtube.com/watch?v=XXXXX
```

**4. Generate a sales script**

```bash
python3 main.py script
```

**5. Check brain stats**

```bash
python3 main.py brain
```

---

## How It Works

### Stage 1 — Download
`yt-dlp` handles Instagram reels, posts, carousels, and YouTube videos. No login required for most content. Audio is extracted as a mono 16kHz WAV via `ffmpeg` — the exact format Whisper expects.

### Stage 2 — Transcribe
OpenAI Whisper runs entirely locally. No audio ever leaves your machine. The `base` model is fast and accurate for clear speech. Swap to `medium` or `large` in `.env` for mumbled or accented content.

### Stage 3 — Analyze
Claude reads the transcript and returns structured JSON with 12 fields:

| Field | What it captures |
|---|---|
| `title` | Descriptive title for the note |
| `creator` | Who made the video |
| `tone` | e.g. aggressive closer / educational / story-driven |
| `hooks` | `[{name, text}]` — typed hook patterns with exact quotes |
| `pain_points` | Every problem the video addresses |
| `tactics` | `[{name, description, quote}]` — named tactics with psychology |
| `objection_handles` | `[{objection, response}]` — exact objection + handle pairs |
| `value_stack` | Every benefit/value point offered |
| `proof_elements` | Social proof, stats, testimonials used |
| `scarcity_urgency` | Any urgency or scarcity framing |
| `cta` | The exact call to action |
| `transcript` | Full text |

### Stage 4 — Write to Vault
Notes are written as interlinked Obsidian markdown. Tactic, hook, and objection notes are **shared concept nodes** — if 20 videos use "Social Proof Stack," that tactic note accumulates 20 backlinks automatically. The library compounds in value with every video added. Duplicate URLs are detected and skipped.

### Stage 5 — Generate Scripts
The sales agent loads your entire vault as context and asks Claude to synthesize a custom script. You specify the product, audience, platform, tone, and goal. The output follows AIDA structure with 8 sections, 3 A/B hook variants, full tactic rationale, and an extended objection kill list.

---

## Commands

```bash
# Add any video to the brain
python3 main.py add <url>

# Generate a sales script (interactive prompts)
python3 main.py script

# View brain stats
python3 main.py brain
```

---

## Vault Structure

```
ObsidianVault/
└── sales/
    ├── _Index.md          ← master table of all analyzed videos
    ├── videos/            ← one detailed note per video
    ├── tactics/           ← atomic tactic concept nodes (deduplicated)
    ├── hooks/             ← hook pattern library by type
    ├── objections/        ← objection + handle pairs
    ├── creators/          ← per-creator video history
    └── scripts/           ← generated sales scripts
```

Every note uses `[[wiki-links]]` so Obsidian's graph view shows the full knowledge network. Open `Ctrl+G` in Obsidian to see how tactics cluster across creators and videos.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Get one at console.anthropic.com |
| `VAULT_PATH` | `C:/Users/oscar/ObsidianBrain` | Path to your Obsidian vault |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` / `large` |

**Whisper model tradeoffs:**

| Model | Size | Speed | Best for |
|---|---|---|---|
| `tiny` | 39 MB | Fastest | Quick tests |
| `base` | 74 MB | Fast | Clear speech, daily use |
| `small` | 244 MB | Medium | Accented speech |
| `medium` | 769 MB | Slow | High accuracy |
| `large` | 1.5 GB | Slowest | Maximum accuracy |

---

## Requirements

- Python 3.10+
- ffmpeg (installed system-wide)
- Anthropic API key
- Obsidian (optional but recommended for graph view)

```
yt-dlp
openai-whisper
anthropic
python-dotenv
rich
ffmpeg-python
```

---

## Cost

| Operation | Tool | Cost |
|---|---|---|
| Download | yt-dlp | Free |
| Transcribe | Whisper (local) | Free |
| Analyze video | Claude API | ~$0.01–0.05 per video |
| Generate script | Claude API | ~$0.05–0.15 per script |

A library of 100 analyzed videos costs roughly $2–5 in API credits total.

---

## Roadmap

- [ ] Batch URL processing from a text file
- [ ] Creator attribution from transcript self-introduction
- [ ] Semantic tactic deduplication (collapse near-identical tactic notes)
- [ ] Vector search over vault for smarter script generation
- [ ] Web UI for non-technical users

---

## License

MIT
