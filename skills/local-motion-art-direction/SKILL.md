# Motion Art Direction

## Define the motion language first

- Define the motion language before anyone animates a frame, so every shot in the piece feels like it came from the same hand.

- Settle three questions before you pick a duration or a curve, by naming the emotional intent, the visual narrative from setup to resolution, and the motion craft that will make the movement believable.

- Place the piece on the tone and energy matrix by choosing calm or kinetic and soft or sharp, then commit to that one cell for the whole piece.

- Pick one motion personality for the project and apply it everywhere, using Playful for fun and bouncy work, Premium for elegant and minimal work, Corporate for clean and trustworthy work, and Energetic for bold and hype work.

- Lock one choice for each row of the motion language spec, covering the easing family, the base timing unit, the transition family, the stagger rhythm, the motion intensity budget, and the minimum hold between moves.

- Limit the piece to two eases, one for entrances and one for exits, and require any third curve to justify its existence.

- Map energy across the timeline before timing individual moves, with a low energy open, a build, a peak, and a settled end card.

## Pick numbers that feel physical

- Reserve linear motion for continuous loops such as spinners and marquees, and ease every discrete event so it accelerates or decelerates into rest.

- Use ease-out for entrances with cubic-bezier(0.16, 1, 0.3, 1), ease-in for exits with cubic-bezier(0.7, 0, 0.84, 0), ease-in-out for moves that stay on screen with cubic-bezier(0.65, 0, 0.35, 1), and a slight overshoot only for playful branded pops with cubic-bezier(0.34, 1.56, 0.64, 1).

- Scale duration to size and distance, using 100 to 200 milliseconds for micro interactions, 200 to 400 milliseconds for interface transitions, 400 to 800 milliseconds for hero elements, and 800 to 2000 milliseconds for cinematic camera moves.

- Add roughly 30 to 50 percent more duration when distance or area roughly doubles, so a full bleed panel never shares the timing of a small icon.

- Stagger grouped reveals by 40 to 80 milliseconds for lists and 20 to 40 milliseconds for dense grids, cap the total reveal near 700 milliseconds, and follow the eye from top to bottom or outward from a focal point.

- Keep any single travel under one third of the screen without an intermediate keyframe or a scale or opacity change, and keep no more than one third of the elements in active motion at once when three or more elements are present.

- Add anticipation with a small counter move of 60 to 120 milliseconds before the main action, then let trailing parts settle 40 to 80 milliseconds after the main body stops.

- Give organic movement a slight arc instead of a pure straight line translation, so the path reads as natural rather than mechanical.

- Land impact keyframes on the beat when motion accompanies audio, and establish a visual pulse of about one major event per 500 to 800 milliseconds when there is no music.

- Choose springs for interactive and interruptible motion with a snappy default of stiffness 300, damping 30, and mass 1, and choose duration plus easing for choreographed timeline locked sequences where exact sync matters.

- Diagnose stiff motion as linear or symmetric easing on an enter and switch it to ease-out, and diagnose floaty motion as a duration that is too long or an ease-out that is too gentle and cut the duration by about 30 percent.

- Diagnose cheap motion as elements appearing all at once or sharing one duration regardless of size, and fix it with stagger and size scaled timing.

- Diagnose mechanical motion as missing anticipation, follow-through, or arcs, and add those before changing the easing curve again.

## Rank what earns motion

- Rank every element as Hero, Support, or Texture, and animate down that list until the meaning is carried, then stop.

- Give the Hero the boldest, slowest, and most eased move in the shot, give Support a smaller and faster move that never competes, and keep Texture subliminal with slow loops and low contrast.

- Treat Hero, Support, and Texture as the same three layers as Primary, Secondary, and Ambient, so direction and craft share one vocabulary.

- Keep exactly one hero per frame, and demote any second element that competes for the eye to Support.

- Cut motion that does not carry meaning, and hold an element still when its movement adds nothing to the message.

- Avoid animating the entire frame at once, and stagger or hold an anchor so the eye has a home.

- Avoid stacking a transition on top of a transition, such as an animated wipe plus a spin plus a fade.

- Avoid looping text that the viewer is still reading, and avoid overshoot on serious or financial content where it reads as toy like.

- Allow only one wow moment per piece, since a second one cancels the first.

## Check consistency before you ship

- Audit every shot against the locked spec, and treat any mismatch as a direction defect rather than a craft preference.

- Confirm that comparable moves share the same easing family with no stray linear or default ease.

- Confirm that all durations are multiples of the base timing unit and that only the chosen transition family connects shots.

- Confirm that the stagger rhythm is identical across grouped reveals and that the hold discipline leaves stillness after each beat.

- Confirm that exactly one hero appears per frame and that no two primary moves compete in the same shot.

- Verify motion changes with frames at entrance, mid movement, and settle, and treat a wrong settled value or a covered overlay as a failure while forgiving a one pixel layout slip.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Read the worked direction playbook kept beside this skill for spec examples, a brief template, and a pre render checklist when the brief is large or the brand translation is unclear.

- Read the easing references kept beside the retired animation principles skill on disk for the full curve library, spring configs, Graph Editor recipes, and the twelve principles when a number or a hand shaped curve needs more detail.

- Use the pipeline specific motion language skill instead when the work is the daily AI news pipeline, since its terminal brisk tokens, brand colors, and safe areas override these general defaults.
