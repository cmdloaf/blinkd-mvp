# BLINKD — FRONTEND DESIGN SYSTEM CONTRACT

This document is the authoritative design specification for all frontend code in the Blinkd application. Every template, stylesheet, and UI component must conform to the rules defined here. No exceptions without explicit justification.

---

## 1. DESIGN PHILOSOPHY

Blinkd is a structured UX intelligence tool. The interface must reflect analytical precision, executive clarity, and confident restraint.

### Brand Character

- Executive-grade
- Analytical
- Modern
- Minimal
- High signal, low noise
- Structured
- Clean
- Confident

### Blinkd Is NOT

- Playful
- Decorative
- Marketing-heavy
- Visually chaotic

### Design Principles

1. **Clarity over decoration.** Every element must serve an informational purpose.
2. **Hierarchy over uniformity.** Critical data surfaces first; supporting detail is accessible but not competing.
3. **Whitespace is structural.** Generous spacing is not wasted space — it creates scanability and focus.
4. **Dense information, high organization.** Dashboards carry significant data density but must remain visually ordered.
5. **Restraint over expression.** No unnecessary gradients, no random colors, no ornamental effects.

### All Frontend Changes Must

- Prioritize clarity above all else.
- Avoid clutter and visual noise.
- Surface key information immediately.
- Maintain consistent visual rhythm.
- Respect the defined color, typography, and spacing systems.

---

## 2. TYPOGRAPHY SYSTEM

### Font Families

Blinkd uses a dual-font system: Alexandria for display elements, system-ui for body content.

**Display font (headings, titles, labels):**
```
font-family: 'Alexandria', sans-serif;
```

**Body font (paragraphs, descriptions, content):**
```
font-family: system-ui, sans-serif;
```

Alexandria provides strong visual identity for headings and structural elements. `system-ui` provides native readability and comfort for body text, matching the user's OS for optimal legibility.

### Type Hierarchy

| Level | Font | Usage | Weight | Characteristics |
|-------|------|-------|--------|-----------------|
| **H1** | Alexandria | Page titles, primary headings | Bold (700) | Large, strong presence, commanding |
| **H2** | Alexandria | Section headers | Semi-bold (600) | Clear section delineation |
| **H3** | Alexandria | Card titles, sub-section headers | Bold (700) | Compact authority |
| **Body** | system-ui | Paragraphs, descriptions, content | Regular (400) | Readable, comfortable line-height |
| **Muted** | system-ui | Secondary labels, metadata | Regular (400) | Reduced opacity (0.6–0.7) |
| **Badge** | Alexandria | Status indicators, severity labels | Medium (500) | Uppercase, small size |

### Typography Rules

- **No serif fonts.** Only Alexandria and system-ui are permitted.
- **No additional font families.** Do not introduce typefaces beyond the two defined above.
- **No arbitrary font weights.** Use only 400, 500, 600, and 700 as defined above.
- **No tight line-height.** Body text must have sufficient leading for comfortable reading (minimum 1.5 line-height for body copy).
- **No long unbroken paragraphs.** Dashboard contexts must break content into scannable chunks. Use lists, short paragraphs, or card structures.

---

## 3. COLOR SYSTEM

### Theme

Blinkd uses a **dark theme** as its canonical visual identity. The deep navy base conveys executive authority and analytical seriousness.

### Semantic Color Tokens

| Token | Value | Usage |
|-------|-------|-------|
| **Primary Background** | `#010122` | Deep navy. Page body background, base surface. |
| **Card Background** | `#0C0C30` | Slightly elevated navy. All card and panel surfaces. |
| **Elevated Surface** | `rgba(255, 255, 255, 0.04)` | Panel headers, collapsible headers, subtle elevation. |
| **Primary Accent** | `#6142C0` | Primary purple. Buttons, active states, links, primary interactive elements. |
| **Accent Dark** | `#4E198C` | Deep accent purple. Hover states, emphasis, secondary accent. |
| **Soft Accent** | `rgba(97, 66, 192, 0.18)` | Translucent purple. Subtle highlights, light badges, background accents. |
| **Primary Text** | `rgba(255, 255, 255, 0.92)` | High-contrast light text on dark backgrounds. |
| **Muted Text** | `rgba(255, 255, 255, 0.45)` | Soft light text. Secondary labels, metadata, helper text. |
| **Borders** | `rgba(255, 255, 255, 0.07)` | Subtle light borders and dividers on dark surfaces. |
| **Accent Glow** | `rgba(97, 66, 192, 0.25)` | Hover border glow on interactive cards. |
| **Danger** | `#DC3545` | Red. High severity, critical alerts, destructive actions. |
| **Warning** | `#F59E0B` | Amber. Medium severity, caution states. |
| **Success** | `#10B981` | Green. Positive status, achievable goals, confirmations. |
| **Neutral Badge** | `#6B7280` | Grey. Low severity, informational, insufficient data. |

