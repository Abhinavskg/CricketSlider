"""Step 1 - gather, de-duplicate, rank and polish cricket stories.

Usage:  python -m src.fetch_content --session morning|evening
Output: output/content.json

Pipeline: RSS + Google-News league searches + Wikipedia "On This Day"
  -> drop anything already posted (id, similar headline, same match)
  -> score (India first, results/records by session, fresh, good summary)
  -> pick a varied set (league cap, India share) -> punchy rewrite -> content.json
"""
import argparse, datetime as dt, hashlib, html, json, math, os, random, re, time
from urllib.parse import quote
import feedparser, requests
from src import facts, state
from src.config import *

STOP = set("a an the of in on at to for and or as is are was were be by with from after over "
           "vs v his her its their says said say new live update updates news".split())


# ------------------------------------------------------------------ text helpers
def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def shorten(text: str, limit: int = 240) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "))
    return cut[:end + 1] if end > 80 else cut.rsplit(" ", 1)[0] + "…"


def tidy_title(t: str) -> str:
    t = re.sub(r"\s+[-|–—]\s+[^-|–—]{2,40}$", "", t)                 # " - ESPNcricinfo"
    t = re.sub(r"\b(Live|LIVE)( Score| Updates?)?:?\s*", "", t).strip(" :-|")
    return shorten(t, 120)


def tokens(t):  return set(re.findall(r"[a-z0-9]+", t.lower())) - STOP
def jaccard(a, b):  return len(a & b) / max(1, len(a | b))
def teams_in(t):  return {x for x in TEAMS if re.search(rf"\b{re.escape(x)}\b", t)}


def is_dup(item, others, recent_days=2) -> bool:
    """Same article, near-identical headline, or the same match/result covered twice."""
    ta, sa = tokens(item["title"]), teams_in(item["title"])
    for o in others:
        if jaccard(ta, tokens(o["title"])) >= 0.5:
            return True
        recent = o.get("age_days", 0) <= recent_days
        if recent and item["kind"] == o["kind"] == "result" and len(sa & teams_in(o["title"])) >= 2:
            return True
    return False


# ------------------------------------------------------------------ item construction
def make_item(kind, title, summary, source, ts=None, query_league=None):
    title = tidy_title(title)
    summary = clean(summary)
    weak = len(summary) < 45 or jaccard(tokens(summary), tokens(title)) > 0.7   # no real summary
    league = next((lab for lab, rx in LEAGUES if re.search(rx, title + " " + summary, re.I)), None)
    return {"id": hashlib.md5(f"{kind}{title.lower()}".encode()).hexdigest()[:12], "kind": kind,
            "title": title, "summary": "" if weak else shorten(summary), "weak": weak,
            "source": source, "league": league or query_league, "women": bool(WOMEN_RE.search(title + " " + summary)), "india": bool(INDIA_RE.search(title + " " + summary)),
            "age_hours": (time.time() - ts) / 3600 if ts else 24.0}


def classify(title):
    return "result" if RESULT_RE.search(title) else "record" if RECORD_RE.search(title) else "news"


def parse_feed(url, limit=15, **kw):
    try:
        feed = feedparser.parse(url, agent=USER_AGENT)
    except Exception as e:
        print(f"[feed fail] {url}: {e}"); return []
    out = []
    for e in feed.entries[:limit]:
        title = clean(e.get("title", ""))
        ts = time.mktime(e["published_parsed"]) if e.get("published_parsed") else None
        if not title or (ts and time.time() - ts > MAX_AGE_HOURS * 3600):
            continue
        out.append(make_item(classify(title), title, e.get("summary", ""),
                             feed.feed.get("title", "RSS"), ts, **kw))
    return out


def fetch_news():
    items = []
    for url in FEEDS:
        items += parse_feed(url)
    for q in GNEWS_QUERIES:                                           # every league / topic
        url = f"https://news.google.com/rss/search?q={quote(q + ' when:2d')}&hl=en-IN&gl=IN&ceid=IN:en"
        items += parse_feed(url, limit=6)
    print(f"[news] {len(items)} raw items")
    return items


def fetch_on_this_day(today):
    try:
        for section in ("events", "births"):
            r = requests.get(f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/{section}/{today:%m}/{today:%d}",
                             headers={"User-Agent": USER_AGENT}, timeout=30)
            for ev in r.json().get(section, []):
                if re.search(r"\b(cricket|test match|one day international|wicket|ashes|batsman|bowler)\b", ev.get("text", ""), re.I):
                    it = make_item("otd", f"On This Day · {ev['year']}", ev["text"], "Wikipedia")
                    pg = (ev.get("pages") or [{}])[0].get("normalizedtitle")
                    it["id"] = hashlib.md5(f"otd{ev['text']}".encode()).hexdigest()[:12]
                    it["image_hint"] = f"{pg} cricket" if pg else None
                    it["weak"] = False
                    return it
    except Exception as e:
        print(f"[otd] failed: {e}")
    return None


