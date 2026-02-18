# BLINKD — CLAUDE OPERATING SPEC (MVP)

## 1. PURPOSE
Blinkd is a constrained AI UX simulation engine.
It evaluates product flows using:
- A file-driven Global UX Knowledge Base (paired UX doctrine patterns)
- Modular persona templates (loaded from JSON files)
- Client-specific product input

Primary output:
Persona-based friction analysis + structured, actionable UX recommendations grounded exclusively in the Global KB.

Blinkd is NOT a general advisor. It is a controlled UX diagnostic system.


--------------------------------------------------
## 2. TECH STACK CONTEXT

Backend: Django (Python)
Frontend: HTML + CSS (server-rendered templates)
LLM Providers: Gemini (primary), Anthropic Claude (fallback)

### Wizard Flow
The setup wizard follows this strict order:
1. **Product Background** (`/upload/step1/`) — product description, value prop, audience
2. **Screenshots** (`/upload/step2/<flow_id>/`) — upload & drag-to-reorder flow screenshots
3. **Persona** (`/upload/step3/<flow_id>/`) — select preset or custom persona
4. **Goals** (`/upload/step4/<flow_id>/`) — define what the persona should achieve
5. **Confirmation** (`/upload/confirm/<flow_id>/`) — review all inputs with Edit buttons before AI submission

The confirmation screen shows a structured preview of all user inputs (background, screenshots, persona, goals) with per-section Edit buttons. Clicking Edit navigates to the relevant step with `?next=confirm` so the user returns to confirmation after editing instead of continuing the normal wizard flow.

AI analysis is triggered only from the confirmation screen via "Send to AI for Review".

### Analysis Flow (Async)
When the user clicks "Send to AI for Review":
1. `POST /upload/analysis/start/<flow_id>/` — sets `analysis_status="processing"`, spawns a background thread, redirects to loading page
2. `/upload/analysis/loading/<flow_id>/` — shows a loading screen with CSS spinner, rotating progress messages, and JS polling
3. `/upload/analysis/status/<flow_id>/` — JSON endpoint returning `{"status": "processing|complete|failed"}`, polled every 5 seconds
4. On completion → JS redirects to `/upload/analysis/<flow_id>/` (results page)

Duplicate submission is prevented via:
- Client-side: button disables on click
- Server-side: if `analysis_status == "processing"`, redirects to loading page without re-running

### LLM Provider Priority
The system automatically detects available API keys and routes requests:
- **Gemini first** (if `GEMINI_API_KEY` is set)
- **Anthropic fallback** (if `ANTHROPIC_API_KEY` is set and Gemini fails)
- No manual `LLM_PROVIDER` setting needed — priority is automatic
- Both `structure_custom_persona()` and `run_analysis()` follow this fallback chain

When suggesting improvements:
- Assume server-rendered flows.
- Avoid SPA-specific assumptions unless specified.
- Feature suggestions must be realistic within Django + HTML/CSS architecture.
- Do not assume React, Vue, mobile apps, or complex JS frameworks unless explicitly stated.


--------------------------------------------------
## 3. KNOWLEDGE ARCHITECTURE

### A. GLOBAL_KB (File-Driven, Bad-UX-Only, Inference Model)
Location: `knowledge/global_ux/`

Each TXT file contains multiple bad UX patterns from a single source. The LLM infers good UX improvements from the detected bad patterns — there are no explicit "Good UX Principle" or "Actionable Correction" fields.

**Sources (3 files, 34 patterns total):**

| File | Source | Patterns |
|---|---|---|
| `kolenda.txt` | Nick Kolenda — UX Guidelines (kolenda.io) | 14 |
| `handbook_usability.txt` | Handbook of Usability and User Experience (CRC Press, 2022) | 10 |
| `norman.txt` | Don Norman — The Design of Everyday Things (2013) | 10 |

