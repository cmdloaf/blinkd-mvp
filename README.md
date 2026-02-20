# Blinkd

Blinkd is a constrained AI UX simulation engine. It evaluates product flows by simulating how specific user personas experience them — identifying friction, mapping it to documented UX failure patterns, and producing structured, actionable recommendations.

It is **not** a general UX advisor. It is a controlled diagnostic system grounded exclusively in an uploaded UX knowledge base.

---

## What It Does

You provide:
- A product description and value proposition
- Ordered screenshots of a user flow
- A persona (preset or custom)
- A goal the persona should be able to complete

Blinkd simulates that persona moving through your flow, produces a step-by-step inner monologue, identifies friction points mapped to documented UX patterns, and evaluates whether the persona can actually complete the stated goal.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django (Python) |
| Frontend | Server-rendered HTML + CSS (no JS frameworks) |
| LLM (primary) | Google Gemini |
| LLM (fallback) | Anthropic Claude |
| Database | SQLite (dev) |

LLM provider selection is automatic — Gemini is used if `GEMINI_API_KEY` is set; Claude is used as fallback if `ANTHROPIC_API_KEY` is set. No manual configuration needed.

---

## Setup

**1. Clone and install dependencies**
```bash
git clone <repo-url>
cd blinkd_mvp
pip install -r requirements.txt
```