# ------------------------------------------------------------------ ranking & selection
def score(i, session):
    kind = {"morning": {"record": 14, "result": 10, "news": 8, "otd": 0},
            "night": {"result": 16, "record": 12, "news": 6, "otd": 0}}[session][i["kind"]]
    return kind + (35 if i["india"] else 0) + (8 if i["league"] else 0) - (25 if i.get("weak") else 0) - 0.3 * i["age_hours"]


def pick(pool, n):
    """Greedy, varied selection: India share first, then fill, respecting a per-league cap."""
    chosen, per = [], {}
    def ok(i, cap): return i["league"] is None or per.get(i["league"], 0) < cap
    def add(i): chosen.append(i); per[i["league"]] = per.get(i["league"], 0) + 1
    want_india = min(sum(i["india"] for i in pool), math.ceil(n * INDIA_SHARE))
    for i in pool:
        if sum(c["india"] for c in chosen) < want_india and i["india"] and ok(i, LEAGUE_CAP):
            add(i)
    for cap in (LEAGUE_CAP, 99):
        for i in pool:
            if len(chosen) < n and i not in chosen and ok(i, cap):
                add(i)
    return sorted(chosen, key=lambda i: pool.index(i))


# ------------------------------------------------------------------ attractive rewriting
def kicker(i):
    rnd = random.Random(i["id"])
    for rx, opts in KICKERS:
        if re.search(rx, i["title"], re.I):
            return rnd.choice(opts)
    return rnd.choice(KICKER_INDIA if (i["india"] and i["kind"] == "news") else KICKER_BY_KIND[i["kind"]])


