## 2026.11.05.7 — 2026-11-05
- BIO IS THE SOURCE LINE ONLY (user, 2026-11-05). The on-screen bio is now a single regular line, 'Source: <root>, <date>' — the bold finding line is dropped entirely. It supersedes bio_no_find_prefix_2026_11_05 from earlier the same day (which had only removed the 'FIND —' label). Implemented in templates/clips/template.yaml (bio_source_only_2026_11_05; the format in bio_source_rule_2026_10_26 and the wording in bio_source_regular_2026_11_04 updated to match; 'FIND line' references in pipeline/clip_frames.py renamed). No code change was needed: clip_frames.build_frame draws whatever bio_lines it gets, and a one-element Source list gets BIO_FONT. Geometry follows automatically (1-line bio box is 80px vs 128px, so the watermark rides up with it). First clip built under it: Kimi K3 in C v3 (frames regenerated; captions byte-identical; narration re-derived deterministically, final -14.70 LUFS / TP -1.38 identical to v1/v2). Verified on v3 frames 2/30s: bio holds exactly one regular line, 'Source: kimi-k3-in-c on GitHub, Nov 5, 2026', watermark beneath it at y1204..1236 (shot 2).

## 2026.11.05.6 — 2026-11-05
- BIO DROPS THE 'FIND —' PREFIX (user, 2026-11-05). The on-screen bio's line 1 is now just the finding itself ('<what>'), with no 'FIND —' label prefix; line 2 stays 'Source: <root>, <date>'. Implemented in templates/clips/template.yaml (bio_no_find_prefix_2026_11_05; the format in bio_source_rule_2026_10_26 updated to match, and 'FIND line' references in bio_source_regular_2026_11_04 and pipeline/clip_frames.py renamed to 'finding line'). The Telegram description still says 'FIND:' (template publish rule, unchanged) — only the on-screen bio drops it. First clip built under it: Kimi K3 in C v2 (frames regenerated; captions byte-identical; narration re-derived deterministically, final -14.70 LUFS / TP -1.38 identical to v1). Verified on v2 frames 2/30s: bio reads 'Kimi K3 running on one CPU' (bold) over the regular Source line, no 'FIND' label anywhere on screen.

## 2026.11.05.5 — 2026-11-05
- WATERMARK 80% TRANSPARENT (user, 2026-11-05). @leos.logos goes from 90% transparent to 80% transparent (20% opaque, alpha 51); placement unchanged (x=60, bio bottom + 20px, clamped above the captions). Implemented in pipeline/clip_frames.py and recorded in templates/clips/template.yaml (watermark_beneath_bio_2026_11_05). First clip built under it: OpenAI cyber kernel v5 (frames regenerated; captions byte-identical; audio copied verbatim from v4). Verified: test-frame watermark max grey 51 over black (exactly 20% of 255); v5 frames 2/31/61s eye-verified, watermark present beneath the bio, slightly more visible than v4.

## 2026.11.05.4 — 2026-11-05
- WATERMARK 90% TRANSPARENT (user, 2026-11-05). @leos.logos goes from 70% opaque to 10% opaque (alpha 26); placement unchanged (x=60, bio bottom + 20px, clamped above the captions). Implemented in pipeline/clip_frames.py and recorded in templates/clips/template.yaml (watermark_beneath_bio_2026_11_05). First clip built under it: OpenAI cyber kernel v4 (frames regenerated; captions byte-identical; audio copied verbatim from v3). Verified: test-frame watermark max grey 26 over black (exactly 10% of 255); v4 frames 2/31/61s eye-verified, watermark present but faint beneath the bio.

## 2026.11.05.3 — 2026-11-05
- WATERMARK BENEATH THE BIO (user, 2026-11-05). @leos.logos moves from middle-left (v2026.11.05.2, same day) to directly beneath the bio/source block: x=60, bio bottom + 20px, clamped so its bottom never passes y1495 (keeps the gap to the top-anchored captions at glyph row ~1530); 70% opaque (alpha 179) unchanged. Implemented in pipeline/clip_frames.py (per-shot, from the hug geometry) and recorded in templates/clips/template.yaml (watermark_beneath_bio_2026_11_05, superseding the middle-left rule). First clip built under it: OpenAI cyber kernel v3 (frames regenerated; captions byte-identical; audio copied verbatim from v2). Verified: test frame bio bottom 1358 -> watermark top 1378 (exactly +20px), bottom 1410; v3 frames 2/31/61s eye-verified, watermark at y1222..1255 under the bio (bottom 1202), clearly readable on black.

## 2026.11.05.2 — 2026-11-05
- WATERMARK MIDDLE-LEFT (user, 2026-11-05). @leos.logos moves from top-left (60,80)/(60,190) 50% opaque to middle-left (x=60, text centre y960, ~y937 top), 70% opaque (30% transparent, alpha 179), on every clip frame; it may overlap the mid content. Implemented in pipeline/clip_frames.py (build_frame computes the centred y from the text bbox) and recorded in templates/clips/template.yaml (watermark_middle_left_2026_11_05). Title-top floor y130 is now a layout margin, not watermark clearance. First clip built under it: OpenAI cyber kernel v2 (frames regenerated; captions byte-identical; audio copied verbatim from v1). Verified: test-frame watermark centre y959, blended value matches 70% opacity; v2 frames 2/31/61s eye-verified. Note: on white-background charts the white watermark reads faint — no shadow added unless the user asks.

## 2026.11.05.1 — 2026-11-05
- TTS COMMA DETECTOR WINDOW FIX (traced by the 2026-11-05 7am scout run on the OpenAI cyber clip). ROOT CAUSE: `_has_pause` windowed [b-0.10, b+0.30], so up to 0.10s of a comma word's OWN quiet fricative tail counted as pause — a word ending in a quiet tail ("itself", "first", "real") chained its pre-end quiet with a short real pause to reach 0.15s, and the detector skipped insertion while the real post-word silence was only 0.04-0.12s (9 of 13 commas on the clip's first check; the verdict was phase-sensitive, flipping between b=6.808 and b=6.81). Fix at pipeline level: the window now starts AT the word end, [b, b+0.30] — only silence after the word counts. Fingerprint code 4 -> 5 (cached segments re-synthesize). Regression test added: pipeline/test_tts.py (5 deterministic cases incl. the fricative-tail straddle; the old window returns True on that signal, the new code False — proven by countercheck). End-to-end proof: a fresh Kokoro synth of a clause ending in "itself," carries 0.26s post-comma quiet. The cyber clip itself was fixed clip-locally before delivery (0.22s spliced after all 9 short commas; final clip verified 0.20-0.34s after every comma — independently re-measured). No cron edits needed (code-layer change).
- ALIMITER LESSON (same run): ffmpeg alimiter's `limit` is a LINEAR value (0.0625-1), not dB — `limit=-1dB` mis-parses and auto-level RAISES peaks to 0.0 dBFS. The correct form is `limit=0.891:level=false` (0.891 = -1 dB linear). No pipeline code used the bad form (the 7am worker's ad-hoc first render did); recorded here so it is never re-applied.

## 2026.11.04.1 — 2026-11-04
- SOURCE LINE NOT BOLD (user, 2026-11-04: "Have the Find source text not be bold"). ROOT CAUSE (style, not curation): both clip text paths drew every bio line in DejaVuSans-Bold, so the attribution line competed with the FIND line. Fix at pipeline level: pipeline/clip_frames.py gains BIO_FONT (regular DejaVuSans) and draw_box takes per-line fonts; build_frame renders the bio's "Source:" line regular while the FIND line and title stay bold. Template: bio_source_regular_2026_11_04 added to templates/clips/template.yaml (same per-line rule governs source-video clip overlays). Proven by test frame (FIND line bold, Source line visibly regular, measured 770px vs 867px bold at 34px) and by the Fortran clip v2 rebuild (same video/captions/audio, only the source line's weight changed). No cron edits needed (scout runs read the clips template in full; narrated builds use clip_frames.py directly).

## 2026.11.03.2 — 2026-11-03
- COMMA-PAUSE DETECTOR CORRECTION (same user complaint as 2026.11.03.1, found in v3 QA before delivery): the first detector (thresh 0.015, window [b-0.20, b+0.10], run >=0.12s) false-positived — its wide window chained the previous word gap + a fricative tail (0.011-0.015) into a fake pause, so it skipped insertion for commas whose real pause was only ~0.08s (PLE v3 "layouts,": 0.06s beat, still rushed; "model," 0.14s, "PLE," 0.16s adequate). Fix: thresh 0.005 (true pause floors are 0.000-0.005; audible tails are 0.01+), window [b-0.10, b+0.30] (a full word away from the previous gap), run >=0.15s. A >=0.15s span below -46dB IS a pause by definition, so skipping then is correct; anything shorter gets the inserted 0.22s. Proven by deterministic detector unit tests (layouts-like tail+short-pause -> insert; PLE-like 0.16s pause -> skip; continuous speech -> insert; inserted 0.22s zeros -> skip). Cache: fingerprint code 3 -> 4. PLE v3 was built with the old detector and superseded before delivery (preserved as clip_v3.mp4); v4 is the delivered cut.

