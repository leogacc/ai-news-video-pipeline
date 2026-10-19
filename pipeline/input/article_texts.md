# AI News Research — Sunday 2026-10-18
*5 stories, ranked most-interesting-first. All facts below come from fetched article text or verified web-search results. `x_media_url` is null for every story: no exact, verifiable X post URL could be recovered (x.com is blocked in this environment), and the task forbids guessing URLs.*

---

## 1. chatgpt-slides — OpenAI launches ChatGPT Slides with real-time co-editing
- **URL:** https://dailyaibrief.com/news/openai-adds-collaborative-slide-creation-to-chatgpt-qNFmvJtV *(replaces the AIWeekly listing placeholder)*
- **X media:** none verifiable — no standalone X announcement of Slides found (only the earlier Oct 14 @ChatGPT post about Space).

**Summary:** In release notes published October 16, OpenAI introduced ChatGPT Slides for creating and editing presentations inside ChatGPT's shared Space workspace. It's rolling out to eligible Pro, Business, and Enterprise users with Space access on web and desktop. Users can start a deck from a conversation, files, an outline, or an example deck; edit text/images/shapes/charts directly or via ChatGPT; invite teammates to edit in real time with shared comments; present from ChatGPT; and export to PowerPoint, PDF, Google Slides, or Keynote.

**Facts:**
- Release notes published **October 16** introduced ChatGPT Slides for creating/editing presentations in Space.
- Rollout to eligible **Pro, Business, Enterprise** users with Space access, on the **web and desktop app**.
- Start from a conversation, files, an outline, or an example deck.
- Edit text, images, shapes, charts directly or ask ChatGPT to make changes; teammates edit the same deck **in real time** and leave **shared comments**.
- Present directly from ChatGPT; web exports to **PowerPoint, PDF, Google Slides**; desktop opens decks in **PowerPoint or Keynote** when installed.
- Same release notes: **GPT-6 Pro** updated with faster responses, improved plugin/tool use, and multiple agents handling parts of a task in parallel — rolling out to eligible Pro users.
- Context (web search): Space was unveiled at OpenAI's **DevDay on September 29**; the rollout is gradual, so many eligible users may not see Slides yet.

---

## 2. deepseek-v41-flash — DeepSeek ships V4.1-Flash-1017 with MIT open weights and search APIs
- **URL:** https://dealroom.co/news/163453-deepseek-moves-up-the-stack-v4-1-flash-update-ships-alongside-its-own-se/ *(confirmed: specific article, kept)*
- **X media:** none verifiable — @deepseek_ai's Oct 17 launch thread exists but the exact x.com status URLs are truncated in every citing source.

**Summary:** DeepSeek released DeepSeek-V4.1-Flash-1017 on October 17, an update to the V4.1-Flash model it launched in September, live on its website, app, and API under the existing `deepseek-flash` name. Weights are open-sourced under the **MIT licence** on Hugging Face and ModelScope. On DeepSeek's own comparison the checkpoint scores **77.0 on DeepSWE v1.1**, ahead of Claude Opus 5's 74.0. Separately, DeepSeek opened its own **Search and Fetch APIs** to all developers at **$0.75 per 1,000 calls**.