**2. Configure environment variables**

Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here   # optional fallback
SECRET_KEY=your_django_secret_key
DEBUG=True
```

**3. Run migrations**
```bash
python manage.py migrate
```

**4. Start the development server**
```bash
python manage.py runserver
```

---

## The Wizard Flow

Analysis is set up through a 5-step wizard:

### Step 1 — Product Background (`/upload/step1/`)
Describe the product: what it does, its value proposition, and the target audience. This becomes the VARIABLE_KB context for the analysis.

### Step 2 — Screenshots (`/upload/step2/<flow_id>/`)
Upload screenshots of the product flow in order. Screenshots can be drag-reordered. Each image is uploaded immediately via XHR and persisted to the server. Uploading in the wrong order? Drag to fix before continuing.

### Step 3 — Persona (`/upload/step3/<flow_id>/`)
Choose who is simulating your flow:

**Preset personas** (loaded from `knowledge/personas/*.json`):
| Slug | Name |
|---|---|
| `rushing_executive` | The Rushing Executive |
| `cautious_first_timer` | The Cautious First-Timer |
| `busy_parent` | The Busy Parent |
| `detail_oriented_analyst` | The Detail-Oriented Analyst |
| `non_tech_senior` | The Non-Tech Senior |

**Custom persona** — describe your own persona in free text. The system sends it to the LLM to structure it into a full persona profile before analysis.

### Step 4 — Goals (`/upload/step4/<flow_id>/`)
Define what the persona should be able to accomplish in this flow. This becomes the PRIMARY USER GOAL — the central signal all friction and recommendations are evaluated against.

### Step 5 — Confirmation (`/upload/confirm/<flow_id>/`)
Review all inputs before submission. Each section has an Edit button that takes you back to that step and returns you here when done. No analysis runs until you click **Send to AI for Review**.

---

## Analysis Flow

When you submit from the confirmation screen:

1. `POST /upload/analysis/start/<flow_id>/` — Sets status to `processing`, spawns a background thread, redirects to the loading page
2. Loading page polls `/upload/analysis/status/<flow_id>/` every 5 seconds
3. On completion, JS redirects to `/upload/analysis/<flow_id>/` — the results dashboard

Duplicate submissions are blocked client-side (button disables on click) and server-side (repeat POSTs redirect to the loading page).

---

## Analysis Output

Results are structured into 5 sections:

**Section 1 — Product Understanding**
Whether the persona can immediately understand what the product does and what they're supposed to do next.

**Section 2 — Goal Achievability**
- Stated goal
- Achievable? (Yes / Partial / No)
- Step where goal breaks down
- Drop-off risk (Low / Medium / High)
- Root cause and direct blockers

**Section 3 — Persona Simulation**
Step-by-step walkthrough in the persona's voice: inner monologue, expectations, hesitations, confusion, emotional state, and verdict (Continue / Hesitate / Drop) per screenshot.

**Section 4 — Friction Summary**
Top friction points, each mapped to a pattern ID from the Global Knowledge Base with severity (High / Medium / Low) and persona-specific reasoning.

**Section 5 — Recommendations**
Actionable fixes, each tied to a KB pattern ID, with priority and goal impact label (Removes goal blocker / Improves goal completion / Clarifies goal pathway / No direct goal impact). Goal blockers are always ranked above cosmetic improvements.

---

## Knowledge Architecture

Blinkd uses three knowledge bases:

### Global KB — UX Failure Patterns
**Location:** `knowledge/global_ux/`

Three `.txt` files containing 34 documented bad UX patterns from authoritative sources. The LLM detects which patterns appear in your flow and infers good UX improvements from them. There are no pre-written "correct" answers — the inference is contextual.

| File | Source | Patterns |
|---|---|---|
| `kolenda.txt` | Nick Kolenda — UX Guidelines | 14 |
| `handbook_usability.txt` | Handbook of Usability and User Experience (CRC Press, 2022) | 10 |
| `norman.txt` | Don Norman — The Design of Everyday Things (2013) | 10 |

To add new patterns: append a new block (separated by `---`) to an existing file, or drop a new `.txt` file into `knowledge/global_ux/`. Restart the server. No code changes required.

### Persona KB — Preset Personas
**Location:** `knowledge/personas/*.json`

Each JSON file defines a complete persona with demographics, psychographics, behavioral traits, digital literacy, tool familiarity, motivations, emotional triggers, internal monologue style, and simulation rules.

To add a new preset persona: drop a new `.json` file into `knowledge/personas/`. No code changes required.

### Variable KB — Per-Analysis Context
Stored in the `ProductFlow` database model. Contains the product background, uploaded screenshots, persona selection, and user-defined goals specific to each analysis run.

---

## Project Structure

```
blinkd_mvp/
├── blinkd/
│   └── settings.py             # Django settings, reads API keys from .env
├── knowledge/
│   ├── global_ux/              # UX failure pattern TXT files (3 sources, 34 patterns)
│   └── personas/               # Preset persona JSON files
├── services/
│   └── kb_loader.py            # Loads Global KB + personas, builds system prompts
├── uploads/                    # Main Django app
│   ├── gemini.py               # Gemini API client
│   ├── anthropic_client.py     # Claude API client
│   ├── llm.py                  # Provider-agnostic router (Gemini-first fallback)
│   ├── models.py               # ProductFlow, Screenshot, AnalysisResult
│   ├── parsing.py              # Parses raw LLM output into structured dashboard data
│   ├── personas.py             # Prompt templates, re-exports kb_loader functions
│   ├── views.py                # Wizard steps, async analysis, loading screen
│   ├── urls.py                 # URL routing
│   └── templates/uploads/      # HTML templates
└── .env                        # API keys (gitignored)
```

---

## Extending the System

**Add a UX pattern:** Append a new block to any file in `knowledge/global_ux/` (separated by `---`) or drop a new `.txt` file in. Restart server.

**Add a persona:** Drop a new `.json` file into `knowledge/personas/` following the existing schema. Restart server.

Neither requires Python changes.

---

## Constraints

The AI is hard-constrained to:
- Use only the Global KB, Persona KB, and per-analysis Variable KB
- Reference a Pattern ID for every friction point identified
- Not fabricate UI elements not shown in screenshots
- Not import external UX frameworks, heuristics, or advice
- Flag missing information explicitly rather than guessing

If no matching pattern exists: `"No matching UX doctrine found in GLOBAL_KB."`
If data is insufficient: `"Insufficient information to evaluate [X]."`
