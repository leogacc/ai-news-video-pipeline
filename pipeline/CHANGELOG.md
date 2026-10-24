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