## 2026.11.03.1 — 2026-11-03
- FIRST-WORD ONSET + COMMA PAUSES (user, 2026-11-03, on the PLE clip: "The voice sometimes skips the first word in a sentence. And doesn't pause after comma sometimes"). ROOT CAUSES, both measured, both in pipeline/tts.py: (1) Kokoro renders a segment's FIRST token with a soft onset — the first ~40ms of a segment-initial word is digital silence, so a short first word ("The" 75ms, "It's" 125ms) is inaudible on a phone speaker and sounds skipped, while mid-sentence words attack cleanly. Fix: synthesize with a disposable discourse marker ("Well," — "Okay,"/"Hmm," fallbacks if the sentence itself starts with one) absorbing the soft onset, then trim it (5ms fade-in at the cut, 0.12s lead silence restored); the real first word then starts at full energy (verified: "The" attacks in its first 20ms window, RMS 0.0439 vs 0.0000 before, no warm-up leak in words). If the warm-up word does not come out first, the segment re-synthesizes plain — warm-up audio is never shipped. (2) Kokoro pauses after SOME commas (first list item, clause commas) but rushes past others — measured on the PLE clip: "layouts,", "switchboards,", "electrical,", "civil,", "model," all with no >=0.12s silence, while "frames,", "mechanical,", "tasks,", "publicly," carry 0.13-0.32s pauses. Fix: after alignment, splice 0.22s of silence (zero-crossing splice, 2ms edge fades) after every comma that lacks a >=0.12s low-energy run, shifting later word times; existing pauses untouched. Both fixes live in synth_segment so every future narration (clips + daily, when it resumes) gets them. Cache: fingerprint code 2 -> 3, so all cached segments re-synthesize with the fixes. Proven by unit test (both cases above) and by the PLE v3 rebuild (same script as v2, delivery only). No cron edits needed (code-layer change; scout runs use tts.py directly).