**Facts:**
- Released **October 17**; update to V4.1-Flash (launched September). Served under the existing `deepseek-flash` API name; live on DeepSeek's website, app, and API.
- Weights open-sourced under the **MIT licence** on **Hugging Face and ModelScope**.
- DeepSeek calls it "a Pareto improvement in performance and cost": stronger benchmarks, faster task completion, shorter outputs.
- DeepSWE v1.1: **77.0** (up from 74.2), ahead of **Claude Opus 5 (74.0)** and **GPT-5.6 Sol (73.0)** — DeepSeek's own numbers. Also leads its table on Automation-Bench, Agents' Last Exam, Apex Bench.
- Claude Opus 5 still leads on HLE, Terminal-Bench 4.0, ProgramBench, NL2Repo-Bench (same article).
- DeepSeek says it builds complete projects end to end, from games to 3D models, via reinforcement learning with self-feedback.
- **Search and Fetch APIs opened to all developers**, powered by an in-house search engine DeepSeek says serves hundreds of millions of requests daily.
- **$0.75 per 1,000 calls** per endpoint; calls via DeepSeek Harness, Claude Code, Codex stay **free until per-request billing starts Nov 1, 2026** (Beijing time).
- Tuned for DeepSeek Harness and Tencent's **CodeBuddy and WorkBuddy**.
- Context: DeepSeek's latest funding round reportedly grew to **$12–15B at ~$75B valuation**, ahead of a planned Shanghai IPO, per CNBC (cited in article).
- **UNCONFIRMED:** the scan's "763B-parameter checkpoint" figure — the article doesn't state total parameters. (MarkTechPost describes a 552B backbone + 196B Engram memory.)

---

## 3. nvidia-rtx-spark — NVIDIA RTX Spark laptops ship from $2,599 with 128GB unified memory
- **URL:** https://wccftech.com/microsoft-teases-rtx-spark-powered-surface-laptop-ultra-starting-at-2599/ *(replaces the aibriefing.dev homepage)*
- **X media:** none verifiable — no exact NVIDIA X post URL found.

**Summary:** Microsoft opened pre-orders for the **Surface Laptop Ultra**, its first laptop on NVIDIA's RTX Spark N1X platform, starting at **$2,599** with shipping beginning **October 16**. Base config: 18-core N1X CPU, 5,120-core Blackwell GPU, 24GB unified memory, 512GB SSD; tops out at **128GB unified memory** ($5,899 full config) aimed squarely at local AI workloads. The launch lands alongside Meta's 816B Muse Spark Open, which Apple demoed running locally on **four** M5 Ultra Mac Studios at 36.73 tokens/sec — framing the Windows-vs-Apple local-AI contest.

