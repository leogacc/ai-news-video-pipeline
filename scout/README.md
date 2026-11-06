# X Scout

Separate scout run for the AI-news video pipeline. It is NOT the daily
digest scan (17:00 PT) and NOT the daily pipeline run (18:00 PT). It has
its own cron, its own output folders, and its own state file, so it can
never overwrite a daily digest output.

## 4x-daily finds mode (user, 2026-10-26; supersedes the 3x-daily mode set
2026-10-25)

The scout runs FOUR TIMES A DAY — 7am, 11am, 4pm, 7pm Pacific, as four
daily schedules sharing one body — and builds at most ONE clip per
run: the single top FIND of that run. It still scouts its sources
(X accounts + X keywords + Threads accounts + Threads keywords; Threads accounts added 2026-10-25, Threads keywords and @terries.ai added 2026-10-26) and still SAVES
everything it classifies to
`scout/saved_items.json` first — releases and rumors found in a run are
saved to the central pool for the daily pipeline, but they are NOT built
into clips or a rumors digest by these runs. The old behaviour
(one clip per release/find, plus a rumors digest) is paused while this
mode is in force.

Ranking the top find (user, 2026-10-26): most notable and interesting first — judged by what is most interesting, pressing, exciting, or important for the AVERAGE INTERESTED PERSON, not for insiders; broad appeal beats a technically neat but narrow find (the same descending-interest rule as the daily digest), with a verified link
(repo, announcement page, or demonstrable demo). Recency is only a
tie-breaker: each run searches back UP TO 3 MONTHS, and a find from
weeks or months ago that was never clipped is fully eligible if it is
the most interesting unclipped find. If no find clears that bar, build
nothing, clip nothing, and stay silent — never invent a find to fill a
run.

EXCITEMENT GATE (user, 2026-10-27): "exciting" is a GATE, not just a
ranking factor. A top pick must be genuinely exciting for the average
interested person — surprising, big, first-of-its-kind, high-stakes, or
viscerally interesting. Routine, incremental, or "company X adds Y
support" stories do NOT clear the bar, no matter how recent, well-sourced,
or big the company — the named below-the-bar example is the 2026-10-27
ChatGPT iCloud Mail/Calendar plugins story. If the pool's best item is
merely interesting but not exciting, build nothing and end the run
silently — never fill a run with a routine story. Log below-the-bar
skips with the reason "not exciting" in the run report.

RECALIBRATION (user, 2026-10-28, on the XREAL Aura clip: "stories like this aren't exciting enough"): product and hardware launches do NOT clear the bar even when first-in-category with a polished demo. Named second below-the-bar example: the 2026-10-28 XREAL Aura story — first wired Android XR glasses, $1,099, with a polished Google demo — which the user judged not exciting enough despite its first-of-its-kind hardware and visceral demo. First-in-category does not by itself make a story exciting; without a surprising capability, an unexpected crossover, or stakes beyond the product itself, a launch stays below the bar like any routine story.

RECALIBRATION (user, 2026-11-02, on the NYT v Brave clip: "Stories like that aren't appealing enough. Don't make videos for stories this boring."): legal-dispute stories do NOT clear the bar on scale or stakes alone. Named third below-the-bar example: the 2026-11-02 NYT v Brave story — the New York Times suing Brave Software over AI scraping — which the user judged boring despite its same-day freshness and broad subject matter. A lawsuit's stakes are legal and financial, not a surprising capability or a visceral hook; without something beyond the dispute itself, a legal fight stays below the bar like any routine story.

GEMINI NOTE (user, 2026-10-28): the 2026-10-17 "no Gemini alerts" withdrawal covers personal alert pings ONLY. Gemini finds and releases remain eligible for clips and the digest like any other item — never skip a Gemini item on the alerts basis. (The 11am 2026-10-28 run wrongly skipped the official Gemini 4 Carbon release on that basis; the user corrected it and ordered the clip.)

THREADS PROFILE LISTING LAG (2026-10-28, user-supplied miss): Threads profile listings can lag new posts by 30+ minutes. Evidence: the 11am 2026-10-28 run paged kimmonismus and saved the Mario + MotionBricks posts via profile, but NEVER saw kimmonismus's 10:49 Gemini 4 Carbon post — it is absent from seen_threads_urls (108 entries), so the listing at run time simply did not contain a post 10–30 minutes old. Mitigation, every run: RE-PAGE each Threads profile at the END of the run (after the keyword passes) and save anything new — a second sweep catches posts that indexed mid-run. If an account's newest seen post predates the run window, say so in the run report (listing lag suspected). And when building a clip, sweep the surfacing account's same-story posts from the last 24h for media (see the clips template's SAME-STORY SWEEP rule).

## Dedupe and the major-progress exception

