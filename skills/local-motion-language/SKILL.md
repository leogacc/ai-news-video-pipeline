

# Motion Language — AI News Pipeline

The channel's motion personality is **terminal-brisk**: fast, precise, no decoration. Motion serves the narration; it never performs for its own sake. When in doubt, hold still.

## Tokens

| Token | Value | Use |
|---|---|---|
| `--ease-enter` | easeOutCubic `1-(1-x)^3`, 300–500ms | anything appearing: badges, person photos, pills |
| `--ease-exit` | easeIn `cubic-bezier(0.7,0,0.84,0)`, 200–300ms | anything leaving |
| `--ease-move` | easeInOut, 300–400ms | repositioning |
| `--stagger` | 0.3s between intro person photos; 40–80ms for dense groups | sequential reveals, cap ~700ms total |
| `--badge-enter` | 0.4s: scale 0.92→1.0 ease-out + alpha fade | story number badge, every story shot |
| `--pill-fade` | 300ms in / 250ms out, no sliding | emphasis pills (user rule: fade only) |

Linear motion is reserved for continuous loops. Everything else eases. Overshoot is allowed on **geometry** (bars, lines) but **never on displayed digits** — a counter must settle on the exact fact, never flash a wrong number mid-roll (analytics.py: `_ease` for geometry, `_ease_out_cubic` for numbers).

## Hierarchy — what earns motion

- **Hero**: the evidence visual per shot (the thing the sentence is about).
- **Support**: story number badge, emphasis pills, intro person photos — one entrance move each, then static.
- **Texture**: terminal typing, film grain. Never the focus.

One shot, one intent. Never two competing primary moves.

## Restraint — what stays still

- The typewriter intro's character is fixed: letter-by-letter, cursor follows. No slide-ins on pills (user 2026-10-10).
- No mid-screen text without an analytical animation (user rule).
- Background is always black. No animated backgrounds.
- `#39FF14` neon green stays exactly (brand). Red `(255,70,70)` is reserved for the BREAKING kicker and lock/downward moments.

## Safe areas (1080×1920, TikTok UI)

Top 140px, bottom 20%, right 120px are platform chrome — no burned-in overlay may intrude. `render.py` writes `output/overlays.json` (single source of truth); `qa.py` fails the run on intrusion. Current geometry: badge right edge at x=960, watermark (60,190), captions anchored (60,1450), pills at x=540/y∈{320,960}.

## Pacing budgets (analytical animations)

Title types in (~0.8s) → values ease in staggered → final state holds. The renderer holds the last frame for the shot duration; the clip itself plays once, never loops. Digits: monospace is inherently tabular; center counters on their final width so rollovers don't jump sideways. Round before formatting; the settled frame must show the exact fact.

## Verification

Every motion change gets frame-verified: extract frames at entrance/mid/settle, tile a contact sheet, eyeball with your own eyes. A one-pixel layout bug is forgivable; a wrong digit or a covered overlay is not.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