def llm_rewrite(items):
    """Optional: rewrite headline/summary in fresh words with Claude (set ANTHROPIC_API_KEY)."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return
    payload = [{"id": i["id"], "kind": i["kind"], "league": i["league"], "headline": i["title"],
                "source_text": i["summary"]} for i in items]
    prompt = ("You write Instagram carousel copy for @cricketslider, an Indian cricket page. For each item return "
              "JSON: id, kicker (max 3 words, ALL CAPS, hype), title (max 12 words, punchy, factual), summary "
              "(max 28 words, in your OWN words). Use ONLY facts present in headline/source_text - never invent "
              "scores, names or numbers; if source_text is empty, restate the headline's meaning briefly. "
              "Reply with a JSON array only.\n\n" + json.dumps(payload))
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=90,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5"), "max_tokens": 2000,
                                "messages": [{"role": "user", "content": prompt}]})
        text = re.sub(r"^```(?:json)?|```$", "", r.json()["content"][0]["text"].strip(), flags=re.M).strip()
        by_id = {x["id"]: x for x in json.loads(text)}
        for i in items:
            if i["id"] in by_id:
                x = by_id[i["id"]]
                i.update(kicker=x["kicker"].upper()[:24], title=x["title"][:120], summary=x["summary"][:260], weak=False)
        print("[llm] rewrote", len(by_id), "items")
    except Exception as e:
        print(f"[llm] skipped: {e}")


def polish(items):
    for i in items:
        i["kicker"] = kicker(i)
    llm_rewrite(items)
    for i in items:                                                    # fallbacks for thin items
        if not i["summary"]:
            i["summary"] = "Developing story - follow @cricketslider for every update from India and world cricket."
        i["image_queries"] = image_queries(i)
        i.pop("weak", None); i.pop("primary", None)


def image_queries(i):
    """Typed queries, most specific first: name -> team -> league -> venue/generic.
    generate_images checks each Commons hit against the query *and* gender, so a women's
    story only gets women's-cricket photos and a men's story never gets one."""
    rnd = random.Random(i["id"] + dt.date.today().isoformat())
    text = i["title"] + " " + i.get("summary", "")
    qs = list(i.get("primary", []))                                    # facts supply their own subject
    names = [n for n in re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b", i["title"]) if not set(n.split()) & NOT_NAME]
    names += [full for sur, full in PLAYERS.items() if re.search(rf"\b{sur}\b", text)]
    for n in list(dict.fromkeys(names))[:2]:
        qs.append({"q": n, "t": "name"})
    for t in [t for t in teams_in(i["title"]) if len(t) > 5][:1]:
        qs.append({"q": f"{t} women cricket team" if i["women"] else f"{t} national cricket team", "t": "team"})
    lq = list(LEAGUE_IMAGE_QUERIES.get(i["league"], [])); rnd.shuffle(lq)
    qs += [{"q": q, "t": "league"} for q in lq[:2]]
    if i["women"]:
        wq = list(WOMEN_IMAGE_QUERIES); rnd.shuffle(wq)
        qs += [{"q": q, "t": "generic"} for q in wq[:4]]
    else:
        vq = list(INDIA_IMAGE_QUERIES if i["india"] else []); rnd.shuffle(vq)
        gq = list(GENERIC_IMAGE_QUERIES); rnd.shuffle(gq)
        qs += [{"q": q, "t": "venue" if re.search(r"Stadium|Ground|Gardens|Oval", q) else "generic"} for q in vq[:3] + gq[:4]]
    return qs


# ------------------------------------------------------------------ main build
COVERS = {"morning": ["GOOD MORNING, CRICKET FANS", "TODAY IN CRICKET", "FIRST BALL OF THE DAY", "MORNING WICKET"],
          "night": ["NIGHT WATCH", "STUMPS! THE DAY IN CRICKET", "THE DAY'S BIG MOMENTS", "NIGHT WRAP"]}
KICK_FACT = ["MIND-BLOWING", "UNBELIEVABLE BUT TRUE", "DID YOU KNOW?", "LEGENDARY STAT", "CRICKET TRIVIA"]


def build_facts(today, posted):
    """2 PM session: 5-6 amazing facts (carousel) + 1 fact (story)."""
    count = random.choice([5, 6])
    items, story = facts.pick_facts(count, posted)
    for n, i in enumerate(items, 1):
        i["label"] = f"FACT {n}"
    story["label"] = "FACT OF THE DAY"
    for i in items + [story]:
        i["kicker"] = random.Random(i["id"]).choice(KICK_FACT)
        i["image_queries"] = image_queries(i)
        i.pop("primary", None)
    return {"session": "afternoon", "date": f"{today:%d %b %Y}".upper(), "title": f"{count} AMAZING CRICKET FACTS",
            "subtitle": "Swipe - number %d will blow your mind" % count, "story": story, "carousel": items}


def build(session):
    today = dt.date.today()
    st = state.load()
    if session == "afternoon":
        return build_facts(today, st["posted"])
    posted = set(st["posted"])
    history = []
    for h in st["titles"]:
        age = (today - dt.date.fromisoformat(h["d"])).days
        if age <= 21:
            history.append({"title": h["t"], "kind": classify(h["t"]), "age_days": age})

    pool, seen_ids = [], set()
    for i in sorted(fetch_news(), key=lambda i: -score(i, session)):    # best version of a story wins
        if i["id"] in posted or i["id"] in seen_ids or is_dup(i, history) or is_dup(i, pool):
            continue
        seen_ids.add(i["id"]); pool.append(i)
    otd = fetch_on_this_day(today)
    if otd and otd["id"] in posted:
        otd = None
    print(f"[pool] {len(pool)} unique fresh stories (India: {sum(i['india'] for i in pool)})")

    # Story: morning = On This Day (else best India story) / evening = best result.
    if session == "morning" and otd:
        story = otd
    elif session == "night":
        story = next((i for i in pool if i["kind"] == "result"), pool[0] if pool else otd)
    else:
        story = pool[0] if pool else None
    if story is None:
        raise SystemExit("No fresh content found - nothing to post.")
    pool = [i for i in pool if i is not story]
    if otd and otd is not story:
        pool.append(otd)
    n = max(1, min(MAX_SLIDES - 2, len(pool)))                         # dynamic page count
    rest = pick(pool, n) if pool else [story]
    polish([story] + [i for i in rest if i is not story])
    lead = max(rest, key=lambda i: score(i, session))                  # dynamic cover teaser
    return {"session": session, "date": f"{today:%d %b %Y}".upper(), "title": random.choice(COVERS[session]),
            "subtitle": "Top story: " + shorten(lead["title"], 70), "story": story, "carousel": rest}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", choices=["morning", "afternoon", "night", "evening"], required=True)
    args = ap.parse_args()
    args.session = "night" if args.session == "evening" else args.session
    OUTPUT.mkdir(exist_ok=True)
    content = build(args.session)
    (OUTPUT / "content.json").write_text(json.dumps(content, indent=2, ensure_ascii=False))
    print(f"Saved: story + {len(content['carousel'])} carousel items")
