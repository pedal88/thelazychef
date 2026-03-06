# Media Hub: Lego-Fragment Content System

This document outlines the architecture, components, and capabilities of the Media Hub's "Lego-Fragment Content System", designed to automatically render rich, native-feeling social media and marketing assets from database recipe records.

## 1. Core Architecture

The Media Hub generates 1080x1920 (Portrait/9:16) PNG images suitable for TikTok, Instagram Reels, YouTube Shorts, and Pinterest. Instead of manually editing images, the system relies on a **Headless Browser Pipeline**:

1. **Jinja2 Templates:** Web templates powered by Tailwind CSS structure the layout.
2. **Context Builders:** Python logic extracts, shapes, handles missing values, and groups Recipe data.
3. **Playwright Engine (`snapshotter.py`):** Instantiates a headless Chromium instance to render the HTML visually and snap high-fidelity PNG copies, which are then stored in Google Cloud Storage.

## 2. The Snapshotter Engine

Located at `media_hub/snapshotter.py`, the engine is the brain of the image generation factory.

- **SmartOverflow (Pagination):** When lists (like Ingredients or Steps) are too long for a single 1920px image, the Snapshotter automatically paginates them. (e.g., `MAX_INGREDIENTS_PER_PAGE = 14`).
- **Density Awareness:** Layout dynamically adjusts padding, image sizes, and font sizes based on the item count (`spacious` for small lists, `normal` for average, `compact` for large lists).
- **Component Support:** Automatically groups ingredients and steps per dish component (e.g., "Main", "Sauce", "Garnish") using distinct headers and color coding.
- **Async Execution wait:** For complex graph visualization (like the Flavor Galaxy), Playwright explicitly waits for an HTML `[data-rendered="true"]` signal from D3.js before capturing the PNG.

## 3. Fragment Types

Recipes are broken down into self-contained "Fragments."

| Fragment | Description | Key Features |
| :--- | :--- | :--- |
| **Hero** | The hook image (`hero.html`) | Full-bleed cover photo with a `backdrop-blur` glassmorphism card covering the bottom 20% to display the dish name without white-space bloat. |
| **Meta** | Key details (`meta.html`) | Displays difficulty, time, servings, and cuisine. Condenses dynamically into a horizontal ribbon (`compact_meta`) if the recipe requires many separate ingredient pages. |
| **Nutrition** | Health facts (`nutrition.html`)| Features a dynamic SVG circular calorie-completion ring and color-coded macro detail cards (Protein, Carbs, Fats). |
| **Ingredients** | The shopping list (`ingredients.html`)| Automatically lists ingredients with visual icons/initial boxes, organized by component. Density-aware vertical spacing. |
| **Steps** | Cooking instructions (`steps.html`) | Clean, numbered instructions with estimated per-step time expectations. Density-aware typography. |
| **Galaxy** | Flavor profile (`galaxy.html`) | Client-side D3.js layout rendering a force-directed graph bridging the recipe's core flavor affinities. |

## 4. Design & Theming System

The base template (`base_fragment.html`) provides a robust foundation across all fragments:

*   **Responsive Typography Fixed to Portrait:** Uses Tailwind `clamp()` functions (`frag-title`, `frag-heading`, `frag-body`) that smoothly scale relative to the fixed 1080x1920 dimension. 
*   **Systematic CSS Var Theming:** The Python Snapshotter injects a `theme` dictionary containing CSS variables (`--fg`, `--bg`, `--accent`, etc.).
    *   **Modern (Default):** High-contrast dark mode with sleek slate/neon orange accents.
    *   **Classic:** A light, cream-based aesthetic with warm amber accents for a softer, organic vibe.
*   **Platform "Safe Box":** Strictly adheres to a universal content layout box (120px clearance at the top, 280px at the bottom, 64px on sides) ensuring text never vanishes under native TikTok interfaces (like buttons or username overlays).

## 5. Developer Tools & Sandbox

To avoid spinning up the entire backend snapshotter pipeline for every CSS tweak, the system includes a robust Developer Sandbox at `/admin/media-hub/sandbox`.

*   **Responsive 2-Column GUI**: The Sandbox utilizes a streamlined, two-column layout. The left pane provides controls (Recipe ID, Theme, Safe Zones) and a minimalist button grid for selecting fragment types. The right pane hosts a dedicated inline `<iframe>` to instantly preview the selected fragment without opening new tabs.
*   **Smart Auto-Scaling**: The fragment templates (`base_fragment.html`) contain injected vanilla Javascript that reads the browser's viewport on load. Since fragments are strictly hardcoded to 1080x1920, the Javascript dynamically calculates the necessary decimal scale and applies a CSS `transform: scale(X)` footprint to shrink and perfectly center the 9:16 canvas within the developer's window, emulating a mobile device bezel. When evaluated by the Playwright Headless engine, it forcibly overrides the scale back to `1.0` to preserve pixel-perfect rendering down the pipeline.
*   **Query Capabilities:** 
    *   `?recipe_id=XY`: Render with real template data.
    *   `?theme=classic`: Hot-swap visual themes.
    *   `?debug=true`: Activates the **TikTok Safe Zones Debug Overlay**. Overlays semi-transparent red/blue blocks showing exactly where TikTok's native right-sidebar (Likes/Shares) and bottom caption blocks sit, guaranteeing zero clipping.

## 6. Admin User Interface

The Media Hub provides an interface at `/admin/media-hub` for staff to interact with the pipeline.

- Adds a "🧱 Fragments" preview button onto each approved recipe row.
- Spawns a dedicated preview carousel modal (Arrow keys, Esc-key support, and infinite scrolling supported) to preview the complete sequence of generated fragments before they are exported to external social pipelines.
