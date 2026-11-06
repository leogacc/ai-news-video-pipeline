

# Shot Grammar

## Purpose

Decide what each shot SHOWS for every sentence of a narrated video script, so no shot is decorative. Learned from a shot-by-shot analysis of a 282k-play reference video (@theventure, 67 seconds, ~12 shots, hard cut every 4–6s). The reference's rule is simple: the visual always shows the literal subject of its sentence.

## Workflow

For each sentence (or shot unit), find its subject and apply the first matching rule:

1. **Names a person → show their face.** Portrait from web search, eye-verified (never a blind result). Faces anchor the video — the reference puts its main person in 7 of 12 shots, cutting back to him at emotional beats (the explainer close-up, the triumph stage shot), not just at his introduction.
2. **Names a company, product, or place → show the thing.** Office building, logo, product screen, skyline. ("$450B defense company" = the company's glass building.)
3. **States an action → show the action literally.** Hands counting cash for "raising money"; a soldier with a rugged laptop for "the army's system".
4. **Describes a situation → show its visual metaphor.** A kid slumped over a retro CRT desk for "engineers nobody takes seriously"; men in branded VR headsets for "building software".
5. **Captions punch, visuals show — never compete.** Punch labels (2–4 words) go mid-frame as pills; narration caption cards go bottom-third. The picture carries the subject, the text carries the punch. They never fight for the same job.
6. **Documentary beats representative.** The actual artifact wins over a symbolic stand-in: a screenshot of the real paper (not a blackboard), the real code or file (not generic code on a screen), the actual post or quoted message (not a stock debate photo). Evidence has two tiers — (a) the actual artifact, (b) a representative image of the thing — and you always reach for (a) first.
7. **Composite when the sentence has two subjects — identify, don't decorate.** When a headline names both a company and an action, the base scene shows the action; the company is identified through the visual itself (building, product UI, wordmark as the shot's subject per rule 2/9). The middle-right of the top third is reserved for the story number badge (rule 12) — never a logo overlay. A corner mark that can't be identified at a glance is a smudge, not an identifier.
8. **The grammatical subject wins.** When a company and a place both appear, the sentence's subject decides the visual. "Moonshot closes its round" → Moonshot's HQ, not the Hong Kong skyline. The place only wins when the sentence is about the place.
9. **When the story is about a word, show the word.** Name changes, new terms, slogans, quoted lines → the text itself is the visual: the logo or wordmark, a screenshot of the announcement post.
10. **Historical events need historical material.** Illustrate the past with actual material from the event — headlines and photos from that time — never generic present-day stock.
11. **If you name people, show people.** A sentence listing people must show faces — the key ones at minimum. Never let a building substitute for named humans. When two people are named, show the one the news is about (the appointee, not the announcer).
12. **Number the stories for wayfinding.** The 5 story hooks each carry a numbered emphasis pill (1–5) at center-top third. Each story's deep-dive segment shows its number as a badge at middle-right of the top third. The number is the thread: hook "3" → story "3". Numbering follows story order and is applied automatically by the pipeline — the script never hand-writes numbers, and hooks carry no other punch label.

## Anti-patterns (how the first version of this grammar failed)

- **Representative stand-ins:** a blackboard for "the paper", generic code for "Lean", a debate stock photo for one specific quoted complaint. Rule 6 exists because the first pass kept picking symbols of the subject instead of the subject.
- **Place-over-company:** the Hong Kong skyline for a sentence whose subject is Moonshot. Rule 8 exists because a secondary named place kept winning over the sentence's actual subject.
- **Building-for-people:** a White House exterior standing in for five named humans. Rule 11 exists because buildings kept substituting for faces.
- **Logo-less company shots:** showing the action without identifying whose action it is. Rule 7 exists because company+action sentences kept dropping one of their two subjects.

## Sourcing order (evidence first)

1. The story's own X-post media
2. Publisher page media (og:image / og:video)
3. Web-searched frame, eye-verified by the research loop and pinned (never a blind search result; never Wikimedia Commons, never stock — blind results hallucinate)
4. Specific stock photo/clip matching the sentence — illustrative tier only, and only after eyeball verification
5. Title card — last resort only

Logos: retired 2026-10-09 — the middle-right of the top third now carries the story number badge (rule 12), never a logo overlay. Company marks appear only as shot subjects (rules 2/9), eye-verified and pinned like any other evidence.

## Output contract

One shot per important sentence; hard cut every ~4–6 seconds. Each shot:
`{"text": exact sentence(s) from the narration, "visual_type": "evidence"|"illustrative", "visual_subject": "exact named entity (evidence only)", "broll": "concrete query — never generic"}`

## Operating rules

- If a shot doesn't illustrate its sentence, replace it. Never keep a decorative shot.
- Faces dominate: for a person-driven sentence, choose the face over the place.
- Re-show the key person's face at the story's emotional turn, not only at their introduction.
- When two people are named in one sentence, show the one the news is about (the appointee, not the announcer).
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