**Pattern IDs by source:**
- **Kolenda**: `kolenda_choice_overload`, `kolenda_no_context`, `kolenda_no_feedback`, `kolenda_no_input_tolerance`, `kolenda_goal_misalignment`, `kolenda_assumed_knowledge`, `kolenda_hard_to_interact`, `kolenda_accusatory_errors`, `kolenda_no_safe_exit`, `kolenda_unpredictable_outcomes`, `kolenda_ignores_skimming`, `kolenda_poor_location_awareness`, `kolenda_hidden_interactivity`, `kolenda_visual_noise`
- **Handbook**: `handbook_goal_misalignment`, `handbook_ignoring_context`, `handbook_assumed_expertise`, `handbook_poor_feedback`, `handbook_low_error_tolerance`, `handbook_task_interface_mismatch`, `handbook_inconsistent_behavior`, `handbook_no_user_control`, `handbook_poor_learnability`, `handbook_no_real_user_testing`
- **Norman**: `norman_poor_discoverability`, `norman_misleading_signifiers`, `norman_mental_model_mismatch`, `norman_gulf_of_execution`, `norman_gulf_of_evaluation`, `norman_blames_user`, `norman_overcomplexity`, `norman_poor_feedback`, `norman_ignoring_error`, `norman_no_recovery`

**TXT file format (multi-pattern, `---` separated):**
```
TITLE: <source title>
SOURCE: <attribution>

INFERENCE RULE:
When a BAD UX pattern is detected, infer a GOOD UX improvement that:
- reduces cognitive load
- improves clarity toward the stated user goal
- aligns with the selected persona's expectations
- avoids prescribing UI styling or visual aesthetics
- remains actionable and context-aware

---

ID: <pattern_id>
Category: <category>

Description:
<what the bad pattern looks like>

Symptoms:
- <symptom 1>
- <symptom 2>

Impact:
<impact description>

---

ID: <next_pattern_id>
...
```

**Expandability:** To add patterns, either add new pattern blocks to an existing file (separated by `---`) or drop a new `.txt` file into `knowledge/global_ux/`. Restart the server. No Python code changes required.

Loaded by `services/kb_loader.py` → `load_global_ux_patterns()` and injected into every AI system prompt via `format_global_kb_for_prompt()`.

Treat as authoritative UX reference. Recommendations MUST reference GLOBAL_KB patterns only. The LLM infers fixes from the bad patterns.

---

### B. PERSONA_KB (File-Driven)
Location: `knowledge/personas/*.json`

Each persona is a single JSON file containing:
- `slug` — unique identifier
- `name` — display name
- `description` — persona summary
- `traits` — quick trait labels (for UI display)
- `demographics` — age_range, role, income, devices
- `psychographics` — values, approach, risk_tolerance, patience, efficiency_bias
- `behavioral_traits` — how they interact with products
- `digital_literacy` — comfort level with technology
- `tool_familiarity` — apps/tools they use regularly
- `motivations` — what drives them
- `emotional_triggers` — what frustrates or delights them
- `internal_monologue_style` — how they think
- `simulation_rules` — persona-specific behavior constraints

Current personas: `rushing_executive`, `cautious_first_timer`, `busy_parent`, `detail_oriented_analyst`, `non_tech_senior`

**Expandability:** To add a new persona, drop a new `.json` file into `knowledge/personas/`. No Python code changes required.

Loaded by `services/kb_loader.py` → `load_all_personas()` and built into system prompts via `build_system_prompt()`.

All simulations must strictly reflect persona constraints.

---

### C. VARIABLE_KB (Per Client)
Stored in the Django `ProductFlow` model. Includes:
- Product description / value proposition / target audience
- Screenshots (ordered flow images)
- Persona selection (preset or custom)
- User-defined goals: what the persona should achieve within the flow

Defines the test environment for each analysis run.

---

### D. HARD CONSTRAINTS
The AI MUST:
- Use only GLOBAL_KB + PERSONA_KB + VARIABLE_KB
- Reference Pattern IDs when identifying friction
- Infer good UX improvements from the matched bad UX pattern
- Not fabricate missing features
- Not assume missing UI elements
- Not introduce external UX knowledge, frameworks, or heuristics
- Not provide generic startup advice
- Flag missing data instead of guessing

If no matching pattern exists in GLOBAL_KB:
Return → "No matching UX doctrine found in GLOBAL_KB."

If insufficient info:
Return → "Insufficient information to evaluate [X]."


--------------------------------------------------
## 4. CORE ENGINE LOGIC