## 2026.11.01.1 — 2026-11-01
- DYNAMIC HUG (user, 2026-11-01, on the HackerTube clip: "The top and bottom text should dynamically hug the mid content to kill any unnecessary deadspace throughout the video"). ROOT CAUSE (layout, not curation): narrated clips used FIXED text zones (title y135..345, bio y1370..1500) while content was centred in y375..1325, so short content left 170-280px black gaps between text and content on every shot (HackerTube v1: ~190/172px on shot 1, ~271/254px on shot 2). Fix at pipeline level: new pipeline/clip_frames.py — content stays centred in the middle zone on clean black (max 960 wide); title box sits directly above the content and bio box directly below it, per shot (20px box gaps; boxes sized to text, so white-text-to-content gaps are 40px title / 36px bio, the no-face layout's existing 36-40px standard); hard limits title top >= y130 (watermark clearance) and bio bottom <= y1500 (caption clearance), with content max height capped (min(950, 2*(630 - bio_h))) so the bio can never overflow. Proven by HackerTube v2 (same script, captions byte-identical to v1, audio copied verbatim from v1; only text positions moved): shot 1 title y310..470 / bio y1230..1358 around content y490..1210; shot 2 title y391..551 / bio y1148..1276 around content y571..1128. Template: dynamic_hug_2026_11_01 added to templates/clips/template.yaml; it supersedes the fixed narrated zones and the y1400 stack-bottom check for narrated clips (hugged short content yields balanced margins, not a top-heavy frame). No cron edits needed (scout runs read the clips template in full). Daily digest layout untouched — its zones are a separate system.

## 2026.10.28.2 — 2026-10-28
- ENUMERATE THE ROOT PAGE (user, 2026-10-28, on the Gemini 4 Carbon clip: "Make the comparison picture the first shot ... you should've found it" + share link to kimmonismus's blog-source post). ROOT CAUSE (hunt completeness, not scout listing): the v1 clip's hunt stopped at the first chart found on the Google blog (ExploitGym) and never enumerated the page's other visuals — missing the blog's main evals comparison table ("Gemini 4 Carbon benchmark table", 4164x3504 original PNG), which is the story's strongest shot. Fix in the clips template: how_to_get_source_footage now requires listing EVERY visual on a root-source article/blog page before choosing shots, with the comparison table named as often the strongest shot. The fix-up cut v2 of the Gemini clip (comparison table as shot 1, padding fix below) is built under this rule. Same turn, second user correction: "your pic is too cropped on top 00:01 ... remember to leave a little padding around text in image crop" — verified at the v1 00:01 frame: the blog-header vision-crop's top bound sat ON the headline's first row (headline touches the card's top edge, no whitespace above it), the same PYMNTS-class margin violation as v2026.10.27.2. The v2 fix-up re-crops the header from a fresh screenshot with clear whitespace above the headline and applies the margin rule to every text-bearing crop, eye-verified at full resolution. No pipeline code changed in this version (instruction-only, like .3); no cron edits needed (scout runs read the clips template in full).

## 2026.10.28.1 — 2026-10-28
- THREADS FOOTAGE HUNT, SCRIPTED (user, 2026-10-28: "Find out why you keep failing to find good footage. You missed this important one" + share link to kimmonismus's Gemini 4 Carbon post). ROOT CAUSE, two parts: (1) THE SCOUT NEVER SAW THE POST — the 11am 2026-10-28 run paged kimmonismus and saved the Mario + MotionBricks posts via profile, but kimmonismus's 10:49 Gemini Carbon post is absent from scout/state.json seen_threads_urls (108 entries): the Threads profile listing at run time did not contain a post 10-30 minutes old, and the "stop at first already-saved" rule means a run never revisits. (2) EVEN A SAVED POST YIELDS NO FOOTAGE — the Threads connector returns text-level data only, never media files or URLs, so every hunt that stopped at the connector fell back to stills by default; the working routes (browser embed-page download for video, microlink screenshot + crop for images) were manual, slow, and unmandated, so workers skipped them. FIX: new pipeline/threads_media.py — given a post URL, share URL, or code, it extracts the post's own image files directly (curl of the /media viewer page, scontent t51.82787-15 URLs, download). Verified 2026-10-28 on three cases: the missed Gemini Carbon post (direct URL and share URL both resolve to the same 209,382-byte benchmark-chart image, byte-identical to the manual extraction) and a video post (Mario demo: no downloadable video in the page, poster only, needs_browser_embed_route=true — reported honestly, video still needs the browser embed route). Two implementation traps, both verified and documented in the script: page fetches MUST go through curl, not Python urllib (urllib gets a 259KB reduced page with zero media URLs; curl gets 623KB with them), and the UA MUST stay a bare "Mozilla/5.0" (a full desktop Chrome UA gets a 261KB shell with no media URLs). TEMPLATE: clips template how_to_get_source_footage now carries a MANDATORY THREADS HUNT (run threads_media.py on the surfacing post before any stills fallback; log attempt + result in meta.json; a stills fallback with no logged attempt FAILS the hunt) and a SAME-STORY SWEEP (hunt the surfacing account's other same-story posts from the last 24h — the missed post's benchmark chart was the best visual while the official announcement post carried none; use the underlying source media itself, never a post-card screenshot). SCOUT README: new THREADS PROFILE LISTING LAG section — re-page each Threads profile at the END of every run (after keyword passes) and save anything new; report suspected lag when an account's newest seen post predates the run window. No cron.body edits needed: scout runs read README + clips template in full first, so both rules govern the next run (4pm 2026-10-28). The daily digest cron is untouched — its footage comes from article cards, not Threads posts. The missed post itself was handed to the in-flight Gemini Carbon clip build with its chart image (scout/threads_footage/DfDAfjVDqYi.jpg); whether it lands in that clip is confirmed by that build's report, not assumed here.

## 2026.10.27.4 — 2026-10-27
- DEADSPACE FIX (user, 2026-10-27, on the 21:14 daily video at 00:17): the Opera hook hero — a 1600x800 wide marketing banner — rendered as a short centred band with a large blurred stretch between the content and the pinned captions, which reads as dead space; the user reports this class happens "sometimes" with short mid content. MECHANISM (render.py frame_layout, blur-pad path): wide pins are fit inside the 1490px visual zone and vertically centred, so the Opera hero filled only 540px of the zone with ~490px of blurred background below it. Fix at pin-spec level, not render geometry — centring/bottom-anchoring only relocates the gap, and document cards cannot be cover-cropped without slicing text: (1) hero pins must now be portrait-leaning, aspect width/height ≤ 1.5, enforced by a new QA gate — pin_edge_check.check_hero_aspect, wired into qa.py after the edge-slice check, FAILING LOUDLY naming the offender pin (tested: flags the quarantined 1600x800 Opera banner, passes the new hero set); (2) the Opera hero was re-cropped to its informative region — the WebAI browser panel (630x800, aspect 0.79, ~92% of the visual zone, ~60px bottom gap) — applied to both the hook hero and the byte-identical deep-dive file, old wide files quarantined aside with every extension variant. The daily cron now carries the HERO PORTRAIT RULE (portrait-leaning heroes; re-crop to the informative region or extend an article crop downward to portrait; never slice text sides to force portrait). RESIDUALS, reported not hidden: the TechCrunch Genie card (aspect 1.63) cannot be portrait-reframed — its headline/dek span the full width, and a fresh TechCrunch capture now returns an adblock wall (discarded, never pinned); the NY Post Genie card (2.19, the worst gap) cannot be reframed — its source URL is not recoverable from script.json and two web searches did not surface it, and swapping in another outlet's card would misrepresent the shot; the Mayer couch photo (1.81) spans the full width, so a portrait crop would cut its subject. Photos and deep-dive cards are exempt from the hard gate for exactly these reasons; the cron spec pushes portrait-leaning crops for them instead.
- FOOTAGE GLOBALIZATION (user, 2026-10-27: footage sourcing upgrades are global to all pipelines, not clips-only). The clips template's footage_priority_2026_10_27 is now adapted for narrated formats — moving source footage first, playing UNDER the narration with terminal captions continuing over it; other useful footage as cutaways; vision-cropped ROOT-source stills only when no video exists; never a third-party surfacing post as a visual; a still is never passed off as footage — and lives in: (1) the daily cron muse-video-pipeline-daily (FOOTAGE PRIORITY FOR NARRATED FORMATS, after SHOT GRAMMAR); (2) templates/rumors-digest/template.yaml visual_rules. The source-audio-backbone clause stays clips-only — it would clash with digest narration — and the adapted text says so explicitly. The rumors cron defers to the rumors template and carries no visual rules of its own, so no rumors cron edit was needed. The montage template was verified video-first by design (pics first, then mainly video, reporter audio, v10 centerpiece) and left untouched. Applies to FUTURE runs only — today's re-render carries only the deadspace fix (script, narration, timings fixed; re-sourcing footage now would desync the video). In passing: the rumors template did not strictly parse as YAML (unquoted dedupe value containing ': '); the value is now quoted, text unchanged, and the file parses clean.

## 2026.10.27.3 — 2026-10-27
- DIGEST TAIL-SLOT RULE (user, 2026-10-27, on the 2026-10-27 daily video): the 5th story is chosen by INDUSTRY WEIGHT, not broad/human-interest appeal. Rank the top 4 by interest as usual; for the 5th slot, if the strongest remaining candidate is a human-interest or celebrity story with no industry consequence and an industry-moving story was dropped, take the strongest dropped industry-moving story instead — even if the human-interest story is more shareable. Example: on 2026-10-27, X locking AI reviewers' accounts over Kimi K3.1 (platform policy with field-wide consequences) takes the tail slot over the Mayer/Dazzle human-interest story. No code change — story selection is the run agent's judgment under cron instructions, so this version records the instruction change; the daily cron's step 2 is synced.

## 2026.10.27.2 — 2026-10-27
- EDGE-SLICED HEADLINE DETECTOR (user, 2026-10-27, on the 20:48 daily video at 00:11): the PYMNTS Apple card's headline shipped with its first line's ascenders sliced off at the pin's top edge — and the full-image audit found the SAME sliced crop in a second shot (the Apple deep-dive at ~01:31), so one bad crop shipped twice. ROOT CAUSE (pipeline, not curation): (1) the vision-crop's top bound was set at the headline's first text row instead of in the whitespace above it, and the same bad crop was saved twice (hook hero + deep-dive pin, same 1000x870, same top-edge signature); (2) QA had wall scans, duplicate guards, and black-frame guards but NOTHING that inspects pin edges, so a clean, relevant card with a tight crop passed every automated check; (3) frame review missed it through two cuts because a few-pixel ascender clip is invisible at contact-sheet thumbnail scale, and "unchanged" pins (Apple/Opera) were never re-examined at full resolution after the 18:40 cut — the user caught it at full-screen playback. Fix: new pipeline/pin_edge_check.py — flags an edge iff its 2px strip is paper-white (median >= 230, which skips photos/dark cards) AND carries >= 5 short near-black runs (2..60px, one per clipped letter stem; bezels give long runs, foliage gives non-white edges) — calibrated on today's video: defective crops show 16 short runs on a median-249 edge, the brightest clean photo edge is median 220, the most short runs on any qualifying clean edge is 1. Wired into qa.py as a blocking check that FAILS LOUDLY naming offender pins. Both defective Apple pins re-cropped from a fresh PYMNTS microlink screenshot with clear whitespace above the headline (hook pin already fixed 20:59, verified clean; deep-dive pin re-cropped here, verified clean + detector-passing, both extensions replaced, defective variants quarantined aside). The daily cron's VISION-CROP PINS section is synced: crops must include clear whitespace beyond the outermost text line, and a sliced ascender/descender is a failed pin caught by the detector.

## 2026.10.27.1 — 2026-10-27
- HOOK HEROES ARE NEWS MATERIAL, NEVER CEO FACES (user, 2026-10-27, on the 18:40 daily video): hooks 1, 2 and 5 shipped full-frame CEO faces (Hassabis, Nadella, Mayer) instead of the news itself, while hooks 3 and 4 correctly showed article screenshots (Apple M6, Opera). ROOT CAUSE (code, not curation): visuals.py's hook-hero chain fell back to story_people person photos (step 2) whenever no hook_hero pin existed — and the 18:00 run had pinned heroes for only 2 of 5 stories. Fix in visuals.py: the person-photo fallback is deleted; the chain is now (1) hook_hero pin, (2) story's first non-document, non-person deep-dive photo, (3) story's first non-person deep-dive shot. If a story has no non-person visual at all, the hook falls back to its first deep-dive shot with a LOUD warning (never silent, never blank) so frame review flags it. The daily cron's HOOK HEROES section is synced: a distinct news-material hero pin is required for every story, and a face as a hook hero is a FAILED frame. Today's video is re-rendered with news-material heroes pinned for Genie 4, Microsoft buyouts, and Mayer/Dazzle.

## 2026.10.26.1 — 2026-10-26
- PINNED CAPTIONS + CENTRED MID CONTENT (user, 2026-10-26, on the 18:34 daily video): (1) captions were still drifting — measured first-glyph row y1470..1734 across the video. ROOT CAUSE (same as the clips bug, now in the daily code): captions.py bottom-anchored every phrase with a per-phrase MarginV ladder assuming a libass line height of 88px (real ~65-70px), plus the trailing line-break bug that rendered a cursor-only line at line changes. Fix in captions.py: top-anchored captions (ASS alignment 7, one fixed style MarginV 1513, events inherit it), line breaks deferred to the next line's first letter — first glyph row now ~1530 on every frame, same pinned behaviour as the find-template clips. (2) Mid content sat too low (sharp story visuals bottom-anchored to y1490, top half blur). Fix in render.py: story foregrounds vertically CENTRED in the y0..1490 visual zone, in both frame_layout (photos) and the final blur-pad overlay (clips); selfplug keeps its bottom-anchor so the brand montage still ends at y1490. Supersedes the 2026-10-25 bottom-anchor for story visuals.

## 2026.10.25.2 — 2026-10-25
- VISUAL-ZONE BOTTOM-ANCHOR (user, 2026-10-25, second half of the deadspace fix): v2026.10.25.1 moved short article cards down only ~45px (centred in the 1490 zone) — frame-check of that re-render showed the Kimi card still ending y1086 and the Meta card y1039, i.e. still ~550px of sharp-content gap to the caption glyphs, with only brighter blurred fill in between. The user's standing instruction for this class of shot is to move content LOWER, more middle-centre (same as the clips zones). Fix in render.py: the fit-path foreground is now BOTTOM-ANCHORED to the visual zone instead of centred — frame_layout pastes fg at y = box_h - fg.height, and the video blur-pad overlay uses y = 1490 - h. A 690px card now sits at y800..1490, its bottom edge right on the caption fade, so the space above the captions is only the fade transition. Tall images are unaffected (fg height ~= box height). Verified on a synthetic 1080x690 article card: text rows 860..1440. Known tradeoff, accepted: an emphasis pill placed at the y1400 third would now overlay the bottom of a short card; today's script carries no emphasis pills, and the thirds logic already avoids faces.

## 2026.10.25.1 — 2026-10-25
- VISUAL-ZONE DEADSPACE FIX (user, 2026-10-25: "mid content was supposed to be more in middle of screen... too much deadspace above captions"): measured on the 2026-10-25 daily digest — worst frames were the Kimi deep-dive at 120s (sharp card ended y1037, first caption glyph y1645, a 608px gap) and the Meta deep-dive at 155s (card ended y994, glyph y1589, 595px gap), confirmed by eye on both frames: short article cards sat high with a dark void below them before the captions. ROOT CAUSE (code, not template): the 2026-10-25 unified-zones work only edited the template YAML files — the live daily code in render.py still hardcoded the old visual zone. frame_layout centred every short card in a y 0..1400 box (a 690px card landed at y355..1045), darkened document blur-fill to 0.45 (so the fill below the card read as black, not content), and the caption gradient blacked everything from y1380 down. Fix in render.py: visual zone 1400 -> 1490 in both the photo blur-pad path (frame_layout) and the video-clip blur-pad path (scale + overlay centring), document blur-fill brightness 0.45 -> 0.70 (same as photos), caption gradient fade moved 1380 -> 1430 (fade completes y1500, caption glyphs from ~1521 sit on solid black). Short cards now centre at the visual-zone middle (y~745) with bright blurred fill running down to the fade, so the black void above the captions shrinks to the fade transition itself. Verified on a synthetic 1080x690 article card: sharp text rows 460..1040, centre 750, fill visible below the card. Self-plug canvas (1080x1400) and emphasis-pills thirds unchanged — the self-plug clip now centres in the 1490 zone and stays fully visible above the caption glyphs. Templates already carried the 1490 rule; this wires the live code to it.

## 2026.10.24.2 — 2026-10-24
- LOGO VISIBILITY (user, 2026-10-24: "JP Morgan Chase co logo was dark and hard to see with black background"): root cause — selfplug.py pasted file logos straight onto the pure-black right column with no brightening (unlike render.py's logo overlays, which auto-invert dark marks), and the JPMorgan file is 100% dark pixels (mean luminance 53/255). Fix in selfplug.py _logo_image (file logos only, glyphs untouched): key out a solid white logo background (>50% near-white, e.g. AWS) so no white box renders, then if the remaining mark's mean opaque-pixel luminance is <110, render it as a white variant (RGB=white, alpha kept). Verified 2026-10-24: whitening fired for JPMorgan and AWS only, DeepSeek (115) and Google (130) left as supplied; full split shot now reads JPMorgan in white and AWS in white with no white box. Same dark-logo problem exists in other logo files (ASML 0, SoftBank 15, CoreWeave 25), so the rule is general, not a one-logo patch.

## 2026.10.24.1 — 2026-10-24
- ADBLOCK-MODAL SCAN (user, 2026-10-24: "At 00:44 in the latest top ai news daily digest video, the screenshot shows an ad warning pop up"): the 2026-10-24 daily video shipped a New York Post adblock modal at 43.2-49.2s (story 1/5, "Free browser versions" shot) — a large centered white box with red "NEW YORK POST" header and "ALLOW ADS" button over the dense article. ROOT CAUSE: the existing wall scans cover only two wall types — _is_adblock_wall early-returns False on dense pages (this shot: 55.7% dark-pixel density) and _is_paywall_modal needs >45% center saturation (this white modal fails it) — so all three scans returned False and the screenshot shipped. New _is_adblock_modal() in visuals.py, wired into both pre-crop and post-crop screenshot checks: solid vivid-red component >5% of pixels PLUS a large solid white connected component (>50% width, >30% height, >60% fill, >25% of image). Verified 2026-10-24: fires on both NY Post adblock modals in the cache, fires on no other cached screenshot and no verified pin, and does not fire on the replacement pin. The bad shot itself is replaced by a verified pin: a vision-cropped 80.lv headline card ("Halo: Combat Evolved Can Now Be Played in a Browser", byline + headline + dek complete, no sponsored banner, no modal) pinned as 2cb76584d0ff.jpg/.png for that shot's broll slug.

## 2026.10.23.10 — 2026-10-23
- SPLIT ROW FIX (frame review of 23.9): split rows now crop ONLY each character's own panel band (source height / 5, in story order), cropped to the left-panel aspect and centred on the face horizontally. The 23.9 square face crops pulled in the neighbouring panel's torso, which showed as a duplicate strip at row boundaries during the slide (seen at ~26s in the 23.9 final). Panel-band rows eliminate that strip — slide frames now show each pair cleanly, full split shot unchanged.

## 2026.10.23.9 — 2026-10-23
- SPLIT MONTAGE + PIXAR PORTRAIT REBUILD (user, 2026-10-23: "Pixar image is supposed to have a relevant background and the characters shouldn't have the same attire. The shot should be split, left side characters right side company or icon logos. Montage simply slides from top to bottom then shows full shot"): (1) intro_people.png regenerated as a true Pixar group, 9:16, top-to-bottom story order, each character in a DIFFERENT outfit (Liang green quilted jacket, Treasury woman navy blazer, Musk black leather jacket, Altman light blue sweater, Melanie coral patterned dress), each with a RELEVANT background panel (DeepSeek data centre + whale, Treasury building + scales, X social feed, OpenAI lab + robots, Canva design studio) — supersedes the pure-black, all-dark-suits portrait (preserved as intro_people_20261023_black_suits.png). (2) selfplug.py rebuilt as a SPLIT montage: left side characters, right side company/icon logos (DeepSeek, scales glyph for Treasury, X, OpenAI, Canva — glyphs are drawn icons, not missing-logo fallbacks), one row per story in story order. The camera simply slides top-to-bottom over the tall split composite (linear, 4.19s), then holds the full split shot (all 5 pairs at once, 1.5s). Character crops are face-centred windows so faces are never cut off at row edges in the full shot; the final group branch now shows the full split shot, not the old portrait group.

## 2026.10.23.8 — 2026-10-23
- LOGO-PAIR MONTAGE (user, 2026-10-23: "have the logos pertaining to the characters right next to them. The montage could be a sliding focus on each pair then end with full view"): the self-plug montage is no longer solo close-ups. Each segment now shows a CHARACTER + LOGO pair, side by side, on black: the character crop on the left, its logo on the right, with a sliding focus that pans from the character to the logo over the segment (easing out, holding on the logo), then cuts to the next pair, ending with the full portrait group view. Logos are mapped from script.json story_ids order -> story_icons (never guessed; glyphs and missing logo files fall back to a solo close-up). Portrait face-order fix: portrait sources sort faces top-to-bottom (story order), not left-to-right, which on the Oct 22 portrait gave Dario, Zuckerberg, Altman, PHP, Jensen and would have paired every character with the wrong logo. Verified in a test clip: Jensen + NVIDIA logo side by side with the slide, and a direct Meta pair frame (character left, Meta logo right). The daily 18:00 run was already in flight when this landed, so the full-video render with this montage ships after that run (or in that run's self-plug stage, if it runs after this change).

## 2026.10.23.7 — 2026-10-23
- PORTRAIT PIXAR ORIGINAL (user, 2026-10-23: "update the original Pixar image so it fits nicely in portrait format, generate it that way"): intro_people.png is now a true 9:16 portrait (1152x2048), generated from the old landscape group — same five characters in story order top-to-bottom (Zuckerberg, Dario with AI network, Jensen, PHP engineer with laptop, Altman), pure black background, all faces fully visible, no text. The old landscape pin is preserved as intro_people_landscape_20261022.png. Code: selfplug.py _fit_group now uses a portrait source DIRECTLY (fit inside 1080x1400 on a blurred background from itself, no tile recomposition — the tile layout is kept only as a legacy landscape fallback); render.py's intro guard now requires portrait (aspect <= 0.85, fitted by height) instead of landscape (>= 1.25), which would have failed the correct new pin.
- MUSIC OFF (user, 2026-10-23, temporary): the bed track is preserved as pipeline/assets/music/ai_digest_bed.mp3.disabled, so render.py finds no *.mp3 track and mixes narration only (loudnorm -14 LUFS, no bed). Re-enable by renaming the file back to .mp3 — do not add a copyrighted song.

## 2026.10.23.6 — 2026-10-23
- SMALLER, SEMI-TRANSPARENT, CLEAN-BLUR PILLS (user, 2026-10-23): the unified pill is now half as small (138x66, was 276x132), background 50% transparent (alpha 128, was 255), text still opaque white. BLUR ROOT CAUSE (user: "why isn't it a clean blur? There's hard edges a bit still"): the old pill blurred a mask that filled the whole PNG, so its straight edges sat exactly on the image boundary and alpha jumped 0 -> 255 in 1px at the sides (verified in the final frame: x743 light video, x744 solid dark) — only the rounded corners looked soft. The new PNG carries a 24px transparent margin around the rect and the mask is blurred (radius 14) into that margin, so alpha fades 128 -> 0 over ~30px and the composited edge is soft all the way round. The pill is centred on the old pill centre (W-198, 212), so the number stays in the same spot, just smaller; pill rect is now W-267..W-129 x 179..245, and the QA sidecar now records that actual rect (it passes: right edge 951 < 960, top 179 > 140).

## 2026.10.23.5 — 2026-10-23
- UNIFIED NUMBER PILLS (user, 2026-10-23: "Have the number pills during hooks and stories look the same: rounded rectangle dark opaque blur. And in this format x/5"): hooks and story deep-dives now carry the SAME pill — one PNG (`number_badge`), same position (W-336:146), format "n/5". Previously hooks got a separate ASS text pill (#n, tight black box) while stories got a PNG badge (#n, rounded dark pill) — different look, different text. Changes: `number_badge` now draws "n/total" (total = len(story_ids)) in a 276x132 rounded rectangle, dark opaque (24,24,24) with a Gaussian-blurred (feathered) edge; hooks get the badge in the segment stage (seg_kind hook + story_id, story-less self-plug gets none) with the same fade-in-once behaviour; the ASS HookNum pill is retired (no double pill); badge PNGs are always regenerated so no stale #n file survives. Position and QA safe-area sidecar unchanged.

## 2026.10.23.4 — 2026-10-23
- SELF-PLUG COVER-FILL FIX (frame-review find, 2026-10-23): the 23.3 video's Pixar group bottom row was hidden under the captions. Cause: the new 1080x1400 self-plug canvas has cover loss 0.27, so `render.py` cover-filled it to 1080x1920, stretching the visual zone to full height and pushing the bottom row into the caption area. `render.py` now explicitly excludes `selfplug_` clips from cover-fill — they always take the blur-pad path, sitting in y 0..1400 above the captions, fully visible. No other shots change.

## 2026.10.23.3 — 2026-10-23
- HOOK HEROES = SOURCE FOOTAGE / CREDIBLE-SOURCE SCREENSHOT (user clarification, 2026-10-23: "showing the most relevant footage… a showcase video from the source or pic from them, or cropped screenshot of the most credible source"): person headshots are NOT the hero. Now: distinct `hook_hero_<story_id>.jpg` pins for all 5 stories, each a 9:16 blur-padded portrait of the story's own source material, eye-verified — Meta: USA Today verdict article (Meta logo photo + headline); Duet: Anthropic's official claude.com product page (Duet app icon + "Get back to what needs you" + proactive-agent description); selloff: Reuters selloff article (Nasdaq ticker-board photo + headline); PHP: The Register article (headline + "32 unavailable" dek — no showcase photo exists for a security flaw); GPT-6: Google Cloud's official blog (headline + "OpenAI models for Google Cloud customers" hero image). Heroes previewing their deep-dive article is now intentional, per the user's definition, not a duplicate error.
- FACE-AWARE PORTRAIT-FILL (user review fix, 2026-10-23): the 23.1/23.2 video was mostly fit-with-blurred-background because no source qualified for cover-fill (cover loss 0.44–0.72). `render.py frame_layout` now face-crops PERSON photos to 9:16 centred on the YuNet-detected face (face box checked against the crop width, so the face is never sliced) even when centre-crop loss exceeds 30% — person deep-dives now fill the frame too. Non-person shots keep the ≤30% rule, then blurred background; document shots still never cover-crop.
- PORTRAIT SELF-PLUG GROUP (user, 2026-10-23: "the Pixar image is still fitted for landscape"): the old group was the 2480x992 landscape portrait pasted full-width into a portrait frame — a thin strip with blurred space above and below. `selfplug.py` now recomposes the group FOR portrait: the clip canvas is the full 1080x1400 visual zone, with one large character on top and a 2x2 grid of the other four below (560 + 10 + 410 + 10 + 410 = 1400), each tile a face-centred crop capped at one character's share so a neighbour's face never leaks in (a little neighbouring hair at a tile edge is unavoidable in a shoulder-to-shoulder group photo). The background between tiles is relevant, not black: the portrait itself, blurred and darkened, showing through the 10px gaps.
- BEAT-SYNCED MUSIC BED SHIPS (user review fix): `pipeline/assets/music/ai_digest_bed.mp3` is now configured — an original, royalty-free instrumental loop (100 BPM, C–Am–F–G pad, bass, kick, hats, soft pentatonic melody, synthesised in-house, no copyrighted audio). `beats.py` detects 99.4 BPM / 107 beats on it, and `render.py` builds the beat-aligned whole-beat loop bed (volume 0.12 under the narration, loudnorm −14 LUFS) when a track exists. The final video now actually carries a beat-synced bed, not just a test video.

# Pipeline changelog

## 2026.10.23.2 — 2026-10-23

- CLIP DEDUPE (frame-review find, 2026-10-23): the duplicate guard in `visuals.py` only hashed still images, never clips — so two different Pixabay queries ("person scrolling Facebook" for Meta, "person reading email" for Duet) returned the SAME video file under two cache names and both shots shipped, in the Oct 22 video and again in the 2026.10.23.1 re-render. The guard now byte-hashes `.mp4` shots too; a byte-identical clip is replaced with a fresh screenshot of its own story's source (as a document photo, never cover-cropped). Unit-tested with the two real clip files: the second is now replaced. This fix lands in code now and ships in tonight's 18:00 run; the 2026.10.23.1 video already sent to Telegram still contains the phone-clip repeat, and is offered for a corrected re-render on the user's call (see vm_runs.log).
- CLIP DEDUPE FIXES (2026-10-23, found in the first 23.2 render attempt, 12:24 PDT — QA blocked, no publish): (1) dedupe ran BEFORE hook heroes, so all 6 hook/selfplug placeholders looked like duplicates and the selfplug shot got flagged duplicate-needs-review, which QA treats as a black frame — dedupe now skips non-story shots entirely; (2) the replacement-story mapping counted script shots in order, but hook segments carry nshots=0 while visuals carries 6 hook shots first, so a Duet duplicate was offered a PHP article screenshot — mapping is now by segment (k-th visual in a segment = k-th shot of that segment); (3) if every source screenshot fails (Reuters 401/wall for Duet), a duplicate clip now falls back to the 2nd Pixabay hit for its own broll query, hash-checked against the duplicate, instead of flagging black. All three unit-tested (hooks untouched, Duet duplicate gets a Duet screenshot).

## 2026.10.23.1 — 2026-10-23

- INTRO CUT (user): the video now starts with the headline hooks — the cold-open "Breaking, {day} {date}" segment is gone from the script structure. `render.py` and `captions.py` only treat a segment as an intro when it is a story-less hook whose text actually starts with "Breaking" (legacy scripts), so the new first story hook is never mistaken for an intro and never loses its captions. The self-plug segment now opens "This is a top five AI story digest." with the rest of its script unchanged ("The digest starts now, follow to stay ahead, the extended version and quick cuts are at the link in bio.").
- PORTRAIT-FILL + BLUR BACKGROUND (user): photos and clips that are close enough to 9:16 that a centre cover-crop loses <=30% now cover-fill the full 1080x1920 frame (no black pillars/bars). Everything else gets a blurred background made from its own colours (scaled cover, blurred, darkened) with the sharp image/clip fit inside the visual zone (y 0..1400) on top. Document shots (articles, tables, posts) never cover-crop — that would slice headline text — they always take the fit + blurred-background path, darkened harder so text still pops.
- CAPTION AREA (user): terminal captions stay, but their area now has a pure black background whose top edge is a 70px smoothstep fade (y 1380..1450, composited in Pass 2 under the ASS captions), never a solid line. This is what makes full-bleed shots safe: a shot can no longer bleed under the captions. Implementation note (2026-10-23, mid-render): the gradient was first built as a separate pre-pass encode, which was still running at 30+ min (file 19MB, final encode still to come) when a service restart killed the run — the pre-pass was deleted and the gradient moved INTO the Pass 2 filter_complex (overlay -> tpad -> ASS -> watermark -> emphasis, one encode), which smoke-tested clean on a 6s clip before the full re-render.
- HOOK HEROES REPLACE HOOK PAIRS (user): headline hooks no longer show person+logo pairs — PAIR CONSISTENCY is retired for hooks. Each hook now shows its story's most important/captivating/relevant image or video, full-bleed: priority is a distinct pinned `hook_hero_<story_id>` visual (worker pins one per story from now on, not used in the deep dive), then the story's central person photo, then its first non-document deep-dive photo, then its first deep-dive shot. Heroes in the last two cases preview the deep-dive opener (a teaser, the same subject-preview the old pairs did) — only a distinct hook_hero pin avoids any repeat. Landscape keeps the old pair path (parked branch, untouched).
- PIXAR PORTRAIT IN PORTRAIT (user): the self-plug montage's group shot now fits the portrait layout (full width, centred in the 1080x1220 clip, which renders above the caption fade) and always gets a relevant background — the portrait itself, blurred and darkened, behind the sharp group — instead of black padding bars. Close-ups were already full-bleed and are unchanged.
- BEAT SYNC (user, librosa + ffmpeg): new `pipeline/beats.py`. librosa `beat_track` (frames converted to seconds via `frames_to_time`) detects a song's beats; `beat_aligned_bed` builds a music bed that starts on the first beat and loops a whole number of beats, so a loop can never cut mid-beat — `render.py` uses it whenever a music track exists, falling back to the raw loop if detection fails. Beats govern the music bed ONLY: shot cuts stay locked to speech (the 2026-10-08 speech-aligned-cut rule). Tested with a generated 120 BPM sample song (no copyrighted audio): librosa read 117.5 BPM, 31 beats, and a 4-clip ffmpeg montage cut exactly on beats [0.534, 2.531, 4.528, 6.525, 8.522]s with 0.0s duration error (`pipeline/output/beatsync_test.mp4`). No music track is currently configured (`pipeline/assets/music/` is empty), so the Oct 22 re-render ships with no bed — the beat path is code + test, not a fake bed.

## 2026.10.20.6 — 2026-10-20

- STALE ANALYTICS MAP (caught in frame-review of the first 18:00 run): `render.py` carried a hardcoded `_analytics_map` keyed to the Oct 20 morning script's shot indices (9 = SpaceX giveaway math, 13 = hacker breach numbers, 21 = Nscale $90B bars, 24 = AEGIS thresholds). The evening run's new script reuses the same shot indices for different stories, so render overwrote four planned shots with yesterday's graphics — SpaceX math over the OpenAI/SofBank shot, hacker numbers over the Musk/X shot, Nscale bars over the Minecraft shot, AEGIS thresholds over the Dream Labs robot shot — while QA still passed (QA checks existence/format, not graphic relevance). Root-cause fix, not a per-day edit: the hardcoded map is deleted from both render paths. Analytics now apply ONLY when the worker writes a per-run `pipeline/output/analytics_map.json` ({"<shot_index>": "<analytics_*.mp4>"}) for the current script; with no file, planned visuals render untouched. Evening run re-rendered clean on v2026.10.20.6 and re-published to Telegram, superseding the first send.


## 2026.10.20.5 — 2026-10-20
- PAIRING CORRECTION (user, on the v2026.10.20.4 fix: "nscale should remain but paired with someone from that company. And anthropic with dario"). The .4 data fix moved story 4's icon to Anthropic; the user wants the opposite split: the Nscale–Anthropic deal story KEEPS the Nscale logo, paired with Nscale's own founder/CEO Josh Payne (real photo verified across BusinessCloud / BM Magazine / CNBC Events — the same official headshot — pinned as person_josh_payne.png), and Dario Amodei anchors the Anthropic hook (story 5, the AEGIS story; Anthony Cimino still appears in that story's deep dive where he is named). Intro portrait regenerated to match (Payne character #4, Dario #5; primary portrait generator 503 again — Canva fallback per the chain) + selfplug rebuilt. PAIR CONSISTENCY rule refined in the daily cron: when two stories share a company or a person, split the pairings — one story takes the shared company with its person, the other takes the partner company with a person from THAT company; the same face never anchors two hooks.

## 2026.10.20.4 — 2026-10-20
- HOOK-PAIR COMPANY CONSISTENCY (user, Oct 20 video at 00:28: "you swapped the person for nscale and anthropic"). Root cause: the script's `story_icons` and `story_people` maps are picked independently — for the Nscale–Anthropic deal story the worker chose Nscale as the central company (logo) but Dario Amodei, Anthropic's CEO, as the central person — and `_build_hook_pairs` stacks whatever the two maps say, so hook #4 shipped Anthropic's CEO over the NSCALE wordmark. Every file was individually correct, so frame review passed it; nothing checked AFFILIATION. Fix at the instruction layer (synced to the daily cron): step 3 gains a PAIR CONSISTENCY rule — a story's person and icon must come from the SAME organization; pick the organization by the story's central person and let the icon follow the person (the face is the stronger identifier). Step 3c gains a PAIR CHECK: in every headline hook, confirm the person belongs to the company whose logo sits under them. Today's video corrected by data fix (story 4 icon -> logo_anthropic.png, matching Dario's deep-dive + portrait) and re-rendered.

## 2026.10.20.3 — 2026-10-20
- VISION CROPPING IS THE STANDARD (user, after the Oct 20 video's 1:39 headline slice and a successful manual test): the daily worker now vision-crops every article/document/X-post evidence shot itself — full microlink screenshot (articles 500x900, X 900x1400), crop picked and verified BY EYE (articles: kicker + complete headline + dek + byline, no site chrome; X: exactly the one post, avatar through action bar, no header/replies), pinned as a verified pin (.jpg + .png). Worker instructions synced in the daily cron (step 3b VISION-CROP PINS + step 3 X POST VISUALS). The tweet card is demoted to in-pipeline fallback for X posts with no pin.
- X LOGIN WALL (user): if the microlink screenshot of an X post hits a login wall, the worker opens the post in the live browser (the user's logged-in X session), screenshots the post column there, vision-crops and pins that. Tweet card only if both routes fail; a login wall is never pinned.
- Code backstop in `visuals.py`: `_crop_to_content` now whitespace-snaps its horizontal edges (`_snap_edge_to_whitespace`) as the final adjustment — an auto-crop edge can never rest inside a text line again (grow-first toward the nearest real block gap, shrink second; contract-tested exhaustively on the Oct 20 failing screenshot: every possible edge in the headline zone lands in whitespace). Root cause of the original slice: the headline-block detector locked onto the site header as the block, and the sized box's bottom edge landed mid-glyph in headline line 2. The snap does not make the auto-crop smart — it can still under-include (it cleanly drops line 3 of that headline instead of slicing line 2) — which is exactly why vision pins are now the standard and the auto-crop is only the backstop.

## 2026.10.20.2 — 2026-10-20
- TikTok description now ships with the video (user: "Send the tiktok description along with the video to telegram from now on"). `publish.py` sends the script's description as its own plain-text Telegram message immediately after the video (`telegram_send_description`), so it is copy-paste ready on the phone; hashtags are appended only when the description text doesn't already carry them. A failed description send prints a loud WARNING but never blocks the publish (the video is already out and story ids must still be marked posted).

## 2026.10.20.1 — 2026-10-20
- X-post shots now actually render the tweet card (frame review 2026-10-20: the Musk SpaceX-pledge shot screenshotted the CNN article instead of the tweet card, because `fetch_visual`'s screenshot fallback tries the article URL first and stops at the first success — the story's `x_media_url` was never reached). Root cause at pipeline level: `visuals.py` now sorts x.com/twitter.com URLs first in the screenshot-fallback loop when the shot's `visual_subject` names the X post ("x post" / "x.com" / "tweet"), so `_screenshot_article`'s tweet-card path fires. Shots whose subject is not the post keep article-first ordering.
- No cron instruction change — the `x_media_url` contract ("include the URL, the card is automatic") now holds.

## 2026.10.19.6 — 2026-10-19
- Tweet cards rebuilt to look like actual X posts (user: "the x posts you made look ugly — there's got to be a better open source project"). Root cause: the v2 card was a hand-drawn PIL approximation (crude geometric icons, DejaVu type, no engagement data) — it could never look like X because it wasn't X's design. New `pipeline/tweet_card.py` v3 follows Vercel's react-tweet (MIT) philosophy: fetch the real tweet payload via the fxtwitter API (author, real avatar, verified type incl. gold org badge, like/repost/reply/view counts, attached photos) and render X's own dark-embed styling as self-contained HTML (Noto Sans, X's exact color tokens, true X icon paths), rasterized at 2x with headless Chromium via new `pipeline/tweetshot/render.mjs` (puppeteer-core; the browser gets no network in this env, so avatar/photos are inlined as data URIs). Counts are real now (v5 deliberately omitted them — oEmbed has none and faking would be dishonest). Resilience: fxtwitter rate-limits per IP under burst use (also 403s Python TLS fingerprints — curl is used for fetch), so 3 attempts with 45s backoff, then oEmbed fallback (author/handle/text/date, icons without counts rather than fake zeros), then the old PIL renderer. No cron instruction change — the `render_tweet_card(url, dest)` contract is unchanged.

## 2026.10.19.5 — 2026-10-19
- Tweet cards now faithful to real X posts (user: "why don't they look exactly like x posts?"). `pipeline/tweet_card.py` v2: real profile avatars via unavatar.io (circular-cropped), blue verified checkmark badge, X-accurate action icon bar (reply/repost/like/views/bookmark/share), pure-black X dark-mode styling with thin divider borders. Engagement counts omitted — oEmbed doesn't provide them and faking numbers would be dishonest.

## 2026.10.19.4 — 2026-10-19
- X posts now render as clean oEmbed tweet cards, never screenshots (user: post still badly cropped at 00:49/02:11). Root cause: screenshotting x.com is fragile by nature — login walls, dynamic layout — and every fixed-percentage crop (63%, then 28%) is a guess that breaks on the next layout; the 28% crop was cutting into the post text itself. New `pipeline/tweet_card.py` fetches the tweet via X's official oEmbed endpoint (author, handle, text, date — no nav, no login wall, no ads) and renders a clean dark-mode card with PIL. `visuals.py` `_screenshot_article` now routes x.com/twitter.com URLs to the tweet card and skips the microlink screenshot path entirely (screenshot kept as fallback if oEmbed fails). Cards are deterministic, always fully in frame, and blend with the video's black background.
- Cron worker instructions synced via cron.update + cron.view.

## 2026.10.19.3 — 2026-10-19
- Five user-reported frame fixes (00:17/00:23/00:49/02:11/01:24), all root-caused at pipeline level. (1) Meta logo missing from hook pair: the white-background keying in visuals.py `_build_hook_pairs` checked RGB whiteness without considering alpha — a white-on-transparent logo has white RGB even where alpha=0, so the keying wiped the mark itself. Keying now only applies to opaque files (alpha ~255 everywhere); render.py already guarded this correctly. (2) Tesla logo tiny then overflowing: the 04:00 hook pair was built before the autocrop fix landed, and `_build_hook_pairs` skipped rebuilding when the file existed (`if out.exists(): continue`) — the 12:26 re-render reused the stale file for 8 hours. Hook pairs now always rebuild (milliseconds of PIL work; staleness is a shipped bug). The autocrop then made wide logos overflow, so logo width is capped at 90% of the person photo's width. (3) X screenshots cut off the post: `crop_x_screenshot` kept the LEFT 63%, but X's post column sits center-right — the crop kept the nav sidebar (dead space) and severed post text mid-sentence. Now crops from 28% to keep the full post column. (4) Irrelevant stock clip (covered car for an ethics story): the broll query was metaphorical ("figure hiding face behind hands in dark room") and Pixabay matched literally. New cron rule LITERAL BROLL: queries must describe literally visible things; the shot's query was rewritten to "cryptocurrency wallet on smartphone screen" and the bad clip quarantined from the catalog.
- Cron worker instructions synced via cron.update + cron.view (LITERAL BROLL rule added).

## 2026.10.19.2 — 2026-10-19
- Intro portrait fallback chain (user: primary image generator -> Canva ->
  Google AI Studio). Root cause: the 2026-10-19 03:45 run's primary
  portrait generator 503'd and the cron had no fallback instruction, so
  the video shipped logos-only and the rescue (Gemini quota-out, Canva
  worked) stayed a manual one-off. The daily cron's INTRO PEOPLE IMAGE
  step now carries the ordered chain: (a) Canva generate-image landscape
  3:2 with minimal job polling (each poll spawns dup designs) + full-res
  via separate-image-layers -> export-design jpg q95 -> curl signed URL;
  (b) Google AI Studio gemini-2.5-flash-image via the connector script —
  skipped when quota says exceeded (free tier, no billing changes). Same
  eye-verify + aspect >= 1.25 bar on fallback pins; total failure ships
  logos-only with an honest heads-up. Synced via cron.update + cron.view.

## 2026.10.19.1 — 2026-10-19
- Logo autocrop (user: the Tesla logo rendered tiny in the intro). Root
  cause: the pin was a 980x980 file whose mark occupied only a 711x213
  middle band — scaling the padded file to LOGO_H=112 shrank the mark
  to ~24px. render.py's _guard_logo now autocrops every logo pin to its
  content bounding box before scaling (invisible-content check still
  runs on the uncropped file so near-empty pins keep the glyph
  fallback); the same crop was added to visuals.py's hook-pair logo
  path. Any padded logo file now renders at full mark size.

## 2026.10.18.3 — 2026-10-18
- BREAKING voice continuity (user: the exclaimed "Breaking!" sounded like
  a different voice). Root cause: the "!" made split_sentences emit
  "Breaking!" as its own synthesis chunk and Kokoro reset prosody for
  the one-word exclamation. tts.py now keeps it in the SAME chunk as the
  following sentence — the "!" still buys exclamation energy + a pause,
  but the voice stays continuous. Fingerprint gains a "code" version so
  the behavior change invalidates the stale two-chunk cache.
- Character+icon headline hooks (user): person-less stories no longer get
  a logo-only hook pair. _build_hook_pairs crops the story's invented
  Pixar character from intro_people.png (selfplug face detection,
  left-to-right story order; loud warning + logo-only fallback when the
  face count doesn't match the story count) and stacks it over the icon
  exactly like a person photo.

## 2026.10.18.2 — 2026-10-18
- BREAKING delivery (user): the "BREAKING" kicker is now a true neon
  solid red (255,30,30) — the old (255,70,70) read as almost orange.
- BREAKING delivery (user): the narrator now exclaims the cold-open
  kicker — tts.py synthesizes the cold open from a "Breaking! ..."
  variant (exclamation energy + pause) while words.json/captions keep
  the punctuation-free "Breaking". Fingerprint covers the TTS variant
  so the cold open re-synthesizes; all other segments keep cache hits.
- TTS hermetic root-cause fix (found while shipping the above): any
  cache-miss TTS run died at the first segment — huggingface_hub builds
  an httpx client that crashes parsing this VM's proxy env (InvalidURL
  on bracketed-IPv6 no_proxy entries). tts.py now sets HF_HUB_OFFLINE=1
  and drops proxy vars (the Kokoro model is cached locally; TTS needs
  no network), so synthesis can never die on proxy parsing again.

## 2026.10.18.1 — 2026-10-18
- Text-card guard false-positive on dark photos (visuals.py). `_is_text_card`
  now also requires bright-pixel fraction > 0.03 before rejecting a pin — a
  real text card has bright text on black (bright ≈ 0.134), but a dark-
  background product photo (Surface Laptop Ultra pin: dark 0.895, bright
  0.001) was being rejected and left the shot with no visual. Dark photos
  no longer read as text cards.
- New analytical animations (analytics.py): DeepSeek Search/Fetch API price
  card ($0.75 / 1K calls, SEARCH + FETCH API rows), DeepSWE v1.1 benchmark
  bars (77.0 vs 74.0 vs 73.0), RTX Spark unified-memory bars (24 GB base vs
  128 GB max). Fixed a label-overflow layout bug in the API price card.
  All BT.709-tagged, neon green on black.
- render.py `_analytics_map` (portrait + landscape) extended for shots
  12/13/15 (DeepSWE bars, API price card, memory bars); shot-13 expected
  ERROR in the visuals log ("no visual available") is by design — the
  render-time override supplies the animation.

## 2026.10.17.4 — 2026-10-17
- Intro portrait size/centering (user: the group portrait should be more
  centered and bigger). render.py: portrait width 950 → 1020 (near
  full-bleed with 30px margins) and its top is now computed as
  960 − height/2, centering it on the frame's vertical middle; the logo
  row is laid out after the portrait so it always sits just above
  wherever the portrait lands. For the standard 3:2 portrait this puts
  it at y 620–1300, centered at 960.

## 2026.10.17.3 — 2026-10-17
- No-repeat-faces rule (user: OpenAI appeared in two stories, so the
  second hook needs Altman but a different shot of him). When the same
  person is central to 2+ stories, each headline hook must show a
  DIFFERENT verified photo of that person — a repeated face across hooks
  reads as a duplicate visual. Two durable pieces: (1) `_build_hook_pairs`
  now FAILS LOUD if two story_ids map to the same person file, so a
  repeated face can never ship silently; (2) the cron STORY PEOPLE step
  now requires pinning a distinct verified photo per story
  (person_<name>_2.png, _3.png…) and mapping each story_id to its own
  file. Today's 0:06 hook (OpenAI rogue agents) now shows a second,
  eye-verified Altman shot (WEF stage) while the Chrome-tabs hook keeps
  the original studio portrait.

## 2026.10.17.2 — 2026-10-17
- Evidence-document root-cause fix (user: at 0:46 the video showed an
  unrelated "AIToolsRecap" promo banner while the narration described
  OpenAI's misalignment disclosure page). Root cause: the story's source
  URL was a republisher (aitoolsrecap.com), and the first-shot
  story-owned pre-pass blindly consumed its og:image — which was the
  site's promo banner, editorially unrelated to the story. Durable fix:
  new `_names_document()` guard in visuals.py — an evidence shot whose
  visual_subject names a specific document/page (page, report,
  disclosure, article, document, filing, paper, memo, transcript, post,
  blog, notice) now skips the story-owned og:image entirely and falls
  through to the screenshot path, which shows the actual document.
  Today's 0:46 shot was also re-pinned to an eye-verified screenshot of
  OpenAI's real Misalignment Reports page (alignment.openai.com/
  misalignment-reports) and the video re-rendered.

## 2026.10.17.1 — 2026-10-17
- Emphasis-pill vs analytical-graphic overlap (root cause of a shipped
  frame where the white "24 YEARS OF HOSPITAL DATA" pill sat on top of
  the analytical clip's own "24 / YEARS OF HOSPITAL BED DATA" text):
  render.py now skips a story emphasis pill when its time window overlaps
  an analytical-animation shot — the graphic IS the punch, the pill is
  redundant. Logged as "[render] emphasis segN: skipped — analytical
  shot owns the punch".


Every pipeline upgrade bumps `VERSION` and adds an entry here, newest first.
The version is stamped into every render's `qa.json` (`pipeline_version`)
so any video can be traced to the exact code that built it.

## 2026.10.16.4 — 2026-10-16
- Bot-wall post-crop re-scan (root cause of a shipped Reuters "Access is
  temporarily restricted" wall): the verification/paywall/adblock scans
  ran on the FULL screenshot, but the content crop could isolate the
  wall — the pre-crop page had enough chrome to pass spread/density,
  then the crop kept only the wall text. `_screenshot_article` now
  re-runs all three scans AFTER cropping and rejects wall-isolating
  crops. Also: `_build_hook_pairs` now keys out opaque white logo
  backgrounds (mirroring the intro loader) — an opaque-white Tencent pin
  had shipped as a white box in the headline hook.

## 2026.10.16.3 — 2026-10-16
- Hook-pair glyph support (root cause of today's QA quarantine):
  `story_icons` entries like "glyph:robot" were treated as filenames by
  `_build_hook_pairs`, so glyph stories got NO hook pair and fell back to
  generic stock in the headline hook — the age-progression hook drew the
  same Pixabay clip as its neighbor and failed QA's
  no-consecutive-duplicate gate twice (the quarantine retry re-fetched
  the identical clip). visuals.py gains a module-level `draw_glyph()`
  (mirroring render.py's intro glyphs) and `_build_hook_pairs` now renders
  glyph specs into proper logo-only hook pairs.

## 2026.10.16.2 — 2026-10-16
- Third analytical animation for the daily: `google_links` (publisher
  referral traffic from Google -40% in a year, AI Overviews at 2B monthly
  users — the -40% row carries the bar; the 2B row is a standalone
  counter, never a misleading fraction of 40). Wired as shot 18 in both
  `_analytics_map` paths. Also replaced the dark server-room verified pin
  (rejected by the text-card scan: >75% dark pixels) with a bright
  data-center hallway, and added a slug-keyed copy of the Pichai pin so
  the Google deep-dive's person shot resolves to the verified photo
  instead of an article screenshot.

## 2026.10.16.1 — 2026-10-16
- Two new analytical animations for the daily's number-heavy shots:
  `certin_attack_timeline` (CERT-In: criminal attack time compressed from
  DAYS to HOURS — red vs neon bars) and `kospi_crash` (KOSPI -14.3% on the
  week / -8% Thursday / 7 straight losing sessions). Both follow the
  existing generator pattern (BT.709 tagging, CAPTION_SAFE_BOTTOM=1090
  enforced by `_write`'s fail-loud scan, monotonic easeOutCubic on
  displayed numbers). Wired into render.py's `_analytics_map` (shots 9
  and 14) in both the portrait and landscape paths; clips pre-generated
  into `cache/generated/`.

## 2026.10.16.1 — 2026-10-16
- Intro portrait layout root-cause fix (user: the intro showed one
  character taking half the screen): when most stories have no central
  person, the worker generated a single-person PORTRAIT (1120x2240) as
  intro_people.png, and render.py scaled it blindly to 950px wide —
  950x1900 covering half the frame and colliding with the intro text.
  Two durable fixes: (1) render.py now FAILS LOUD if intro_people.png
  has aspect < 1.25 (the check sits outside the missing-file try/except
  so the error can never be swallowed) — a wrong-aspect pin can never
  ship a broken intro again; (2) the daily cron's INTRO PEOPLE IMAGE
  step now requires a LANDSCAPE group composition (aspect ≥ 1.25), one
  Pixar character per story in story order (invent a representative
  character when a story has no central person — never a single-person
  portrait), each showing their story's emotion, plus eye-verification
  of the pinned file before the render proceeds. Today's video was
  re-rendered with a proper 5-character landscape portrait.

## 2026.10.14.2 — 2026-10-14
- Analytical-animation caption-overlap root-cause fix (user: at 1:40 the
  red "SOLD OUT THROUGH 2028" overlapped the captions): analytical clips
  are padded at frame y=290 in render.py while typewriter captions start
  around frame y=1430 — but analytics.py had NO caption-safe layout rule,
  so the ASML footer's clip-y-1180 text landed at frame y~1479, inside
  the caption band. Durable fix: (1) new `CAPTION_SAFE_BOTTOM = 1090`
  rule in analytics.py (50px clearance above the caption zone); (2) `_write`
  scans every 6th frame and FAILS LOUD if any non-black pixel is drawn
  below that row — enforced for all current and future generators;
  (3) `asml_record_quarter` rows re-spaced (280→240 pitch) so the footer
  sits at clip y 1000 (frame y 1290). Standing rule: analytical text must
  stay above the caption zone; the renderer can no longer be handed a
  clip that violates it.

## 2026.10.14.1 — 2026-10-14
- Self-plug montage hair-zoom root-cause fix (user: at 00:32 the shot
  zoomed into a character's hair): YuNet fired a 70x88px false positive
  ON THE CURLY HAIR between two heads, and the IoU/center dedupe kept it
  (IoU ~ 0 vs the real face boxes). The montage spent a whole solo
  segment pushing into hair. selfplug.py now drops detections under 25%
  of the largest face box's area (real faces in a group portrait are all
  similar scale — self-calibrating, no hardcoded sizes), caps at 5 faces
  (intro max), and writes a reviewable `cache/generated/selfplug_boxes.jpg`
  contact sheet (red = detection, green = montage close-up box) so frame
  review can verify every box lands on a face. Standing rule: montage
  close-ups must center on verified faces, never hair/ears/background.

## 2026.10.13.4 — 2026-10-13
- Headline crop root-cause fix (user: title cut at 00:22): (1) the
  y-search window (120-450px) was tuned for 500x900 but captures are
  1000x1800 — headlines pushed down by tall headers fell outside it, so
  detection failed silently; now searches the top 50% proportionally.
  (2) The density fallback used a FIXED 600px height that sliced
  multi-line headlines; now groups ALL wrapped headline lines into a
  block and sizes the crop to the block (block bottom + 60px), never a
  fixed height. Standing rule: the article title must be fully in frame.
- Emphasis pill face-avoidance (user: pills cover faces): detect_face now
  returns the full box [cx,cy,w,h], not just the center. The pill goes to
  the third-center (320/960/1600) whose band clears the face box (+120px
  margin); person shot with no detected face defaults to top third.
  Standing rule: emphasis shows above or below faces, never on them.

## 2026.10.13.3 — 2026-10-13
- Render/visuals metadata truth (root-cause fix): QA's black-frame guard
  reads visuals.json `source`, but render-time overrides never updated it —
  the analytics-map swap and hook-pair swap changed what RENDERED while
  visuals.json still said "black-frame"/"duplicate-needs-review", failing
  clean renders. Now: the analytics override mutates the visual in place
  and stamps source="analytical-animation"; the hook-pair swap stamps
  source="hook-pair"; render.py writes the updated visuals list back to
  visuals.json after the shot loop. QA now judges what actually shipped.
- Five new analytical animations: muse_wonder_benchmark (Opus 5.5 58 /
  Wonder Full 56 / Wonder 52), maia_300_specs (40% tokens/MW, 96 chips/rack,
  7x throughput), ai_oversight_letter (400 scientists, 34 countries,
  AIR-GAP), asia_selloff (KOSPI -6%, Kioxia -13%, Samsung -10%, SK Hynix
  -8%), imf_warning ($1.4T commitments, 10% IG issuance, -1.1% GDP).

## 2026.10.13.2 — 2026-10-13
- Landscape hooks get captions (user): headline hooks and branding now
  use the split layout (terminal panel | visual) like story deep-dives —
  the panel types the hook narration, so no segment lacks on-screen text.
  Only the cold-open intro stays full-frame (it types its own).
- Logo inversion root-cause fix (user: "lancet logo is too white"):
  _build_hook_pairs inverted the COMPOSITED image (dark text on black
  background), turning the background white — shipped a gray-on-white
  Lancet pair. Now inverts the RGBA colors while keeping alpha, then
  composites onto black. Inverted marks normalized to 85% white in both
  the pair builder and _load_intro_logo (raw inversions glare against
  native white logos). Standing rule: prefer white logo artwork, always
  on black.
- Hook wordmarks capped at 900px in the visual region (logo-only pairs
  sprawled across the full region width).
- Fixed unlabeled filtergraph output crash on badgeless splits (added
  explicit -map [stack]).

## 2026.10.13.1 — 2026-10-13
- Landscape mode (user): new 16:9 `landscape` config mode (1920x1080) and
  render path, developed on the `landscape-layout` branch. Story
  deep-dives split the frame — left third is a live terminal panel typing
  the narration in green mono synced to TTS word timings (this IS the
  caption track in landscape; no ASS captions burned), right two-thirds
  plays the visual. Intro/hooks/branding stay full-frame: wide terminal
  intro, side-by-side person+logo hook pairs (new
  `hook_pair_<sid>_landscape.png`, cache-safe alongside the 9:16 pairs),
  pillarboxed self-plug. Story badge top-right of the visual region,
  watermark top-left of the visual region, hook number pills centered on
  the badge. Story emphasis pills skipped in landscape (the panel shows
  the text). QA safe-area check is mode-aware (YouTube zones: top 70px,
  right 40px, bottom 7%). Render writes `chapters_landscape.txt` (YouTube
  description chapters). Two-up render support: a shot with
  `two_up`/`path2` shows both visuals side by side in the visual region
  (data contract documented; worker markup pending). The 9:16 daily path
  is untouched.

## 2026.10.12.3 — 2026-10-12
- Story ordering rule change (user): most interesting/important story
  FIRST — supersedes the 2026-10-11 smallest-first crescendo rule.
  Headline hooks, story numbering (#1–#5), and deep dives all follow the
  same descending order; #1 is the story viewers most need to see.
  Implemented in the daily cron worker instructions (via cron.update +
  cron.view). Takes effect on the next scheduled run (2026-10-13 03:45 PT).

## 2026.10.12.2 — 2026-10-12
- A/V sync root-cause fix (render.py): no-loop clips (self-plug,
  analytical animations) played ONCE via `-t {dur}`, but ffmpeg's `-t`
  is a cap, not a pad — the self-plug clip (5.69s) ended 1.36s before
  its planned 7.02s shot, shifting EVERY later shot early so story
  visuals changed before the narrator finished the prior story (user
  report). The render now probes the clip and appends
  `tpad=stop_mode=clone` to hold the last frame to the planned
  duration. qa.py gained a backstop: every rendered shot segment must
  match its planned duration within 0.15s or the run fails.
- Narration voice: Kokoro `am_echo` (user pick from the 9 American male
  voice samples; was `af_sarah`). TTS fingerprint includes the voice,
  so all segments re-synthesize.

## 2026.10.12.1 — 2026-10-12
- Badge pill visibility fix (render.py): the story-number badge's dark pill
  was drawn at alpha-140 black — invisible on black backgrounds, so badges
  rendered as bare numbers. Pill is now a lifted dark gray (48,48,48,235)
  that reads as a pill on black.
- Hook pairs for person-less stories (visuals.py): `_build_hook_pairs`
  now builds a logo-only pair when a story has no person photo (previously
  skipped → hook fell back to a generic article screenshot). Dark logos are
  auto-inverted so they read on black.
- Pipeline versioning introduced: `pipeline/VERSION` + this changelog +
  version stamped into `qa.json`. Upgrade flow documented in the
  `pipeline-upgrade` skill; cron instructions reference it.

## Earlier history
- 2026-10-12: BT.709 colorspace tags on still-image encodes (render.py) —
  fixes green-hue chroma shift on dark backgrounds (user report 00:35).
- 2026-10-12: selfplug.py YuNet face-dedupe (merge overlapping detections).
- 2026-10-12: visuals.py accepts `.png` verified pins (were skipped).
- 2026-10-11: story-number badges #1–#5 (x=W-336, persistent per story),
  headline hook pills (x=w-198), per-letter typewriter captions with
  trailing █, y=960 centering + y=1400 caption-safe clamp, hook
  person+logo pairs in headline hooks (intro reverted to logos-only),
  logo alpha compositing + white-box rejection, dHash no-repeat dedupe,
  screenshot stage (analyze → root-source → crop), no-logo-fullshot rule,
  periods script style (retired comma-heavy), stories ordered smallest
  stakes first.
- 2026-10-11: analytical animations BT.709 tagging (analytics.py).
- 2026-10-09/10: terminal intro + captions, neon green #39FF14, red
  BREAKING kicker, Pixar intro portrait + self-plug emotion montage,
  watermark, H.264 High yuv420p + faststart encode standard.

