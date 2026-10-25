# @cricketslider – automated cricket carousels & stories

Runs on GitHub Actions twice a day (08:00 and 20:00 IST). Each run publishes
**1 Story (1080x1920) + 1 Carousel (2–8 slides, 1080x1080)**.

```
fetch_content.py  ->  generate_images.py  ->  (push to `media` branch)  ->  publish.py
 RSS + Wikipedia       Wikimedia + Pillow        public image URLs         Instagram Graph API
```

## 1. Instagram prerequisites (one-time)
1. Convert @cricketslider to a **Professional (Business/Creator)** account and link it to a Facebook Page.
2. Create an app at developers.facebook.com (type: Business) and add **Instagram Graph API**.
3. Generate a token with `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`.
   Exchange it for a **long-lived token** (60 days). For a non-expiring token, use a Business Manager *System User* token.
4. Get your **Instagram Business Account ID** (`GET /me/accounts` -> page -> `?fields=instagram_business_account`).

## 2. Deploy
1. Create a **public** GitHub repo (raw image URLs must be reachable by Instagram) and push this project.
2. Settings -> Secrets and variables -> Actions:
   - Secrets: `IG_USER_ID`, `IG_ACCESS_TOKEN`
   - Variable (optional): `CONTACT` (your email – used in the Wikimedia User-Agent)
3. Settings -> Actions -> General -> Workflow permissions -> **Read and write**.
4. Actions tab -> *Cricketslider Auto Scheduler* -> **Run workflow** with `dry_run = true`;
   download the `cricketslider-…` artifact to preview the images.
5. Run once with `dry_run = false`. After that the cron schedule takes over.

## 3. Local testing
```bash
pip install -r requirements.txt
export CONTACT="you@example.com"
python -m src.fetch_content --session morning
python -m src.generate_images          # look in output/
DRY_RUN=true MEDIA_BASE_URL=https://example.com python -m src.publish
```

## Customising
- **Schedule**: edit the `cron` lines (UTC). 08:00 IST = `30 2`, 20:00 IST = `30 14`.
- **Sources**: edit `FEEDS` in `src/config.py` (verify each feed URL still works).
- **Look**: colours at the top of `generate_images.py`; drop `Bold.ttf`/`Regular.ttf` in `fonts/`.
- **Housekeeping**: the `media` branch grows over time – delete old `run_*` folders occasionally.

## What's new in v2
- **Coverage:** ~8 direct RSS feeds + Google News searches for 20 topics (IPL, WPL, Ranji, Vijay Hazare, SMAT,
  Duleep, BBL, PSL, SA20, The Hundred, CPL, ILT20, MLC, LPL, County, ICC, Team India, women's cricket, records).
  Each card shows its league tag. ~60% of every carousel is India-focused when India news exists.
- **No repeats:** `data/state.json` stores posted ids, headlines and photo files. A story is skipped if its id was posted,
  its headline is >=50% similar to a recent one, or it is another report of the same match result (within 2 days).
- **Different photos every time:** random pick among all valid Commons hits (never the top result), shuffled query pools
  (Indian stadiums, players, leagues), a file is never reused, a separate photo for the cover, random crop + colour
  grade, and alternating split / full-bleed layouts with accent colours per category.
- **Attractive titles:** a hook line ("WHAT A FINISH!", "TON UP!", "SQUAD ALERT"...) above every headline.
  Optional: add secret `ANTHROPIC_API_KEY` and headlines/summaries are rewritten in fresh words by Claude
  (never adding facts). Without it, rule-based hooks are used.

## v3: three sessions a day (IST)
| Time | Session | Story | Carousel |
|---|---|---|---|
| 08:00 | morning | On This Day (else top India story) | Top headlines, records, squads - random cover title + live "Top story" teaser |
| 14:00 | afternoon | 1 fact of the day | **5-6 amazing cricket facts** (India-heavy, women's cricket included) |
| 20:00 | night | Top match result | Results, records, day wrap |

- **Facts** come from a hand-verified bank in `src/facts.py` (56 facts, none repeated). When it runs low the bot
  recycles the oldest ones - add your own verified entries, or set repo variable `FACTS_AI=true` (+ `ANTHROPIC_API_KEY`)
  to let Claude draft more. AI-drafted facts should be spot-checked before you rely on them.
- **Image matching:** every Wikimedia candidate is checked against its title, description and categories.
  Women's stories only accept women's-cricket photos; men's stories reject them; a player story needs that
  player's name in the file info; non-cricket photos are rejected. If nothing relevant exists, a designed
  navy card is used instead of a wrong photo.
- Cron times are UTC: `30 2`, `30 8`, `30 14`. Manual runs accept `auto | morning | afternoon | night`.

## Notes
- Instagram needs JPEG images; the Graph API publishing limit is ~100 posts per 24 h – you use 4.
- Photo credits (author + licence) are appended to the caption for CC-BY/CC-BY-SA compliance.
- News text comes from RSS excerpts – the source is credited, but consider rewriting the summaries
  in your own words for original content.
- GitHub may pause scheduled workflows in repos with 60 days of no activity (the state commit keeps it active).
