# Lower Thirds

Build a clean, branded lower third — the name/role caption that lives in the bottom band of the frame — that animates in, holds long enough to read, and exits without stealing the shot. The craft is restraint: a crisp reveal, a strong type hierarchy, correct safe-area placement, and one template that drives a whole roster of speakers.

## When to use

- Speaker/interview name tags, panel rosters, talking-head captions.

- Broadcast-style titles, news straps, podcast/webinar name plates.

- Templating one design across a list of names/titles → many clips (the payoff).

## Anatomy

A lower third is two text lines plus a graphic bed, placed in the lower band. Keep it to two lines. A name line + role line is the whole job.

## Three rules that prevent cheap-looking titles

1. Never hard-cut a title on or off.

2. Stagger, don't slam. Animate the bar first, then the name, then the role, each offset by 3–6 frames.

3. Hold long enough to read twice. Roughly 3–5s on screen.

## Enter & exit animations

Pick one motion language and reuse it. Use asymmetric easing: a snappy ease-out on enter, a quicker ease-in on exit. Exit faster than you entered.

## In/out timing & dwell

Think in three phases at 30fps: Enter 12–18f, Hold 90–150f, Exit 8–12f. Drive every state from the current frame, not wall-clock time.

## Safe area & broadcast conventions

Compose inside the title-safe area (inner ~90% / margin 5%) and respect platform chrome. For 9:16, lift the band up and avoid the bottom ~18% and top ~12%. Anchor to the left and grow rightward.

## Type hierarchy & brand styling

Make the name unmistakably dominant: size contrast ≥ 1.6×, name bold and near-white, role lighter with one brand accent color, text over a solid or semi-opaque bar, scrim, or soft shadow.

## Templating one design across a list

Make name/role/theme props, never hardcoded, then map a roster to instances. In a renderer, render once per row to emit one branded clip per person.

## Output checklist

- Two lines only: dominant name, secondary role (≥1.6× size contrast).

- Animated in and out (no hard cut); enter staggered bar→name→role; exit faster.

- Hold 3–5s; motion only at the ends, never mid-segment.

- Left-anchored inside title-safe; 9:16 band lifted above the bottom UI zone.

- Text legible over any plate; one brand accent throughout.

- Name/role/theme are props — one template renders the whole roster.

## Deliver & verify (rendered stills → MP4)

Verify with stills at enter, dwell, and exit using shipped props (a real roster row, not defaults), inspect the dwell frame for hierarchy, brand lock, legibility, and 9:16 safe area, then encode. Verify ONE row via stills before rendering all names.

## Reference files

- `references/lower-third-component.md` — a complete runnable lower-third: a Remotion component with staggered spring enter, readable hold, and faster exit driven purely by frame; a typed theme object for brand lock; the list→many-instances sequencing pattern; a per-row batch render script; plus a dependency-free CSS/HTML version of the same design with mask-reveal and wipe-bar variants.

## Available connectors

Use `muse.connector_search` to find the current connector docs before following recovered instructions.
