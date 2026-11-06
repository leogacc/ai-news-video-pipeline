# Animated Data Visualization

Turn numbers and structure into motion that reads: composed infographics, animated charts, and diagrams that reveal over time. These share one craft, so one skill covers all three: design the static frame first, reveal in hierarchy order, ease the values, then verify with frozen frames before you encode.

## Choose the right form

- Build a composed infographic when the ask is a designed scene of icons, key numbers, and short labels, such as "X in 3 steps" or "by the numbers".

- Build an animated chart when the data is the content: a bar chart race, a growing line, a count-up stat, or one chart design rendered across many datasets.

- Build a diagram reveal when the ask is structure: an architecture, flow, or sequence diagram that builds node by node, or data shown flowing along connectors.

- Scope any piece to one central insight with 3 to 5 supporting points in 30 to 90 seconds, since more competing elements read as chaos.

## Design the static frame first

- Lay out and balance the full composition with every element in its final position before adding a single keyframe, so the held final frame looks intentional rather than accidental.

- Reveal in importance order, not layout order: the title or central insight first and alone, then each icon, then its key number, then its label, then the connector that links finished items.

- Give sibling items a fixed stagger of 6 to 10 frames so the group reads as a sequence, and keep one enter curve across all siblings.

- Reveal diagrams as nodes first, then edges, then labels; highlight the active element while dimming the rest, and hold each step 0.5 to 1.5 seconds so it lands.

## Animate values and structure

- Drive every animated value from the current frame, never from wall-clock time or a library animation loop, so renders stay deterministic; in Remotion read `useCurrentFrame()`, and switch off third-party chart animations.

- Ease the value the same way you ease motion: let count-ups and growing bars settle with an ease-out, let rank changes glide on a spring, and keep steady time axes linear.

- Round every number before formatting, format with `Intl.NumberFormat`, and set tabular numerals so digits never jitter or clip as they change.

- Interpolate bar chart race values between sparse data rows, derive each bar's rank fresh every frame, and keep stable keys per item so overtakes glide instead of jumping.

- Draw connectors and edges on with a path-length technique, landing each line just as the item it points to finishes, so the motion leads the eye into the next reveal.

## Pick the build tool

- Use Remotion when the deliverable is a rendered video, since it is frame-deterministic and any exact frame can be rendered headlessly for inspection.

- Use inline animated SVG with GSAP or CSS for bespoke web diagrams, D3 for data-bound charts using its scales and shapes but never its timers, and Framer Motion for declarative React reveals.

- Honor `prefers-reduced-motion` on the web by showing the final composed diagram without looping motion.

- Keep datasets as input props rather than hardcoded constants, so one chart template renders every dataset in a folder with a single theme object holding colors, fonts, and layout.

## Verify before you ship

- Render single frames first at the start, the middle, and the final hold; inspect each PNG for exact numbers, correct labels, and artifacts like overflow or off-canvas elements; encode only after the stills check out.

- Freeze web diagrams with one master timeline and a control such as `?t=N`, screenshot the frozen start, middle, and end, and confirm the reveal order and the exact values.

- Confirm determinism: no `Date.now()`, no `Math.random()`, and no library timers; the shipped props must render correctly, not just the defaults.

- End video pieces on the complete composed frame held still for 2 to 3 seconds, so the takeaway lands and screenshots cleanly.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Compose a chart built from the chart recipes as one block inside a larger infographic instead of rebuilding it, keeping one visual language across the piece.

- Verify one representative dataset with stills before batch-rendering all variants, so a scale or mapping bug is caught once rather than in every output.

- Reuse the runnable recipes kept beside the retired skills on disk: `~/workspace/custom-skills/local-chart-animation/references/bar-chart-race.md`, `~/workspace/custom-skills/local-animated-infographic/references/sequenced-infographic.md`, and `~/workspace/custom-skills/local-diagram-animation/references/diagram-and-chart-recipes.md`.

- Render a GIF of the verified composition for the README after the MP4 is done.