Status badge text colors on dark backgrounds use lighter variants (e.g., `#F87171` for danger text, `#34D399` for success text, `#FBBF24` for warning text) to ensure readability.

### Color Rules

- **No arbitrary hex values.** Every color used in templates and stylesheets must map to a defined token above. Introducing a new color requires explicit justification and addition to this table.
- **Semantic application only.** Colors are assigned by meaning, not aesthetics. Danger red is for high severity — never for decoration.
- **No decorative gradients.** Flat, solid colors only. Subtle opacity variations are permitted for hover/focus states.
- **Contrast compliance.** All text-on-background combinations must maintain readable contrast ratios.

---

## 4. CARD DESIGN SYSTEM

Cards are the primary content container across all Blinkd dashboards. Every data unit — recommendations, friction items, simulation steps, metrics — renders within a card.

### Card Styling

| Property | Specification |
|----------|--------------|
| Background | `#0C0C30` (Card Background token) |
| Border radius | `14px` (consistent across all cards) |
| Border | `1px solid rgba(255, 255, 255, 0.07)` (thin, clean) |
| Shadow | `none` — cards are border-defined, no box-shadows |
| Padding | `24px` minimum (internal content padding) |
| Margin-bottom | `16px` minimum (vertical spacing between cards) |
| Hover | Border transitions to `rgba(97, 66, 192, 0.25)` accent glow |

### Card Rules

- **No box-shadows.** Cards are defined by thin borders only. No drop shadows of any kind.
- **No glossy gradients.** Card surfaces are flat.
- **No 3D effects.** No transforms, perspective shifts, or simulated depth.
- **Hover states use accent glow.** Interactive cards show a subtle purple border glow on hover, not shadow lift.
- **Generous padding.** Content must never feel cramped within a card.
- **Clear vertical spacing.** Cards must be visually separated from each other.
- **Cards must not touch container edges.** Maintain horizontal padding from page margins.

### Recommendation Card Structure

Each recommendation card must follow this layout:

1. **Title** — One-sentence actionable statement (bold, H3 level). First sentence of the actionable fix.
2. **Summary** — 1–2 sentence context (muted text). First sentence of the observed problem.
3. **Severity badge** — Aligned top-right of the card header.
4. **Goal impact badge** — Inline, colored, when applicable.
5. **Expandable details** — Collapsible section containing: Root Cause, Violated Pattern, Full Fix, Expected Outcome, Goal Impact.

**Critical:** Never render raw LLM text blocks. All AI output must be parsed and structured into the defined card format before display.

### Friction Card Structure

1. **Description** — Bold, primary statement of the friction point.
2. **Root cause summary** — Muted text, brief context.
3. **Expandable details** — "Root Cause" and "Why [Persona] Struggles" in collapsible section.

---

## 5. BADGE SYSTEM

Badges communicate status and severity at a glance. They are the primary visual signal for priority and outcome.

### Badge Styling

| Property | Specification |
|----------|--------------|
| Shape | Pill (fully rounded ends) |
| Text transform | Uppercase |
| Font weight | 500 (Medium) |
| Font size | Small (0.75rem) |
| Padding | `4px 12px` |
| Border radius | `9999px` |

### Severity Badges

| Severity | Background | Text Color |
|----------|-----------|------------|
| **High** | `#DC3545` (Danger) | `#FFFFFF` |
| **Medium** | `#F59E0B` (Warning) | `#1A1A2E` |
| **Low** | `#E5E7EB` (Neutral light) | `#4B5563` |

### Goal Status Badges

| Status | Background | Text Color |
|--------|-----------|------------|
| **Achievable (Yes)** | `#10B981` (Success) | `#FFFFFF` |
| **Partial** | `#F59E0B` (Warning) | `#1A1A2E` |
| **Not Achievable (No)** | `#DC3545` (Danger) | `#FFFFFF` |
| **Insufficient Data** | `#6B7280` (Neutral Badge) | `#FFFFFF` |