**Facts:**
- Surface Laptop Ultra starts at **$2,599**; shipping begins **October 16**.
- Base: **18-core NVIDIA N1X CPU**, **5,120-core Blackwell GPU**, **24GB unified memory**, 512GB SSD.
- Top config ($5,899): 20-core CPU, 6,144-core GPU, 128GB unified memory, 1TB SSD.
- 15-inch mini-LED HDR touchscreen, up to **2,000 nits** peak; ~4.5 lbs; magnetic USB Type-C charging; triple Type-C, USB-A, HDMI, full-size SD reader, 3.5mm jack.
- The 128GB unified-memory pool is pitched at **local AI workloads** — running larger models locally instead of relying on the cloud.
- Gaming demo: 60 FPS in *Gears of War: E-Day*.
- Price context: HP OmniBook X 14 starts at $2,999 (16" at $3,199), higher configs to $4,499/$4,999.
- Apple/Meta counter-move (verified web search): Meta released **Muse Spark Open** (816B params, 42B active) on Oct 15; Apple's MLX benchmarks: **36.73 tokens/sec on FOUR M5 Ultra Mac Studios**, 24.99 on two (tensor), 15.74 on two (pipeline).
- **CORRECTION vs the scan summary:** "two M5 Ultra Mac Studios at 36+ tokens per second" is **wrong** — 36+ tps needed four machines; two machines = 24.99 tps.
- NVIDIA's own claims (company-supplied, treat skeptically): up to **1 petaflop FP4** AI performance; up to 2.1x faster time-to-first-token vs a MacBook Pro with M5 Pro — not independent benchmarks.

---

## 4. deepfake-candidate — Recruiter catches deepfake job candidate with hand-wave test
- **URL:** https://www.indulgexpress.com/msociety/2026/Oct/18/recruiter-uses-the-john-cena-test-to-catch-a-deepfake-candidate-using-face-filter *(confirmed: specific article, kept)*
- **X media:** none verifiable — @loktar00's Oct 16 post (media `pic.twitter.com/r2HnbwroMV`) is embedded in the article, but its exact x.com status URL could not be recovered.

**Summary:** Michigan-based recruiter Jason (@loktar00) posted a clip on X on October 16 saying he had just interviewed his "first deepfake candidate." After his coworker noticed glitched glasses and a ghosted second frame, Jason asked the candidate to put a hand in front of his face, demonstrating John Cena's "You Can't See Me" wave himself — and the candidate avoided doing so. The clip went viral, sparking fresh debate over AI misuse in remote hiring.

**Facts:**
- Recruiter **Jason** (Michigan-based, posts as @loktar00) shared the clip on X on **October 16**, saying he'd interviewed his "first deepfake candidate."
- Suspected the applicant was using a **live digital filter**; his coworker noticed **glasses looked off** and **"a second ghost frame smeared across his cheeks."**
- Asked the candidate to put a hand in front of his face, demoing **John Cena's "You Can't See Me" wave** himself; the candidate **avoided** putting his hand directly in front of his face — enough to raise Jason's suspicions.
- Mechanics per article: live face-swap tools track a face and lay a digital overlay on top; a hand passing in front can confuse tracking, making the image glitch, blur, or break apart.
- Not the first: **Dawid Moczadlo**, cofounder of Vidoc Security Lab, went viral earlier with footage where a candidate's face kept glitching; when asked to cover his face the candidate ignored the request and the interview was ended.
- A recruiter at the digital studio **Make** had a similar episode: when asked to wave a hand in front of his face, the candidate **left the call**.
- Social media was largely on Jason's side; he wrote: *"In the days of AI we're going to have to be more careful.. and forced to move to in person interviews."*
- Article's own caveat: this is **one recruiter's account of one call**; the candidate is unidentified; avoiding the request isn't proof of a deepfake; security firms warn the hand-wave check won't stay reliable as the tech improves.

---

## 5. shipwreck-debunk — AI-generated iPhone shipwreck videos go viral; Al Jazeera debunks them
- **URL:** https://inshorts.com/en/news/ai-generated-videos-of-iranians-collecting-iphones-go-viral--1792299025001 *(confirmed: specific article; canonical non-AMP variant of the given URL)*
- **X media:** none verifiable — the @Telegraph Oct 16 post is referenced via a shortened t.co link whose exact x.com status URL is unrecoverable.

**Summary:** Videos claiming to show Iranian fishermen retrieving iPhones and perfumes from a sunken cargo ship went viral, gathering millions of views. An **Al Jazeera investigation** found the clips were **AI-generated**. The underlying incident was real — the Singapore-flagged **GFS Pride sank on October 14 after a fire** — but all 21 crew members were rescued safely and none of the viral footage was genuine.

**Facts:**
- Videos claiming to show Iranian fishermen retrieving iPhones and perfumes from a sunken cargo ship went viral; **millions of views**.
- An **Al Jazeera investigation** found the clips were **AI-generated**.
- The **Singapore-flagged GFS Pride sank on October 14 after a fire**; **all 21 crew members rescued safely**.
- Per verified coverage (iranianuae.ae citing Al Jazeera): some viral videos originated from an Instagram account called **Nativora**, which describes itself as a creator of fictional stories/imagery using AI.
- Fabrication signs cited: unnatural movement on water, unusually shaped boxes, distorted/illegible writing, motionless people aboard moving boats.
- The sinking and dispersal of containers/cargo are genuine; the widely circulated images of hundreds of floating/retrieved iPhones are fabricated. No credible evidence the vessel carried iPhones.
- Per verified coverage (The Apple Post, citing Singapore's Maritime and Port Authority): GFS Pride sustained damage and fire before sinking, all 21 evacuated safely; a second Singapore-registered ship, **GFS Giselle**, was struck on October 13–14, suffered hull damage, and reached safe anchorage.
