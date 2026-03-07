# Fragment Design Specification

> **Canvas**: 1080 × 1920 px (TikTok / IG Reels native)
> **Base Template**: `templates/fragments/base_fragment.html`

## Typography Tokens

All fragment templates MUST use these classes instead of hardcoded `font-size` values.
They are defined in `base_fragment.html` and render at TikTok-safe sizes on the 1080px canvas.

| Class | Size | Use For |
|---|---|---|
| `.frag-title` | 68px | Hero headlines, dish names |
| `.frag-heading` | 48px | Section titles, ingredient names, step numbers |
| `.frag-body` | 36px | Body text, descriptions, amounts |
| `.frag-label` | 29px | Uppercase labels, metadata tags, section markers |
| `.frag-small` | 25px | Captions, footnotes, page indicators (minimum readable) |

### Rules
- **Never use `font-size` below 22px** on the 1080px canvas — it will be unreadable on phones
- **Prefer token classes** over inline `font-size` styles
- If a design requires a custom size, it must be ≥ 26px for body text, ≥ 22px for captions

## Color Tokens (CSS Variables)

| Variable | Purpose |
|---|---|
| `--bg` | Page background |
| `--bg-lighter` | Card / surface background |
| `--accent` | Brand accent (buttons, highlights, amounts) |
| `--accent-dark` | Darker accent variant |
| `--fg` | Primary text color |
| `--fg-muted` | Secondary / muted text |
| `--fg-subtle` | Tertiary / very subtle text |
| `--card-bg` | Glass card background |
| `--card-border` | Card / divider borders |

### Rules
- **Always use CSS variables** for colors, never hardcode hex values (except in light-themed variants like `ingrid.v2`)
- This ensures theme switching (modern ↔ warm) works automatically

## Safe Zones

The 1080×1920 canvas has platform-imposed safe zones:

```
┌──────────────────────────────┐
│  TOP SAFE ZONE (120px)       │  ← TikTok UI overlays
├──────────────────────────────┤
│                              │
│     CONTENT AREA             │
│     px-16 (64px sides)       │
│                              │
├──────────────────────────────┤
│  BOTTOM SAFE ZONE (280px)    │  ← Captions, buttons, branding
└──────────────────────────────┘
```

- Use `pt-[120px]` or `pt-[130px]` for top padding
- Use `pb-[280px]` or `pb-[290px]` for bottom padding
- Use `px-16` (64px) for horizontal padding
- Or use the `.safe-box` class which applies all of these

## Layout Classes

| Class | Purpose |
|---|---|
| `.safe-box` | Content container with safe zone padding |
| `.full-bleed` | Edge-to-edge background (no padding) |
| `.card-glass` | Glassmorphism card with backdrop blur |
| `.bg-surface-grad` | Theme-aware background gradient |

## Fragment Density

For list-based fragments (ingredients, steps), use density-based spacing:

```
{% set density = 'spacious' if item_count <= 6 else ('compact' if item_count > 10 else 'normal') %}
```

- **spacious** (≤6 items): Larger gaps, bigger thumbnails
- **normal** (7–10 items): Standard spacing
- **compact** (>10 items): Tight spacing, smaller elements

## Versioning vs New Fragment

| Change Type | Use |
|---|---|
| CSS / HTML styling changes | **Version** (v2, v3 of same fragment) |
| Different data fields needed | **New fragment** |
| Different `build_sandbox_context` logic | **New fragment** |
| Same data, different visual treatment | **Version** |
| Can coexist in the same video | **New fragment** |
