# Design System Specification: Industrial Command & Control
 
## 1. Overview & Creative North Star
The North Star for this design system is **"The Vigilant Architect."** 
 
In the high-stakes environment of automated barrier systems and industrial security, the interface must be more than a utility; it must be an authoritative partner. We are moving away from the cluttered, line-heavy "control room" aesthetic toward a sophisticated, editorial dashboard. This system utilizes intentional asymmetry, tonal depth, and high-contrast typography to ensure critical data (video feeds and alerts) feels prioritized, while administrative tasks recede into a refined, layered background. 
 
The goal is to provide a sense of absolute calm and precision. We achieve this by replacing rigid boxes with "zones of focus" defined by subtle shifts in light and texture.
 
---
 
## 2. Colors: Tonal Authority
Our palette is rooted in deep industrial blues and technical grays. To move beyond a "generic" feel, we rely on tonal shifts rather than structural lines.
 
### The Palette (Material Design Tokens)
*   **Primary (Action):** `#002e78` (Primary) / `#0043a7` (Primary Container)
*   **Safety/Success:** `#572500` (Tertiary - used here for warm, low-light visibility) / Custom Green Accents
*   **Alert/Danger:** `#ba1a1a` (Error) / `#ffdad6` (Error Container)
*   **Neutral Base:** `#faf8ff` (Surface) / `#283044` (Inverse Surface)
 
### Core Rules for Application
*   **The "No-Line" Rule:** Explicitly prohibit the use of 1px solid borders for sectioning. Structural boundaries must be defined solely through background shifts. For example, a video player module (`surface-container-high`) should sit directly on the dashboard base (`surface`) without a stroke.
*   **Surface Hierarchy & Nesting:** Use a "Physical Stacking" mental model. 
    *   **Level 0:** `surface` (The floor/base)
    *   **Level 1:** `surface-container-low` (Secondary sidebars)
    *   **Level 2:** `surface-container-high` (Primary data tables and video frames)
    *   **Level 3:** `surface-container-highest` (Floating modals or active alerts)
*   **The "Glass & Gradient" Rule:** Main barrier action buttons (Open/Close) should not be flat. Use a subtle linear gradient from `primary` to `primary_container` to give the button a "machined" tactile quality. For overlaying audio/mic toggles on top of video feeds, use **Glassmorphism**: `surface_variant` at 60% opacity with a `20px` backdrop-blur.
 
---
 
## 3. Typography: Editorial Precision
We utilize **Inter** for its neutral, technical clarity. The scale is designed to create an "Editorial Industrial" look—large, bold headers for status, and minuscule, high-contrast labels for technical metadata.
 
*   **Display (Status):** `display-md` (2.75rem). Use this for the primary state of the barrier (e.g., "SECURED" or "LOCKED").
*   **Headlines (Module Titles):** `headline-sm` (1.5rem). Used for "Live Feed" or "Entry Logs."
*   **Body (Data):** `body-md` (0.875rem). Used for table data and descriptions.
*   **Labels (Technical Metadata):** `label-sm` (0.6875rem) in `on_surface_variant`. Used for timestamps, IP addresses, and sensor readings.
 
**Editorial Tip:** To break the "template" look, pair a `display-sm` status indicator with a `label-sm` technical detail immediately below it, using a 4px gap to create a "tight" typographic unit.
 
---
 
## 4. Elevation & Depth: Tonal Layering
Traditional dropshadows are forbidden in this system. We use "Ambient Depth."
 
*   **Tonal Layering:** Depth is achieved by placing `surface_container_lowest` cards on a `surface_container_low` background. This creates a soft, natural lift that mimics high-end architectural materials.
*   **Ambient Shadows:** For floating emergency overrides, use a shadow with a 40px blur, 0px offset, and 6% opacity using the `on_surface` color. It should feel like a soft glow, not a shadow.
*   **The "Ghost Border" Fallback:** If a UI element (like a search bar) disappears into the background, use a "Ghost Border": `outline_variant` at 15% opacity. This provides a tactile edge without introducing visual noise.
 
---
 
## 5. Components: Industrial Sophistication
 
### Video Player Frames
*   **Style:** No borders. Use `roundedness-lg` (0.5rem). 
*   **Overlay:** Toggle buttons for Audio/Mic should be circular (`roundedness-full`), using the Glassmorphism rule. Place them in the bottom-right corner with a 16px inset.
 
### Data Tables (Entry/Exit Logs)
*   **The "No Divider" Rule:** Forbid horizontal lines between rows. Instead, use a subtle background hover state (`surface_container_high`) and generous vertical padding (16px) to separate entries.
*   **Status Indicators:** Instead of a simple colored dot, use a small, high-contrast Pill/Chip using `primary_fixed` for neutral and `error_container` for alerts.
 
### Large Action Buttons (The "Barrier Controls")
*   **Primary:** `primary` background, `on_primary` text. Use `roundedness-md` (0.375rem) for a professional, slightly sharp feel.
*   **Interaction:** On hover, transition to `primary_container`. On press, add a 2px "Ghost Border" of `primary`.
 
### Toggles & Controls
*   **Audio/Mic Toggles:** Use a "Switch" pattern. When "On," the track is `primary`; when "Off," the track is `surface_container_highest`. Avoid high-contrast grays to keep the focus on the video.
 
---
 
## 6. Do’s and Don’ts
 
### Do
*   **Do** use asymmetrical layouts. Place the video feed (large) off-center against the data logs (narrow) to create visual interest.
*   **Do** use `surface_dim` for "inactive" dashboard states to guide the user's eye to active alerts.
*   **Do** maintain 24px or 32px of "Breathing Room" between major containers.
 
### Don't
*   **Don't** use pure black `#000000` for text or shadows. Use `on_surface` (`#131b2e`) to maintain the deep blue industrial tone.
*   **Don't** use standard 1px dividers. If you must separate content, use a 8px wide vertical "spacer" of `surface_container_low`.
*   **Don't** use generic icons. Use thick-stroke (2px) technical icons that match the `outline` token weight.
 
---
 
## 7. Signature Element: The Command Header
To give the system a bespoke feel, the top navigation should not be a solid bar. Instead, use a transparent background with a `surface_container_lowest` "Floating Island" in the center that contains the system status and time. This breaks the grid and makes the system feel like a high-end, custom-engineered piece of hardware.