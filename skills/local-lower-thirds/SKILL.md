# Lower thirds

Build the name and role graphic that sits in the lower band of the frame, animates in, holds still long enough to read, and leaves without stealing the shot. The two learned lower third skills taught the same craft under different names, so this merged skill covers both deliveries and lets the destination choose the build.

## Choose the delivery first

- Ask where the graphic will play before you build anything, since the destination fixes the file and the build tool.

- Build a transparent overlay for OBS, a livestream, a web page, or an editor that lays graphics over footage, using the canvas template and render script kept beside this skill.

- Build a vertical video title for a short form feed when the graphic ships inside the video itself, using a frame driven Remotion composition with name, role, and theme as props.

- Deliver WebM with alpha for OBS and browsers, ProRes 4444 for Premiere Pro, DaVinci Resolve, and Final Cut, and an MP4 on a green ground only for a tool without alpha support.

- Deliver a vertical MP4 as the default for the short form build, with 1080 by 1920 as the default frame size.

## Design the card

- Keep the card to two lines, a dominant name line and a secondary role line, and never invent a title, surname, or second line the user did not give.

- Make the name at least 1.6 times the role size, set the role at about 45 to 60 percent of the name size, and put the role in a lighter weight and one brand accent color used consistently.

- Put text on its own backing, such as a panel, bar, band, or heavy shadow, so it reads over bright and dark footage alike.

- Keep every pixel inside title safe, at least 5 percent in from each edge, and keep the middle of the frame empty for the speaker.

- Lift the band above the bottom UI zone on a 9:16 frame, clear of platform captions and buttons, and anchor the card to the left so names of different lengths stay pinned.

- Shrink a long name to fit its box instead of letting it overflow, check the longest entry in the roster, and pick a face with lining numerals when the card carries digits.

- Pin font, accent color, bar style, and corner radius in one theme object so every title across a series matches.

## Animate the reveal

- Animate the bar first, then the name, then the role, with each step offset by 3 to 6 frames, so the card arrives as a short cascade rather than a single slam.

- Budget about 12 to 18 frames for the enter, 90 to 150 frames for the readable hold, and 8 to 12 frames for the exit at 30 frames per second, with the exit faster than the enter.

- Hold the card still while it is read, with motion only in the build in and build out, and never hard cut a title on or off.

- Start and end on empty frames for the overlay build, keeping the lead and tail intact, so the clip never pops on or cuts off in the edit.

- Drive every animated value from the current frame, never from wall clock time or a library timer, so renders stay deterministic and any exact frame can be inspected.

## Render for a roster

- Treat name, role, and theme as props, never as hardcoded values, and map one design across the whole roster so a text change needs no re-animation.

- Use the canvas build defaults of 1920 by 1080 at 30 frames per second, about 8 seconds long, lower left, and silent, when the brief gives no other answer, and list the defaults you chose when you deliver.

- Use one Google Fonts link per family with the weights and italics you use, and list every face you draw with, so nothing renders in a fallback font.

- Verify one real roster row with stills before you render the whole roster, so a layout or overflow bug is caught once rather than once per name.

- Hand over the rendered files plus the page or project, so the user can change a name and re-render without rebuilding the design.

## Verify before you ship

- Run the overlay check for fonts, transparency, empty first and last frames, title safe placement, and timing, and fix any failure before you render.

- Render stills for the enter, the dwell, and the exit phases, using a real roster row rather than default props, and inspect the dwell frame hardest.

- Confirm at the dwell frame that the name dominates the role, the brand accent and bar are correct, both lines are fully revealed rather than mid wipe, and the band sits inside the safe area.

- Confirm in the enter and exit stills that the animation actually runs as a partial reveal, not as a hard cut, and that no text shows before or outside the part of its panel that is revealed.

- Encode only after the stills check out, and confirm that WebM and ProRes files really carry an alpha channel by decoding a frame from the hold.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Reuse the runnable Remotion lower third component kept beside the retired skill on disk at `~/workspace/custom-skills/local-tiktok-lower-thirds/references/lower-third-component.md` when the short form build needs its staggered spring enter and per row batch script.

- Reuse the canvas template, render script, and delivery notes kept beside this skill when the overlay build needs a transparent file for OBS, a browser, or an editor.

- Render a short proof clip after the MP4 is done when the user needs to see the motion without opening the full project.
