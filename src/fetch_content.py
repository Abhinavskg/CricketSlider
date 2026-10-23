"""Step 1 - gather cricket news, results, records and 'On This Day' facts.

Usage:  python -m src.fetch_content --session morning|evening
Output: output/content.json
"""
import argparse, hashlib, html, json, re, time
import datetime as dt
import feedparser, requests
from src.config import FEEDS, MAX_SLIDES, OUTPUT, STATE_FILE, USER_AGENT

RESULT_RE = re.compile(r"\b(beat|beats|defeat|defeats|won by|win by|wins|clinch|thrash|"
                       r"crush|seal series|loses|lost to|victory)\b", re.I)
RECORD_RE = re.compile(r"\b(record|fastest|highest|milestone|historic|first player|"
                       r"first time|double hundred|hat-trick|five-for|most ever)\b", re.I)
OTD_RE = re.compile(r"\b(cricket|test match|one day international|wicket|ashes|batsman|bowler|t20)\b", re.I)
TEAMS = ["India", "Australia", "England", "Pakistan", "South Africa", "New Zealand",
         "Sri Lanka", "Bangladesh", "West Indies", "Afghanistan", "Zimbabwe", "Ireland"]

# Used only when Wikipedia has no cricket entry for today's date (MM-DD).
FALLBACK_FACTS = {
    "03-15": (1877, "The first-ever Test match began at the MCG, Melbourne - Australia v England."),
    "08-29": (1882, "Australia beat England by 7 runs at The Oval, giving birth to The Ashes."),
    "08-27": (1908, "Sir Donald Bradman, cricket's greatest batter, was born in Cootamundra."),
    "01-05": (1971, "The first official One Day International was played at the MCG."),
    "02-24": (2010, "Sachin Tendulkar became the first man to score an ODI double century (200*)."),
}


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def shorten(text: str, limit: int = 240) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "))
    return cut[:end + 1] if end > 80 else cut.rsplit(" ", 1)[0] + "…"


def image_queries(title: str) -> list:
    """Build Wikimedia Commons search phrases, most specific first."""
    qs = [f"{n} cricket" for n in re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b", title)[:2]]
    qs += [f"{t} national cricket team" for t in TEAMS if t in title][:2]
    return qs + ["cricket match", "cricket stadium"]


def make_item(kind, title, summary, source, extra_q=None):
    uid = hashlib.md5(f"{kind}{title}".encode()).hexdigest()[:12]
    return {"id": uid, "kind": kind, "title": title, "summary": shorten(summary or title),
            "source": source, "image_queries": (extra_q or []) + image_queries(title)}


def fetch_news() -> list:
    items, seen = [], set()
    cutoff = time.time() - 48 * 3600
    for url in FEEDS:
        try:
            feed = feedparser.parse(url, agent=USER_AGENT)
        except Exception as e:
            print(f"[feed fail] {url}: {e}"); continue
        for e in feed.entries[:15]:
            title = clean(e.get("title", ""))
            if not title or title.lower() in seen:
                continue
            ts = e.get("published_parsed")
            if ts and time.mktime(ts) < cutoff:
                continue
            seen.add(title.lower())
            kind = "result" if RESULT_RE.search(title) else "record" if RECORD_RE.search(title) else "news"
            items.append(make_item(kind, title, clean(e.get("summary", "")), feed.feed.get("title", "RSS")))
    print(f"[news] {len(items)} fresh items")
    return items


def fetch_on_this_day(today: dt.date):
    """Cricket entry from Wikipedia's On-This-Day feed (events + births), with fallback."""
    try:
        for section in ("events", "births"):
            r = requests.get(f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/{section}/"
                             f"{today:%m}/{today:%d}", headers={"User-Agent": USER_AGENT}, timeout=30)
            for ev in r.json().get(section, []):
                if OTD_RE.search(ev.get("text", "")):
                    pages = ev.get("pages") or [{}]
                    q = [f"{pages[0]['normalizedtitle']} cricket"] if pages[0].get("normalizedtitle") else []
                    return make_item("otd", f"On This Day · {ev['year']}", clean(ev["text"]), "Wikipedia", q)
    except Exception as e:
        print(f"[otd] failed: {e}")
    fact = FALLBACK_FACTS.get(f"{today:%m-%d}")
    return make_item("otd", f"On This Day · {fact[0]}", fact[1], "Wikipedia") if fact else None


def load_posted() -> set:
    try:
        return set(json.loads(STATE_FILE.read_text())["posted"])
    except Exception:
        return set()


def build(session: str) -> dict:
    today = dt.date.today()
    posted = load_posted()
    news = [i for i in fetch_news() if i["id"] not in posted]
    otd = fetch_on_this_day(today)
    if otd and otd["id"] in posted:
        otd = None

    # Editorial priority differs by session.
    prio = {"morning": ["record", "result", "news"], "evening": ["result", "record", "news"]}[session]
    news.sort(key=lambda i: prio.index(i["kind"]))

    otd_list = [otd] if otd else []
    pool = otd_list + news if session == "morning" else news + otd_list
    if not pool:
        raise SystemExit("No fresh content found - nothing to post.")

    story = pool[0]                                   # morning: On This Day / evening: top result
    rest = [i for i in pool if i is not story][:MAX_SLIDES - 2] or [story]
    title = "MORNING BRIEFING" if session == "morning" else "EVENING WRAP"
    return {"session": session, "date": f"{today:%d %b %Y}".upper(), "title": title,
            "story": story, "carousel": rest}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", choices=["morning", "evening"], required=True)
    args = ap.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    content = build(args.session)
    (OUTPUT / "content.json").write_text(json.dumps(content, indent=2, ensure_ascii=False))
    print(f"Saved content: story + {len(content['carousel'])} carousel items")
