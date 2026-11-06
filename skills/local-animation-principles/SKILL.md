# Motion Principles

Decide how something should move so it feels right, independent of the tool used to build it. This skill answers timing, easing, spacing, weight, and rhythm. It does not pick a tech stack. It produces concrete numbers ready to hand to any implementation.

## When to use

- Motion feels stiff, floaty, mechanical, robotic, or cheap and needs diagnosis.

- Choosing a clip or transition duration, easing curve, and stagger offset.

- Reviewing whether motion respects physics intuition.

- Synchronizing keyframes to a musical beat or edit accent.

## Core method

- Settle emotional intent, visual narrative, and motion craft before picking a duration or curve.

- Use Primary, Secondary, and Ambient as the three motion layers, matching Hero, Support, and Texture in motion art direction.

- Use ease-out for entrances, ease-in for exits, and ease-in-out for moves that stay on screen, and reserve linear motion for continuous loops.

- Scale duration to size and distance, stagger grouped reveals, keep travel under one third of the screen without an intermediate keyframe, and add anticipation and follow-through.

- Land impact keyframes on the beat, and choose springs for interactive motion and duration plus easing for timeline locked sequences.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Use the merged local_motion_art_direction skill for motion direction, easing, timing, and diagnosis, and read its references for the full curve library and Graph Editor recipes kept beside this retired skill on disk.