For each persona:

1. Load persona traits from `knowledge/personas/<slug>.json`
2. Load Global KB from `knowledge/global_ux/`
3. Load product + flow context + user goals from ProductFlow
4. Inject all three KBs into the system prompt
5. Simulate step-by-step interaction against stated goals
6. Evaluate goal achievability — can the persona achieve the PRIMARY USER GOAL through this flow?
7. Identify friction and map to Pattern IDs from GLOBAL_KB
8. Generate recommendations by inferring good UX improvements from the detected bad patterns

Simulation must:
- Reflect persona psychology
- Show inner monologue
- Identify hesitation
- Identify confusion
- Assess drop-off risk
- Assess error likelihood
- Explicitly evaluate whether the persona can achieve the PRIMARY USER GOAL


--------------------------------------------------
## 5. PRODUCT CLARITY CHECK

Always evaluate:
- Does persona understand what product does?
- Is value proposition clear?
- Is next action obvious?
- Is onboarding self-explanatory?
- Can the persona complete the PRIMARY USER GOAL within this flow?

If unclear:
- Identify breakdown point
- Map to violated UX pattern (must be a Pattern ID from GLOBAL_KB)
- Recommend fix (inferred from the matched bad UX pattern)


--------------------------------------------------
## 6. FRICTION DETECTION RULES

Check for (must map to GLOBAL_KB Pattern IDs — 34 patterns across 3 sources):
- Choice overload, cognitive overload, visual noise (`kolenda_choice_overload`, `kolenda_visual_noise`, `norman_overcomplexity`)
- Poor feedback / system status (`kolenda_no_feedback`, `handbook_poor_feedback`, `norman_poor_feedback`, `norman_gulf_of_evaluation`)
- Error handling failures (`kolenda_no_input_tolerance`, `kolenda_accusatory_errors`, `handbook_low_error_tolerance`, `norman_blames_user`, `norman_ignoring_error`)
- Goal/task misalignment (`kolenda_goal_misalignment`, `handbook_goal_misalignment`, `handbook_task_interface_mismatch`)
- Discoverability / interactivity issues (`kolenda_hidden_interactivity`, `norman_poor_discoverability`, `norman_misleading_signifiers`)
- Mental model mismatch (`kolenda_unpredictable_outcomes`, `norman_mental_model_mismatch`, `handbook_inconsistent_behavior`)
- Onboarding / assumed knowledge (`kolenda_assumed_knowledge`, `handbook_assumed_expertise`, `handbook_poor_learnability`)
- Navigation / location awareness (`kolenda_poor_location_awareness`, `kolenda_ignores_skimming`, `kolenda_no_context`)
- Trust / recovery (`kolenda_no_safe_exit`, `norman_no_recovery`, `handbook_no_user_control`)
- Context of use (`handbook_ignoring_context`, `norman_gulf_of_execution`)

Each friction must include:
- Pattern ID (from GLOBAL_KB)
- Persona reasoning
- Severity (Low/Medium/High)

Severity reweighting:
- Friction that directly blocks goal completion → auto High severity
- Cosmetic friction not affecting goal → deprioritized to Low unless compounding


--------------------------------------------------
## 7. OUTPUT FORMAT (MANDATORY)

### SECTION 1 — PRODUCT UNDERSTANDING
- Clarity status
- Early confusion signals

