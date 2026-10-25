"""Afternoon session: a bank of verified 'amazing cricket facts' (no scraping, no guessing).

Entry: (category, headline, detail, image-query, flags)
  image-query prefix: n: person  v: venue  t: team  g: generic scene
  flags: i = India angle, w = women's cricket
Add your own entries freely - only use facts you have verified. IDs are hash-based, so
every fact is posted once; when the bank runs out the least-recently posted ones are recycled.
Optional: FACTS_AI=true + ANTHROPIC_API_KEY lets Claude propose extra facts (spot-check these!).
"""
import hashlib, json, os, random, re
import requests

BANK = [
 ("H", "The very first Test match was played in 1877", "Australia beat England by 45 runs at the MCG in March 1877. Charles Bannerman scored 165 and retired hurt - the first Test century.", "v:Melbourne Cricket Ground", ""),
 ("H", "The Ashes were born from a mock obituary", "After Australia won by 7 runs at The Oval on 29 August 1882, a newspaper declared English cricket dead and its 'ashes' would be taken to Australia.", "v:The Oval", ""),
 ("I", "Sachin Tendulkar: 100 international centuries", "51 in Tests and 49 in ODIs. He also scored 34,357 international runs - the most in the history of the game.", "n:Sachin Tendulkar", "i"),
 ("R", "Murali's 800 Test wickets still stand", "Sri Lanka's Muttiah Muralitharan retired with 800 Test wickets - no bowler in history has taken more.", "n:Muttiah Muralitharan", ""),
 ("R", "400 not out: Brian Lara's untouchable Test score", "In 2004 at Antigua, Lara became the first batter to score 400 in a Test innings, against England. It remains the highest score ever.", "n:Brian Lara", ""),
 ("I", "Rohit Sharma has three ODI double centuries", "He is the only player with three, and his 264 against Sri Lanka in 2014 is the highest individual score in ODI history.", "n:Rohit Sharma", "i"),
 ("I", "Yuvraj Singh's six sixes in one over", "At the 2007 T20 World Cup in Durban, Yuvraj hit six sixes off Stuart Broad - and scored the fastest T20I fifty, in just 12 balls.", "n:Yuvraj Singh", "i"),
 ("R", "Bradman missed a 100 Test average by four runs", "Needing just 4 in his final Test innings in 1948, Don Bradman was bowled for a duck and finished with an average of 99.94.", "n:Donald Bradman", ""),
 ("R", "Jim Laker took 19 wickets in a single Test", "In 1956 at Old Trafford, England's Jim Laker took 9 for 37 and 10 for 53 against Australia - a record that still stands.", "n:Jim Laker", ""),
 ("I", "Anil Kumble took all 10 wickets in an innings", "Against Pakistan in Delhi in 1999, Kumble took 10 for 74 - one of only three bowlers in Test history to take all ten.", "n:Anil Kumble", "i"),
 ("I", "India's 1983 World Cup miracle", "Under Kapil Dev, underdog India beat the mighty West Indies by 43 runs at Lord's to win the 1983 World Cup.", "n:Kapil Dev", "i"),
 ("I", "Kapil Dev's 175* rescued India in 1983", "India were 17 for 5 against Zimbabwe at Tunbridge Wells when Kapil played one of the greatest ODI innings ever: 175 not out.", "n:Kapil Dev", "i"),
 ("H", "The first ODI was born from a rained-off Test", "Rain ruined the 1970-71 Melbourne Test, so a one-day match was played on 5 January 1971 - the first ODI. Australia won by 5 wickets.", "v:Melbourne Cricket Ground", ""),
 ("H", "The first T20 international was in 2005", "Australia beat New Zealand by 44 runs at Auckland on 17 February 2005 - and both teams wore retro-style kit for the occasion.", "g:T20 cricket match", ""),
 ("I", "The IPL's very first match had a 158* blast", "Brendon McCullum smashed 158 not out for KKR against RCB on 18 April 2008 - the opening game of the IPL.", "n:Brendon McCullum", "i"),
 ("I", "Shane Warne led Rajasthan Royals to the first IPL title", "Warne's underdogs beat Chennai Super Kings in the 2008 final to become the first IPL champions.", "n:Shane Warne", "i"),
 ("I", "Chris Gayle's 175* is still the IPL record", "Playing for RCB against Pune Warriors in 2013, Gayle hit 175 not out off 66 balls, including a 30-ball century.", "n:Chris Gayle", "i"),
 ("R", "Nepal once scored 314 in a T20I", "At the 2023 Asian Games, Nepal made 314/3 against Mongolia - the highest T20I total ever. Dipendra Singh Airee also hit a 9-ball fifty.", "t:Nepal national cricket team", ""),
 ("R", "New Zealand were bowled out for just 26", "In 1955 at Auckland, New Zealand were dismissed for 26 against England - the lowest total in Test history.", "t:New Zealand national cricket team", ""),
 ("R", "Sri Lanka's 952/6 against India", "In 1997 at Colombo, Sri Lanka declared on 952 for 6, the highest total in Test history. Sanath Jayasuriya made 340.", "n:Sanath Jayasuriya", ""),
 ("H", "Cricket was once an Olympic sport", "Cricket appeared at the 1900 Paris Olympics - and returns at the 2028 Los Angeles Games with T20 events.", "g:cricket trophy", ""),
 ("R", "Shane Warne's 'Ball of the Century'", "His first Ashes delivery in 1993 pitched outside leg stump and turned sharply to bowl Mike Gatting at Old Trafford.", "n:Shane Warne", ""),
 ("I", "Virat Kohli broke Tendulkar's ODI hundreds record", "His 50th ODI century came in the 2023 World Cup semi-final at Wankhede Stadium against New Zealand.", "n:Virat Kohli", "i"),
 ("W", "Belinda Clark scored the first ODI double century", "Australia's Belinda Clark made 229 not out against Denmark at the 1997 Women's World Cup in Mumbai - 13 years before any man did it.", "n:Belinda Clark", "w"),
 ("W", "The Women's World Cup began before the men's", "The first Women's Cricket World Cup was held in England in 1973 - two years before the first men's World Cup in 1975.", "g:women's cricket World Cup", "w"),
 ("W", "Harmanpreet Kaur's 171* stunned Australia", "In the 2017 Women's World Cup semi-final at Derby, Harmanpreet smashed 171 not out off 115 balls to send India into the final.", "n:Harmanpreet Kaur", "iw"),
 ("W", "Mithali Raj: the leading run-scorer in women's ODIs", "India's Mithali Raj finished her career with more than 7,800 runs in women's ODIs - the most by any woman.", "n:Mithali Raj", "iw"),
 ("W", "The first Women's Premier League was won by Mumbai", "The inaugural WPL in 2023 was won by Mumbai Indians, led by Harmanpreet Kaur.", "g:Women's Premier League cricket", "iw"),
 ("I", "Dhoni won every ICC white-ball trophy", "MS Dhoni captained India to the 2007 T20 World Cup, the 2011 World Cup and the 2013 Champions Trophy - the only captain to win all three.", "n:Dhoni", "i"),
 ("I", "Rahul Dravid faced the most balls in Test history", "Dravid faced 31,258 deliveries in Test cricket - more than any other batter, earning him the nickname 'The Wall'.", "n:Rahul Dravid", "i"),
 ("I", "Sunil Gavaskar: first to 10,000 Test runs", "Gavaskar reached the landmark against Pakistan in Ahmedabad in March 1987.", "n:Sunil Gavaskar", "i"),
 ("I", "Tendulkar made his Test debut at just 16", "Sachin Tendulkar debuted against Pakistan in Karachi in 1989, aged 16 years and 205 days.", "n:Sachin Tendulkar", "i"),
 ("R", "AB de Villiers' 31-ball ODI century", "Against West Indies in Johannesburg in 2015, AB de Villiers reached a hundred in 31 balls - the fastest in ODI history.", "n:AB de Villiers", ""),
 ("R", "McCullum's 54-ball Test century", "In his final Test in 2016 at Christchurch, Brendon McCullum scored the fastest Test hundred ever, off 54 balls, against Australia.", "n:Brendon McCullum", ""),
 ("R", "Shoaib Akhtar bowled 161.3 km/h", "Pakistan's Shoaib Akhtar recorded the fastest officially measured delivery, 161.3 km/h, against England at the 2003 World Cup.", "n:Shoaib Akhtar", ""),
 ("R", "England's 498 - the highest ODI total", "England made 498 for 4 against the Netherlands at Amstelveen in June 2022, the highest team score in ODI history.", "t:England cricket team", ""),
 ("I", "The Ranji Trophy is named after a prince", "India's premier domestic tournament, started in 1934-35, honours Ranjitsinhji, who played Test cricket for England. Mumbai have won it more than 40 times.", "g:Ranji Trophy", "i"),
 ("I", "Narendra Modi Stadium is the world's biggest", "The Ahmedabad stadium holds around 132,000 spectators - the largest cricket stadium in the world.", "v:Narendra Modi Stadium", "i"),
 ("I", "India's first Test win took 20 years", "India played their first Test in 1932 but beat England at Madras by an innings and 8 runs only in February 1952.", "g:Indian cricket team", "i"),
 ("I", "VVS Laxman's 281 at Eden Gardens", "In 2001, India followed on against Australia and still won, thanks to Laxman's 281 and Rahul Dravid's 180 - ending Australia's 16-Test winning streak.", "n:VVS Laxman", "i"),
 ("I", "India chased 326 at Lord's in 2002", "Mohammad Kaif and Yuvraj Singh led the NatWest Series final chase, and Sourav Ganguly famously waved his shirt from the balcony.", "v:Lord's Cricket Ground", "i"),
 ("I", "Gabba 2021: India ended Australia's fortress", "India chased 328 to win at the Gabba, ending Australia's 32-year unbeaten run at the ground, and took the series 2-1.", "v:The Gabba", "i"),
 ("I", "Mohammed Siraj bowled Sri Lanka out for 50", "In the 2023 Asia Cup final in Colombo, Siraj took 6 for 21 and India won by 10 wickets in just 6.1 overs.", "n:Mohammed Siraj", "i"),
 ("I", "Rohit Sharma scored five hundreds in one World Cup", "In the 2019 World Cup, Rohit scored five centuries - the most by any batter in a single edition.", "n:Rohit Sharma", "i"),
 ("H", "The first day-night Test used a pink ball", "Australia played New Zealand at Adelaide in November 2015 in the first day-night Test.", "v:Adelaide Oval", ""),
 ("H", "DRS made its Test debut in 2008", "The Decision Review System was first used in a Test between India and Sri Lanka in Colombo in July 2008.", "g:cricket umpire", ""),
 ("R", "Sobers hit the first six sixes in an over", "In 1968, Garfield Sobers hit six sixes in one over for Nottinghamshire. Ravi Shastri matched it for Bombay against Baroda in 1985.", "n:Garfield Sobers", ""),
 ("R", "Ben Stokes' 135* at Headingley", "England needed 359 to beat Australia in the 2019 Ashes Test. Stokes hit 135 not out to complete one of the most dramatic chases ever.", "n:Ben Stokes", ""),
 ("T", "Cricket's most powerful club was founded in 1787", "The Marylebone Cricket Club, based at Lord's, wrote the Laws of Cricket and still owns them today.", "v:Lord's Cricket Ground", ""),
 ("R", "Sangakkara's four consecutive World Cup hundreds", "Kumar Sangakkara hit four straight ODI centuries at the 2015 World Cup - a world record.", "n:Kumar Sangakkara", ""),
 ("I", "India won the 2024 T20 World Cup unbeaten", "India beat South Africa by 7 runs in the final at Barbados in June 2024 without losing a single match in the tournament.", "t:India national cricket team", "i"),
 ("T", "The Ashes urn is tiny", "The Ashes urn stands only about 11 cm tall and rarely leaves the museum at Lord's - teams play for a replica trophy.", "g:The Ashes cricket", ""),
 ("I", "Rishabh Pant became the costliest IPL player", "At the 2025 mega-auction, Lucknow Super Giants bought Pant for Rs 27 crore - the highest price in IPL history at that time.", "n:Rishabh Pant", "i"),
 ("H", "The Hundred launched in 2021", "England's 100-balls-per-side competition debuted in July 2021 with men's and women's tournaments running side by side.", "g:The Hundred cricket", ""),
 ("T", "What is inside a cricket ball?", "A cork core wound tightly with string and covered in leather. A men's ball weighs about 156 to 163 grams.", "g:cricket ball", ""),
 ("I", "Eden Gardens opened in 1864", "Kolkata's Eden Gardens is one of the oldest and most iconic cricket grounds in the world.", "v:Eden Gardens", "i"),
]


