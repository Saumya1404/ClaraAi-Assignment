# Clara AI — Zero-Cost Agent Configuration Pipeline

An automated pipeline that converts raw demo-call and onboarding-call transcripts into structured Retell AI agent configurations — entirely at zero cost.

## Architecture & Data Flow

```
 ┌──────────────┐     ┌──────────────┐
 │  Audio File  │────▶│ faster-whisper│──── transcript.txt
 └──────────────┘     │  (local STT) │
                      └──────────────┘

 Pipeline A  (Demo Call → v1 Agent)
 ─────────────────────────────────────────────────────────
  transcript.txt
      │
      ▼
 ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
 │  n8n Trigger│───▶│ Gemini Flash│───▶│ account_memo │
 │ (file watch)│    │  (extract)  │    │    .json (v1) │
 └─────────────┘    └─────────────┘    └──────┬───────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │ agent_spec   │
                                       │   .json (v1) │
                                       └──────────────┘
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                    ▼
                             validation_flags.json   task_tracker.json


 Pipeline B  (Onboarding → v2 Agent)
 ─────────────────────────────────────────────────────────
  onboarding_transcript.txt + v1/account_memo.json
      │
      ▼
 ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
 │  n8n Trigger│───▶│ Gemini Flash│───▶│ account_memo │
 │ (file watch)│    │(merge + diff)│   │   .json (v2) │
 └─────────────┘    └─────────────┘    └──────┬───────┘
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                    ▼
                             agent_spec.json (v2)   changelog.json

```

### Component Summary

| Component | Role | Cost |
|-----------|------|------|
| **n8n** (Docker, self-hosted) | Workflow orchestration, file triggers, JSON I/O | Free |
| **Gemini Flash** (free tier) | LLM extraction & agent spec generation | Free |
| **faster-whisper** (local) | Audio → text transcription via CTranslate2 | Free |
| **Asana** (free tier) | Task tracking — review items created per account | Free |

## Prerequisites