### SECTION 2 — GOAL ACHIEVABILITY
- Stated User Goal
- Achievable? (Yes / Partial / No)
- Breakdown Step (step # or "N/A")
- Drop-off Risk (Low / Medium / High)
- Root Cause of Goal Failure (reference Pattern ID if applicable, or "N/A")
- Direct Blockers (list, or "None identified")

If no goal provided → "Insufficient information to evaluate goal achievability."

### SECTION 3 — PERSONA SIMULATION
Per step:
- Step #
- Inner monologue
- Expectation
- Hesitation
- Confusion reason
- Emotional state
- Verdict: Continue / Hesitate / Drop

### SECTION 4 — FRICTION SUMMARY
Top issues (each MUST reference a Pattern ID from GLOBAL_KB):
- Description
- Pattern ID
- Severity
- Root cause (referencing the bad UX pattern from the KB)
- Affected persona reasoning

Goal-blocking friction → auto High severity. Cosmetic friction → Low unless compounding.

### SECTION 5 — RECOMMENDATIONS
For each (MUST reference a Pattern ID and infer a good UX fix from the bad pattern):
1. Observed Problem
2. Pattern ID
3. Why It Happens (persona reasoning)
4. Violated Pattern (the bad UX pattern from the KB — no external patterns)
5. Actionable Fix (realistic within Django + HTML/CSS, inferred from the bad UX pattern)
6. Expected Impact
7. Priority (Low/Med/High)
8. Goal Impact ("Removes goal blocker" / "Improves goal completion" / "Clarifies goal pathway" / "No direct goal impact")

Recommendations removing goal blockers MUST be ranked higher than cosmetic improvements.


--------------------------------------------------
## 8. SIMULATION BEHAVIOR RULES

- Low digital literacy → higher hesitation.
- Experienced users → expect efficiency.
- Risk-averse users → react strongly to ambiguity.
- Impatient users → sensitive to workflow length.
- Trust-sensitive users → react to unclear data usage.

No generic emotional output.
All reactions must tie to persona traits.


--------------------------------------------------
## 9. SCOPE LIMITS

Do NOT:
- Use internet knowledge unless explicitly enabled.
- Compare competitors unless data is provided.
- Infer UI not shown in screenshots.
- Fill missing steps with imagination.
- Suggest tech incompatible with Django + HTML/CSS unless requested.
- Introduce UX frameworks, heuristics, or principles outside GLOBAL_KB.

If data incomplete → explicitly flag it.


--------------------------------------------------
## 10. SUCCESS CONDITIONS

Valid output must:
- Be persona-consistent
- Be goal-evaluative (every analysis explicitly judges whether the persona can achieve the stated goal)
- Be friction-traceable (every friction maps to a GLOBAL_KB Pattern ID)
- Contain actionable recommendations (each inferred from the matched bad UX pattern)
- Avoid hallucinations (no UX advice outside uploaded doctrine)
- Follow structure exactly

Primary objective:
Goal-oriented UX feasibility evaluation + structured diagnosis + implementable improvements, fully grounded in uploaded UX doctrine.


--------------------------------------------------
## 11. PROJECT STRUCTURE

```
blinkd_mvp/
├── blinkd/                     # Django project settings
│   └── settings.py             # GEMINI_API_KEY, ANTHROPIC_API_KEY (from .env)
├── knowledge/                  # File-driven knowledge bases (no Python edits to extend)
│   ├── global_ux/              # Bad-UX-only multi-pattern TXT files (3 sources, 34 patterns)
│   └── personas/               # Persona JSON files
├── services/
│   └── kb_loader.py            # Loads personas + Global KB from files, builds prompts
├── uploads/                    # Main Django app
│   ├── anthropic_client.py     # Anthropic Claude API client
│   ├── gemini.py               # Google Gemini API client
│   ├── llm.py                  # Provider-agnostic LLM interface (Gemini-first fallback)
│   ├── models.py               # ProductFlow, Screenshot, AnalysisResult
│   ├── parsing.py              # Analysis response parser
│   ├── personas.py             # Prompt templates, re-exports kb_loader functions
│   ├── views.py                # Wizard steps, async analysis, loading screen
│   ├── urls.py                 # URL routing
│   └── templates/uploads/      # Server-rendered HTML templates
└── .env                        # API keys (gitignored)
```

### Key Files
- `services/kb_loader.py` — Central loader for both PERSONA_KB and GLOBAL_KB. Functions: `load_all_personas()`, `load_global_ux_patterns()`, `format_global_kb_for_prompt()`, `build_system_prompt()`
- `uploads/personas.py` — Prompt templates (`OUTPUT_FORMAT_INSTRUCTIONS`, `BASE_SIMULATION_PROMPT`, `CUSTOM_STRUCTURING_PROMPT`, `GOAL_ACHIEVABILITY_CHECK`) and `get_system_prompt()` which injects Global KB into persona prompts
- `uploads/parsing.py` — Parses raw LLM output into structured data for the dashboard. Key functions: `parse_analysis_sections()`, `parse_goal_achievability()`, `parse_recommendations()`, `parse_friction_items()`, `parse_simulation_steps()`, `parse_executive_summary()`
- `uploads/llm.py` — Provider routing: tries Gemini first, falls back to Anthropic. No config needed beyond setting API keys in `.env`


--------------------------------------------------
## 12. ANALYSIS RESULTS PARSING

### Section Splitting
`parse_analysis_sections()` splits raw LLM output on `## SECTION <N> — <TITLE>` headers.
- **5-section format** (current): product_understanding, goal_achievability, persona_simulation, friction_summary, recommendations
- **4-section format** (legacy): product_understanding, persona_simulation, friction_summary, recommendations (no goal_achievability)
- Legacy results still render correctly — the goal achievability tile simply doesn't appear.

### Field Extraction
`_extract_field(block, field_name)` extracts values after `**Field Name**:` markers. Handles multiple AI output formats:
- `**Field**: value` (inline)
- `1. **Field**: value` (numbered)
- `*   **Field**: value` (bullet-indented, common from Gemini)
- `- **Field**: value` (dash bullet)

**Critical**: Do NOT call `clean_llm_output()` on text before passing to `_extract_field()` — it strips `**` markers that the regex needs.

### Goal Achievability Parsing
`parse_goal_achievability()` extracts: `stated_goal`, `achievable` (Yes/Partial/No), `breakdown_step`, `dropoff_risk` (High/Medium/Low), `root_cause`, `direct_blockers`. Returns `None` if the field is empty or unparseable (never defaults to "Unknown").

### Recommendation Card Structure
Each parsed recommendation contains:
- `title` — First sentence of `actionable_fix` (action-oriented, for card header)
- `summary` — First sentence of `observed_problem` (brief context, for card body)
- `pattern_id` — Cleaned (brackets/backticks stripped), used internally only
- `goal_impact` — "Removes goal blocker" / "Improves goal completion" / "Clarifies goal pathway" / "No direct goal impact"
- Full fields (`observed_problem`, `why_it_happens`, `violated_pattern`, `actionable_fix`, `expected_impact`) shown only in expandable details

### Pattern ID Display
Pattern IDs are internal identifiers used by the LLM for friction tracing. They are **never shown to end users**:
- `clean_llm_output()` strips bracketed pattern IDs (e.g., `[kolenda_choice_overload]`) from all displayed text
- The template does not render pattern_id fields in cards
- Pattern IDs remain in the parsed data for debugging/traceability but are hidden from the UI

### Dashboard Metrics
`_build_dashboard_context()` computes:
- `critical_count` = high-priority recs + high-severity friction + goal blockers (non-high-priority recs with "blocker" in goal_impact)
- `problematic_steps_count` = steps with verdict "Drop" or "Hesitate"
- `goal_achievable` = achievable status from goal achievability parsing

### UI Card Design Rules
- **Recommendation cards**: Title (bold) + summary (muted) + goal impact badge (inline, colored) + "View details" toggle. Expandable details show: "Root Cause", "Violated Pattern", "Full Fix", "Expected Outcome", "Goal Impact".
- **Friction cards**: Description (bold) + root cause summary (muted) + "View details" toggle. Expandable details show: "Root Cause", "Why [persona] Struggles".
- No pattern IDs visible to end users. All displayed text is cleaned of bracketed pattern IDs by `clean_llm_output()`.


--------------------------------------------------
## 13. DEVELOPMENT RULES

When modifying any system in this project:
1. **Update this file** — Any change to prompts, output format, parsing logic, dashboard metrics, or UI structure must be reflected in the relevant section of this CLAUDE.md.
2. **Backward compatibility** — Parsing changes must handle both current and legacy AI output formats. Never break rendering of existing `AnalysisResult` records.
3. **Parsing safety** — Never call `clean_llm_output()` before `_extract_field()`. Extract fields from raw markdown first, clean values after.
4. **No SPA patterns** — All UI changes must work within Django server-rendered templates + vanilla CSS/JS. No React, Vue, or frontend frameworks.
5. **Goal-first evaluation** — Goal achievability is the primary diagnostic signal. Friction severity and recommendation priority must reflect goal impact.