def fid(text): return hashlib.md5(text.encode()).hexdigest()[:12]


def _item(e):
    cat, hook, text, q, flags = e
    t, name = q.split(":", 1)
    return {"id": fid(hook), "kind": "fact", "cat": cat, "title": hook, "summary": text, "source": "verified bank",
            "league": None, "india": "i" in flags, "women": "w" in flags, "age_hours": 0,
            "primary": [{"q": name, "t": {"n": "name", "v": "venue", "t": "team", "g": "generic"}[t]}]}


def ai_facts(n, avoid):
    """Optional extra facts from Claude. Treat as drafts: spot-check before relying on them."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not (key and os.getenv("FACTS_AI", "").lower() == "true"):
        return []
    prompt = (f"Give {n} amazing, well-documented cricket facts (India/women's/domestic/world mix). Only include "
              "facts you are certain are true and widely verifiable (famous records, dates, scores). Avoid these topics: "
              f"{'; '.join(avoid[:60])}. JSON array only, items: {{\"hook\": <=9 words, \"text\": <=30 words, "
              "\"query\": <a Wikimedia Commons search phrase for a person/venue>, \"india\": bool, \"women\": bool}}.")
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=90,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5"), "max_tokens": 1500,
                                "messages": [{"role": "user", "content": prompt}]})
        txt = re.sub(r"^```(?:json)?|```$", "", r.json()["content"][0]["text"].strip(), flags=re.M).strip()
        return [_item(("A", x["hook"], x["text"], "n:" + x["query"], ("i" if x.get("india") else "") + ("w" if x.get("women") else "")))
                for x in json.loads(txt)]
    except Exception as e:
        print(f"[facts-ai] skipped: {e}")
        return []


def pick_facts(count, posted):
    """count + 1 facts (last one is for the Story): India-heavy, women's cricket included, mixed categories."""
    posted = list(posted)
    fresh = [_item(e) for e in BANK if fid(e[1]) not in posted]
    if len(fresh) < count + 1:
        fresh += ai_facts(count + 1 - len(fresh), [e[1] for e in BANK])
    if len(fresh) < count + 1:                      # bank exhausted -> recycle least-recently posted
        old = sorted((_item(e) for e in BANK if fid(e[1]) in posted), key=lambda i: posted.index(i["id"]))
        fresh += old[:count + 1 - len(fresh)]
    random.shuffle(fresh)
    chosen, cats = [], {}
    def add(i):
        chosen.append(i); cats[i["cat"]] = cats.get(i["cat"], 0) + 1
    for pred, k in ((lambda i: i["india"], 3), (lambda i: i["women"], 1)):
        for i in fresh:
            if i not in chosen and pred(i) and sum(pred(c) for c in chosen) < k and cats.get(i["cat"], 0) < (3 if i["cat"] == "I" else 2):
                add(i)
    for i in fresh:
        if len(chosen) < count + 1 and i not in chosen and cats.get(i["cat"], 0) < (3 if i["cat"] == "I" else 2):
            add(i)
    for i in fresh:
        if len(chosen) < count + 1 and i not in chosen:
            add(i)
    random.shuffle(chosen)
    return chosen[:count], chosen[count]