- **Docker & Docker Compose** — to run n8n
- **Python 3.12+** and **uv** — to run the transcription script
- A free **Google Gemini API key** — [Get one here](https://aistudio.google.com/app/apikey)
- A free **Asana account** — [Sign up here](https://asana.com/create-account)

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/Saumya1404/ClaraAi-Assignment.git
cd ClaraAi-Assignment

# Create your env file
cp .env.example .env
# Edit .env with your local values
```

### 2. Start n8n

```bash
docker-compose up -d
```

n8n will be available at **http://localhost:5678**.  
Default credentials (set in `.env`): `admin@clara.com` / `Clara123`

### 3. Import workflows

1. Open n8n → **Workflows** → **Import from File**
2. Import both:
   - `n8n/workflows/Pipeline A(v1) - Complete.json`
    - `n8n/workflows/Pipeline B(v2) - Complete.json`
3. In each workflow, open the **Gemini Chat Model** nodes and attach your Google Gemini credential in the n8n UI
4. In each workflow, open the **Create Asana Task** node and attach an **Asana API** credential in the n8n UI using your Personal Access Token
5. **Activate** each workflow (toggle at top-right)

### 3a. Configure Asana

1. In Asana, go to **My Settings → Apps → Personal Access Tokens** and create a token
2. In n8n, go to **Credentials** → **Create Credential** → **Asana API** and paste that token there
3. Add these to your `.env` file:
    ```
    ASANA_WORKSPACE_GID=your_workspace_gid
    ASANA_PROJECT_GID=your_project_gid
    ```
4. To find the IDs: open a project in Asana and copy the numeric IDs from the URL, or use the [Asana API Explorer](https://developers.asana.com/docs/api-explorer)
5. Restart n8n after changing `.env` so the container reloads the values

The workflow JSONs do not include any access tokens or credential bindings. Gemini and Asana credentials are intentionally attached after import from the n8n UI, while `ASANA_WORKSPACE_GID` and `ASANA_PROJECT_GID` are still read from `.env`.

> The Asana request node has `continueOnFail` enabled — if the credential is missing or invalid, the workflow will still complete and save all JSON files locally.

## Workflow Comparison

- `n8n/workflows/Pipeline A(v1) - Complete.json` is the canonical v1 workflow. The similarly named `Pipeline A (v1) - Complete.json` is an older export with a fixed manual test path, different model selection, different node IDs/layout, and older credential wiring.
- Pipeline A creates the initial `v1` account memo from a demo call, validates critical fields, and writes `validation_flags.json`.
- Pipeline B requires an existing v1 memo, identifies the account from an onboarding call, merges updates into `v2`, and writes `changelog.json` alongside the refreshed `agent_spec.json`.
- Both workflows now follow the same credential rule: no access tokens or API keys are exported in workflow JSON; credentials must be attached in the n8n UI after import.

### 4. Transcribe audio (if you have audio files)

```bash
# Install dependencies
uv sync

# Transcribe all audio in default directories
uv run scripts/transcribe.py

# Or transcribe a specific file
uv run scripts/transcribe.py inputs/demo_calls/call.m4a

# Use a larger model for better accuracy
uv run scripts/transcribe.py --model medium inputs/onboarding_calls
```

Transcripts are written as `.txt` files alongside the audio files.

### 5. Run the pipelines

**Option A — Auto-trigger (file watch):**  
With workflows activated, simply drop a `.txt` transcript into:
- `inputs/demo_calls/` → triggers Pipeline A → outputs to `outputs/accounts/<account_id>/v1/`
- `inputs/onboarding_calls/` → triggers Pipeline B → outputs to `outputs/accounts/<account_id>/v2/`

> **Windows/macOS note:** The file trigger uses polling mode to work reliably with Docker bind mounts. If the trigger doesn't fire, verify "Use Polling" is enabled in the trigger node options.

**Option B — Manual trigger:**  
Each workflow has a **Manual Test Trigger** node. Click **Test Workflow** in the n8n editor to run it against all `.txt` files in the watched directory.

## Where Outputs Are Stored

```
outputs/
├── accounts/
│   └── <account_id>/
│       ├── v1/
│       │   ├── account_memo.json       # Extracted business config
│       │   ├── agent_spec.json         # Retell agent draft spec
│       │   └── validation_flags.json   # Missing-field warnings
│       └── v2/
│           ├── account_memo.json       # Merged config (onboarding updates)
│           ├── agent_spec.json         # Updated agent spec
│           └── changelog.json          # Field-level diff v1 → v2
└── tasks/
    └── <account_id>_v1_task.json       # Task tracker entries
```

### Output Descriptions

| File | Description |
|------|-------------|
| `account_memo.json` | Structured JSON with business hours, services, emergency rules, routing, integrations |
| `agent_spec.json` | Retell-ready agent configuration (persona, greeting, call flows, extracted from memo) |
| `validation_flags.json` | Lists any critical fields that are missing or null after extraction |
| `changelog.json` | Per-field diff showing v1 → v2 changes, reasons, and conflict flags |
| `*_task.json` | Task tracker entry with status, timestamps, and output file paths |

This project tracks workflow tasks in two ways:
- **Local JSON files** in `outputs/tasks/` (always written)
- **Asana tasks** created automatically in your configured project (if Asana credentials are set)

## Pipeline Details

### Pipeline A — Demo Call → v1 Agent

1. **Trigger**: Watches `inputs/demo_calls/` for new `.txt` files (or manual trigger)
2. **Read & extract text** from the transcript file
3. **LLM extraction** (Gemini Flash) → structured `account_memo.json` with all business config fields
4. **Post-processing**: Derives `account_id` from company name, adds version/timestamp metadata
5. **Idempotency gate**: Checks if v1 output already exists — skips if so
6. **Agent spec generation** (Gemini Flash) → `agent_spec.json` with persona, greeting, call flows
7. **Validation**: Flags missing critical fields → `validation_flags.json`
8. **Task tracker**: Creates a local task JSON + Asana task for review

### Pipeline B — Onboarding → v2 Agent

1. **Trigger**: Watches `inputs/onboarding_calls/` for new `.txt` files (or manual trigger)
2. **Identify account**: LLM extracts company name from onboarding transcript to find matching v1
3. **Load v1 memo**: Reads existing `account_memo.json` from the account's v1 directory
4. **Extract updates & conflicts** (Gemini Flash): Compares onboarding transcript against v1 memo, identifies changes and flags conflicts
5. **Non-destructive merge**: Applies updates to produce v2 `account_memo.json` (v1 preserved intact)
6. **Regenerate agent spec**: Produces updated `agent_spec.json` from v2 memo
7. **Changelog**: Generates field-level `changelog.json` with v1 values, v2 values, reasons, and conflict flags
8. **Task tracker**: Creates a local task JSON + Asana task for review

## Plugging In Dataset Files

1. Place demo-call transcripts (`.txt`) in `inputs/demo_calls/`
2. Place onboarding-call transcripts (`.txt`) in `inputs/onboarding_calls/`
3. If you have audio files instead, place them in the same directories and run:
   ```bash
   uv run scripts/transcribe.py
   ```
4. Activate both workflows in n8n — they will auto-process new files

For batch processing, you can drop all transcript files at once; the file watch trigger will pick up each one sequentially.

## Retell AI Integration

This pipeline generates `agent_spec.json` files that are structured for Retell AI agent configuration. To deploy:

1. Create a [Retell AI](https://www.retellai.com/) account
2. Open the generated `agent_spec.json` for your account
3. In the Retell dashboard, create a new agent and paste the configuration:
   - **Agent name** / **Persona** / **Greeting** from the spec
   - **Call flows** (office hours, after hours, emergency) mapped to Retell's flow builder
4. The `account_memo.json` provides all the business rules the agent needs

> On the free tier, Retell does not expose full API access — manual paste into the UI is required.

## Project Structure

```
├── docker-compose.yml          # n8n container config
├── .env.example                # Environment variables template
├── pyproject.toml              # Python project config (uv)
├── inputs/
│   ├── demo_calls/             # Drop demo transcripts here
│   └── onboarding_calls/       # Drop onboarding transcripts here
├── outputs/
│   ├── accounts/<id>/v1/       # Pipeline A outputs
│   ├── accounts/<id>/v2/       # Pipeline B outputs
│   └── tasks/                  # Task tracker entries
├── prompts/                    # LLM prompt templates (reference)
├── scripts/
│   └── transcribe.py           # Local Whisper transcription
└── n8n/
    └── workflows/              # Importable n8n workflow JSONs
```

## Known Limitations

- **No Retell API integration**: Free-tier Retell does not allow programmatic agent creation — the generated `agent_spec.json` must be manually pasted into the Retell UI
- **Single-file triggers**: The file-watch trigger processes one file at a time; concurrent drops may queue
- **Account matching heuristic**: Pipeline B identifies the account by asking the LLM to extract the company name from the onboarding transcript, then matches it to existing v1 output by `account_id`. If the company name is phrased differently across calls, the match may fail
- **LLM extraction accuracy**: Gemini Flash occasionally misses or misinterprets fields from noisy transcripts; `validation_flags.json` helps catch these gaps
- **Windows Docker file events**: Docker bind mounts on Windows don't forward native filesystem events. Polling mode is enabled as a workaround, which adds a small delay before trigger fires
- **Lightweight task tracking**: Task artifacts are stored as local JSON files and also pushed to Asana. If Asana credentials are not configured, local files are still created (the Asana node uses `continueOnFail`)

## What I Would Improve With Production Access

- **Retell API integration**: Automate agent creation and updates via Retell's API (programmatic provisioning instead of manual paste)
- **Persistent task management**: Add assignees, due dates, and SLA tracking via Asana API (currently creates basic tasks)
- **Database storage**: Replace flat-file JSON with a proper database (PostgreSQL) for querying, versioning, and audit trails
- **Diff viewer UI**: Build a simple web dashboard to visualize v1 → v2 changes with highlighted diffs
- **Batch metrics**: Aggregate extraction stats across accounts — field coverage, conflict rates, processing times
- **Webhook triggers**: Replace file-watch polling with webhook-based triggers from an upload endpoint
- **Multi-model fallback**: Add a fallback chain (e.g., Gemini → local Llama) for reliability
- **Confidence scoring**: Have the LLM output confidence per field so reviewers can focus on low-confidence extractions
- **Automated tests**: Validate output schemas against a test suite of known-good transcripts
- **CI/CD**: Auto-deploy workflow changes and run regression tests on PR merge