### Badge Rules

- **No additional badge styles.** Only the severity and goal status variants defined above are permitted.
- **Clear contrast.** Badge text must be legible against its background at all times.
- **Consistent sizing.** All badges use the same padding, font size, and border radius.
- **No outline-only badges.** All badges use filled backgrounds for maximum scanability.

---

## 6. SPACING SYSTEM

All spacing values derive from an **8px base grid**. This creates consistent visual rhythm across every page and component.

### Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | `4px` | Tight internal spacing (badge padding, inline gaps) |
| `sm` | `8px` | Compact spacing (between related elements) |
| `md` | `16px` | Standard spacing (card gaps, paragraph margins) |
| `lg` | `24px` | Generous spacing (card internal padding, section gaps) |
| `xl` | `32px` | Section separation |
| `2xl` | `48px` | Major section breaks, page-level vertical rhythm |
| `3xl` | `56px–80px` | Top-level page padding, hero spacing |

### Radius Scale

| Token | Value | Usage |
|-------|-------|-------|
| `card` | `14px` | Cards, panels, confirm sections |
| `input` | `10px` | Buttons, inputs, textareas |
| `badge` | `9999px` | Pill-shaped badges |

### Spacing Rules

- **Section spacing must be generous.** Use `xl` or `2xl` between major dashboard sections.
- **Cards must not touch edges.** Maintain minimum `lg` horizontal padding from page container edges.
- **No cramped layouts.** If elements feel tight, increase spacing. Err on the side of breathing room.
- **Consistent horizontal padding.** Left and right padding within any container must be equal.
- **Vertical rhythm must be preserved.** Sequential elements of the same type must use identical vertical gaps.
- **Grid alignment.** All spacing values should be multiples of 8px. Exceptions only for the 4px micro-spacing token.

---

## 7. DASHBOARD RULES

Dashboards are the primary output surface for Blinkd analysis results. They must communicate complex UX analysis clearly and efficiently.

### Dashboards Must

- **Surface top-level metrics clearly.** Key numbers (critical issues count, problematic steps, goal achievability) must be immediately visible without scrolling.
- **Use short, scannable insight titles.** No paragraph-length headers.
- **Hide detailed reasoning under expandable sections.** The default view is summary-level; depth is opt-in.
- **Avoid text-heavy blobs.** Break content into cards, lists, and structured groups.
- **Avoid repeating structured metadata inline.** If data appears in a badge or metric tile, do not restate it in body text.

### Dashboards Must Never Display

- **Pattern IDs in user-facing text.** Pattern IDs (e.g., `kolenda_choice_overload`, `norman_poor_feedback`) are internal identifiers. They must be stripped from all displayed content.
- **Raw markdown formatting.** No asterisks, hash symbols, or markdown syntax in rendered output.
- **LLM prompt artifacts.** No system prompt leakage, no instruction fragments, no structural markers from AI output.
- **Duplicated text blocks.** If the same information appears in a title and body, remove the redundancy.
- **Unstructured AI output.** All LLM responses must be parsed and rendered through the defined card and badge systems. Never dump raw text.

---

## 8. ENFORCEMENT RULE

This document is a binding contract for all frontend modifications. Compliance is not optional.

### Before Every Frontend Change, Claude Code Must

1. **Check against this CLAUDE.md.** Verify that the proposed change conforms to every applicable section.
2. **Follow defined color tokens.** No hex value may appear in templates or stylesheets that is not defined in Section 3.
3. **Follow Alexandria typography rules.** All text must use the Alexandria font family with approved weights from Section 2.
4. **Maintain the spacing system.** All margins and padding must align to the 8px grid defined in Section 6.
5. **Apply card and badge standards.** Any new UI element that displays data must follow the card structure (Section 4) and badge system (Section 5).
6. **Preserve dashboard conventions.** Analysis result pages must follow the display and suppression rules in Section 7.
7. **Avoid design drift.** Do not introduce one-off styling, ad hoc color values, or inconsistent component patterns.

### If a Proposed Change Violates This Contract

The change must be corrected before implementation. Do not merge, commit, or present non-conforming frontend code. Identify the specific violation, reference the relevant section of this document, and revise the implementation to comply.

### Scope

This contract applies to all files within `uploads/templates/` and any associated CSS, inline styles, or JavaScript that affects visual presentation. It does not govern backend logic, API contracts, or non-visual infrastructure.