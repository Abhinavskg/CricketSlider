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

## Notes
- Instagram needs JPEG images; the Graph API publishing limit is ~100 posts per 24 h – you use 4.
- Photo credits (author + licence) are appended to the caption for CC-BY/CC-BY-SA compliance.
- News text comes from RSS excerpts – the source is credited, but consider rewriting the summaries
  in your own words for original content.
- GitHub may pause scheduled workflows in repos with 60 days of no activity (the state commit keeps it active).