Dedupe is tracked in TWO places, and both must be checked before
building anything: `scout/state.json` (seen / posted ids) AND
`scout/clipped_finds.json` (one entry per clipped find, with post_id,
clip folder, and clip date). Never re-clip a post already in either
file — EXCEPT when major progress on that same find is documented and
worth sharing. Major progress means a substantive new development, for
example: a new major version or official release superseding the demo,
a materially changed capability or benchmark (not a restatement of the
same numbers), or confirmation/adoption that changes the story. It does
NOT mean: the same post reposted, a small engagement bump, a minor
bugfix, or the same claims repeated by another account. A major-progress
re-clip must be labelled as an update in its description ("Update on
X — previously clipped on <date>"), must say what is new versus the
previous clip, and must be appended to `scout/clipped_finds.json` as an
update entry against the original post_id.

**Central source rule (user, 2026-10-24): ALL pipelines retrieve their
data from what this scout saved.** The daily digest, clips, and rumors
digest read `scout/saved_items.json` first, before doing any of their
own searching. That is why the scout's keyword list must be broad
enough to cover top stories, releases, and finds — not just one account.

**THREADS MIRROR RULE (user, 2026-10-25): a Threads post that mirrors
an already-saved X post is coverage, not a new find.** His Threads
posts mirror his X posts (verified 2026-10-25: the same Anthropic IPO,
Opus token-volume, Kimi rate-limits, Nanbeige, and G1 ladder items on
both). A Threads item is a mirror when it has the same author, the same
story, the same day, and near-identical text to an already-saved X
item: save it with its source noting the X post_id it mirrors, and
NEVER pick it on its own — it must not produce a second clip of a story
already clipped from X. Only a Threads post with NO X counterpart is an
eligible pick, and a clip built from one must name its Threads source
(via @handle on Threads) in its bio and description, not X.

## What it does, each run

1. **Scout THREE sources, not one:**
   - The accounts in `scout/accounts.yaml` (never guess accounts).
   - The keyword searches in `scout/keywords.yaml` (the combined
     `search_queries`, last 24h first). A keyword hit is not a story
     by itself — it must be a notable post with source + date + author.
   - The Threads accounts in `scout/threads.yaml`, via the Threads
     connector (see "How Threads is accessed" below). A Threads hit
     is subject to the MIRROR RULE in the dedupe section.
   - If NO source can be read at all, report “scout not configured”
     and stop. Do not publish anything, do not build anything, do
     not guess.
2. **Classify each new notable post as a release, a rumor, or a find.**
   - Release: an official announcement — a product/model launch, a
     company post, a confirmed feature, a paper or demo from the lab
     itself.
   - Rumor: unconfirmed — a leak, a “reportedly”, a “sources say”, a
     post from a leaker/reporter account, with no company confirmation yet.
   - Find: GENERAL AI finds (user, 2026-10-24 — NOT hacks as a
     category, stay general in the AI space) — community tools, demos,
     projects, research, benchmarks, clever uses that are real and
     demonstrable (repo, code, or demo linked), but neither an official
     release nor a future rumor. If a find happens to be an unlock or
     workaround, label its benchmarks as claimed by its author, and
     do not rename the category to Hacks.
   - If it is neither notable nor clearly classifiable, skip it and log
     why in the run report, not in a published video.
3. **SAVE EVERYTHING first, before building any video.** Append each
   classified item to `scout/saved_items.json` with: post_id, author,
   date, text, url, category (release/rumor/find), source
   (account/keyword/threads + which account, query, or Threads handle),
   and any verified link
   (repo, announcement page). For Threads items, post_id is
   `threads:<post code>` and url is the Threads permalink. Downstream
   pipelines read this file.
   Dedupe against `scout/state.json` and `pipeline/state.json` first.
4. **Releases AND Finds → clips, one clip per release/find**,
   following `templates/clips/template.yaml` in full (transcript scan,
   speaker scan, title + same-length bio, per-speaker face check, no-face
   layout when there is no face, full video uncut when
   information-dense throughout).
   (User, 2026-10-26: releases ARE part of finds — a release is picked
   and clipped exactly like a find and labelled FIND, and releases are
   also eligible for the daily digest. This supersedes any older
   "releases saved only" wording in the scout cron bodies.)
   - If the post has audio or video: process its transcript from that
     audio/video, exactly as in the clips template.
   - If it has NO audio or video (text-only post, article link, image
     only): NARRATE it. Write a short script from the verified text
     only — no invented facts, dates, or quotes — narrate it with
     Kokoro `am_echo` at 1.20×, terminal captions, and visuals from the
     source (vision-cropped screenshot of the post/article, logo, or
     relevant source footage, following the pipeline visual rules).
     The bio line then names the source account / company, not a person
     who is not speaking — but the bio's SOURCE is the ROOT source per
     `templates/clips/template.yaml` `bio_source_rule_2026_10_26` (never
     the X/Threads post that surfaced it). For a find, the bio/description must say
     FIND (not release, not rumor) and label any benchmarks as claimed
     by the author.
   - Output: `pipeline/output/scout/clips/<date>_<slug>/`, one folder
     per release/find, video + transcript + meta file. Never write to
     the daily output root.
5. **Rumors → grouped to the top 3**, following
   `templates/rumors-digest/template.yaml` (copy of Daily Digest, 3
   stories, n/3 pills, “top three AI rumors digest” self-plug, every
   rumor labelled as a rumor with source + date + claim).
   - Output: `pipeline/output/scout/rumors/<date>/`, one digest video
     per run, only if there is at least 1 new rumor (and at most 3).
   - If there are no new rumors, no rumors video is made that run.
6. **Dedupe.** Check `scout/state.json` (seen_post_ids,
   posted_release_ids, posted_rumor_ids, posted_find_ids) AND
   `pipeline/state.json` posted_ids before building anything. Never
   rebuild or re-publish a post already covered. A rumor that later
   becomes a confirmed release is a NEW release, not a duplicate.
7. **Publish to Telegram** in the pipeline's normal telegram_queue
   pattern, one message per clip, one message for the rumors digest,
   each with its description (rumors descriptions must say “rumor” and
   must not present rumors as confirmed; finds descriptions must say
   “find”). Report the run to the user with: accounts + keyword
   queries scouted, new releases/finds found (with clip links), new
   rumors found (with digest link if made), and anything skipped + why.

## How X is accessed

There is NO X connector in Muse, and no X login saved in the Secure
Vault. Until the user confirms otherwise, scouting uses PUBLIC methods
only, as the pipeline already does for X posts: public post pages,
fxtwitter API via curl, web search, and microlink screenshots. The first
post on a public account page shows publicly, logged-out.

Do NOT push the user for an X login, and do NOT invent a login flow.
If the user confirms their X account should be used logged-in, that
access method goes in `scout/accounts.yaml` (`access: logged_in_browser`)
and the browser session is set up by the user in a separate, approved
step — the scout worker does not start that step on its own.

## How Threads is accessed

Threads is connected through the user's linked Threads account
(`threads-cli`, Meta Accounts Center) — NOT by scraping threads.com.
The worker resolves each listed account each run from the linked
account's following list (the user follows him there) and reads his
posts with `profile-threads`. Numeric user IDs are machine handles:
never put them in chat reports or in `saved_items.json` text — use the
handle + permalink.

Threads enforces strict rate limits and scraping protection, so a run
pages `profile-threads` at most 3 pages and stops at the first post
already in `scout/saved_items.json` (by permalink). Never re-fetch
unchanged content on every run and never poll. A 429 is final for that
run's Threads calls: stop them, do not retry, and report the error with
the next published clip (or on its own if it blocks a top find).
Record Threads permalinks seen in `scout/state.json`
`seen_threads_urls`.

THREADS KEYWORD SEARCH (user, 2026-10-26): the combined
`search_queries` in `scout/keywords.yaml` also run on Threads each
scout run, via `threads-cli search` (Top tab; add `--recent 1` for the
same query only when Top returns no notable hit), at most 1 page per
call. A Threads keyword hit must be a notable post with source post +
date + author, saved with source `threads:keyword:<query>` and the
Threads permalink (`threads:<post code>` as post_id). Threads keyword
calls share the run's Threads rate guard: a 429 ends ALL Threads calls
for that run. If a listed Threads account cannot be resolved from the
following list (e.g. @terries.ai, not followed as of 2026-10-26),
report it as unresolvable — never guess its numeric ID, never scrape
threads.com, and note that Threads handle search returns no posts, so
search is not a resolution route; following the account in the Threads
app is what makes it resolvable.

## Files

- `scout/accounts.yaml` — the X account list the scout may use (never guess others)
- `scout/threads.yaml` — the Threads account list the scout may use (never guess others); added 2026-10-25, @terries.ai added 2026-10-26 (not followed yet — see that entry)
- `scout/keywords.yaml` — the master keyword list + combined search queries; runs on X and, from 2026-10-26, on Threads too
- `scout/saved_items.json` — the CENTRAL saved pool: every classified release/rumor/find, with post_id, author, date, text, url, category, source, verified link. ALL downstream pipelines read this first.
- `scout/state.json` — seen / posted / held rumor ids, last run time
- `scout/README.md` — this file
- `pipeline/output/scout/clips/` — release clips, one folder each
- `pipeline/output/scout/rumors/` — rumors digests, one folder per date
- `templates/clips/template.yaml` — release clip template
- `templates/rumors-digest/template.yaml` — rumors digest template
