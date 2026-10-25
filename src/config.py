"""Shared settings for the @cricketslider automation."""
import os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
STATE_FILE = ROOT / "data" / "state.json"

HANDLE = "@cricketslider"
MAX_SLIDES, MIN_SLIDES = 8, 2          # carousel = cover + 1..6 items + outro
INDIA_SHARE = 0.6                       # ~60% of each carousel is India-focused (when available)
LEAGUE_CAP = 2                          # max items from one league per carousel (variety)
MAX_AGE_HOURS = 48

# Wikimedia requires a descriptive User-Agent with contact info (set CONTACT env/var).
USER_AGENT = f"cricketslider-bot/2.0 ({os.getenv('CONTACT', 'https://instagram.com/cricketslider')})"

# ------------------------------------------------------------------ sources
# Direct RSS feeds (best summaries). Dead feeds are skipped automatically.
FEEDS = [
    "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
    "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    "https://timesofindia.indiatimes.com/rssfeeds/4719161.cms",
    "https://www.thehindu.com/sport/cricket/feeder/default.rss",
    "https://sportstar.thehindu.com/cricket/feeder/default.rss",
    "https://indianexpress.com/section/sports/cricket/feed/",
    "https://www.hindustantimes.com/feeds/rss/cricket/rssfeed.xml",
    "https://www.news18.com/commonfeeds/v1/eng/rss/cricket.xml",
]
# Google News RSS searches - one per league/topic so *everything* is covered.
# (Out-of-season leagues simply return nothing; `when:2d` keeps results fresh.)
GNEWS_QUERIES = [
    "Team India cricket", "IPL", "Women's Premier League WPL", "India women cricket",
    "Ranji Trophy", "Vijay Hazare Trophy", "Syed Mushtaq Ali Trophy", "Duleep Trophy",
    "Big Bash League", "PSL Pakistan Super League", "SA20", "The Hundred cricket",
    "CPL Caribbean Premier League", "ILT20", "Major League Cricket", "Lanka Premier League",
    "County Championship", "ICC cricket", "Test cricket", "T20 World Cup", "cricket record broken",
]

# ------------------------------------------------------------------ classification
LEAGUES = [  # (label shown on card, regex)
    ("IPL", r"\bIPL\b|Indian Premier League"), ("WPL", r"\bWPL\b|Women'?s Premier League"),
    ("RANJI TROPHY", r"Ranji"), ("DULEEP TROPHY", r"Duleep"), ("VIJAY HAZARE", r"Vijay Hazare"),
    ("SYED MUSHTAQ ALI", r"Syed Mushtaq|SMAT"), ("IRANI CUP", r"Irani Cup"),
    ("WBBL", r"WBBL|Women'?s Big Bash"), ("BBL", r"\bBBL\b|Big Bash"), ("PSL", r"\bPSL\b|Pakistan Super League"), ("SA20", r"\bSA20\b"),
    ("THE HUNDRED", r"The Hundred"), ("CPL", r"\bCPL\b|Caribbean Premier"), ("ILT20", r"ILT20"),
    ("MLC", r"Major League Cricket|\bMLC\b"), ("LPL", r"Lanka Premier|\bLPL\b"),
    ("COUNTY", r"County Championship|Vitality Blast"), ("ASIA CUP", r"Asia Cup"),
    ("ASHES", r"\bAshes\b"), ("ICC", r"World Cup|Champions Trophy|World Test Championship|\bWTC\b|\bICC\b"),
]
INDIA_RE = re.compile(
    r"\b(India|Indian|BCCI|IPL|WPL|Ranji|Duleep|Vijay Hazare|Syed Mushtaq|Kohli|Rohit|Dhoni|Bumrah|"
    r"Shubman|Jadeja|Pant|Hardik|Pandya|Suryakumar|Smriti|Mandhana|Harmanpreet|Ashwin|Shami|Siraj|"
    r"Jaiswal|Gambhir|Tendulkar|Samson|Kuldeep|Arshdeep|Rahul|Shreyas|Mumbai|Chennai|Bengaluru|"
    r"Kolkata|Hyderabad|Rajasthan Royals|Punjab Kings|Gujarat Titans|Lucknow|Delhi Capitals|"
    r"CSK|RCB|KKR|SRH|LSG)\b", re.I)
RESULT_RE = re.compile(r"\b(beat|beats|defeat|defeats|won by|win by|wins|clinch|thrash|crush|"
                       r"seal series|lose|loses|lost to|victory|triumph)\b", re.I)
RECORD_RE = re.compile(r"\b(record|fastest|highest|milestone|historic|first player|first time|"
                       r"double hundred|hat-trick|five-for|most ever|breaks|smashes)\b", re.I)
TEAMS = ["India", "Australia", "England", "Pakistan", "South Africa", "New Zealand", "Sri Lanka",
         "Bangladesh", "West Indies", "Afghanistan", "Zimbabwe", "Ireland", "Netherlands",
         "Chennai Super Kings", "Mumbai Indians", "Royal Challengers", "Kolkata Knight Riders",
         "Sunrisers", "Rajasthan Royals", "Punjab Kings", "Gujarat Titans", "Lucknow Super Giants",
         "Delhi Capitals", "CSK", "RCB", "KKR", "SRH", "LSG"]
NOT_NAME = {"Test", "Series", "World", "Cup", "Premier", "League", "Super", "Over", "Trophy", "Match",
            "Live", "Day", "Players", "Team", "Women", "Men", "Final", "First", "Second", "Third"}

# ------------------------------------------------------------------ attractive "kicker" lines
KICKERS = [  # (regex on headline, options)
    (r"super over|last ball|final over|thriller|nail|by \d runs?|one wicket", ["WHAT A FINISH!", "NAIL-BITER ALERT", "PURE THRILLER"]),
    (r"record|historic|first time|fastest|highest|breaks|smashes", ["HISTORY MADE!", "RECORD BOOKS REWRITTEN", "NEW RECORD ALERT"]),
    (r"century|hundred|\bton\b|double", ["TON UP!", "BATTING MASTERCLASS", "CENTURY ALERT"]),
    (r"five-for|fifer|hat-trick|haul", ["BOWLERS ON FIRE", "WICKET-TAKING SPREE"]),
    (r"injur|ruled out|doubtful|\bmiss(es|ed)?\b", ["BIG BLOW", "INJURY UPDATE"]),
    (r"squad|named|picked|selected|announce|captain", ["SQUAD ALERT", "TEAM NEWS"]),
    (r"auction|retain|trade|released|franchise", ["AUCTION BUZZ", "FRANCHISE WATCH"]),
    (r"retire", ["END OF AN ERA"]),
]
KICKER_BY_KIND = {"result": ["MATCH WRAP", "WHO WON?", "RESULT IN"], "record": ["RECORD ALERT", "MILESTONE MOMENT"],
                  "news": ["JUST IN", "CRICKET BUZZ", "TRENDING NOW"], "otd": ["FLASHBACK", "CRICKET HISTORY", "THROWBACK"]}
KICKER_INDIA = ["INDIA UPDATE", "FROM THE INDIAN CAMP", "DESI CRICKET BUZZ"]

# ------------------------------------------------------------------ Wikimedia image query pools
GENERIC_IMAGE_QUERIES = [
    "cricket bowler delivery", "cricket batsman shot", "cricket fielder catch", "cricket wicketkeeper",
    "cricket celebration", "cricket fans stadium", "cricket trophy", "Test cricket match",
    "T20 cricket match", "cricket umpire", "cricket stumps bails", "cricket ground aerial",
    "Lord's Cricket Ground", "Melbourne Cricket Ground", "The Oval cricket", "Sydney Cricket Ground",
    "Newlands cricket ground", "Galle International Stadium", "Dubai International Cricket Stadium",
]
INDIA_IMAGE_QUERIES = [
    "Eden Gardens", "Wankhede Stadium", "M. Chinnaswamy Stadium", "Narendra Modi Stadium",
    "Arun Jaitley Stadium", "MA Chidambaram Stadium", "Rajiv Gandhi International Cricket Stadium",
    "Indian cricket team", "Indian cricketer batting", "India cricket fans", "Brabourne Stadium",
    "Sawai Mansingh Stadium", "HPCA Stadium Dharamsala", "Green Park Stadium Kanpur", "India women cricket",
]
LEAGUE_IMAGE_QUERIES = {
    "IPL": ["Indian Premier League", "IPL match", "IPL trophy", "IPL cheerleaders crowd"],
    "WPL": ["Women's Premier League cricket", "India women cricket team"],
    "BBL": ["Big Bash League", "Sydney Sixers", "Melbourne Stars"], "PSL": ["Pakistan Super League", "Gaddafi Stadium"],
    "SA20": ["SA20 cricket", "Newlands cricket ground"], "THE HUNDRED": ["The Hundred cricket", "Lord's Cricket Ground"],
    "WBBL": ["Women's Big Bash League"], "CPL": ["Caribbean Premier League", "Kensington Oval"], "RANJI TROPHY": ["Ranji Trophy", "Indian domestic cricket"],
    "VIJAY HAZARE": ["Vijay Hazare Trophy", "Indian domestic cricket"], "SYED MUSHTAQ ALI": ["Syed Mushtaq Ali Trophy"],
    "DULEEP TROPHY": ["Duleep Trophy"], "ASIA CUP": ["Asia Cup cricket"], "ASHES": ["The Ashes cricket", "Ashes urn"],
    "ICC": ["ICC Cricket World Cup", "ICC trophy"], "COUNTY": ["County Championship cricket"],
    "ILT20": ["International League T20"], "MLC": ["Major League Cricket"], "LPL": ["Lanka Premier League"],
}

HASHTAGS = ("#cricket #cricketnews #indiancricket #teamindia #ipl #bcci #t20 #testcricket "
            "#cricketlovers #cricketupdates #cricketslider")

# ------------------------------------------------------------------ women's cricket + player lookup
WOMEN_RE = re.compile(r"\b(women|woman|women's|womens|WPL|WBBL|Smriti|Mandhana|Harmanpreet|Shafali|Jemimah|"
                      r"Mithali|Jhulan|Renuka|Deepti|Perry|Mooney|Sciver|Lanning|Ellyse|Beth|Belinda)\b", re.I)
WOMEN_IMAGE_QUERIES = ["women's cricket match", "women cricketer batting", "women cricketer bowling",
                       "women's cricket team celebration", "women's T20 cricket", "India women cricket team",
                       "women's cricket World Cup"]
# Headline surnames -> full names (single-word headlines like "Kohli hits ton" still get the right photo)
PLAYERS = {"Kohli": "Virat Kohli", "Rohit": "Rohit Sharma", "Dhoni": "Dhoni", "Bumrah": "Jasprit Bumrah",
           "Shubman": "Shubman Gill", "Jadeja": "Ravindra Jadeja", "Pant": "Rishabh Pant",
           "Hardik": "Hardik Pandya", "Suryakumar": "Suryakumar Yadav", "Smriti": "Smriti Mandhana",
           "Mandhana": "Smriti Mandhana", "Harmanpreet": "Harmanpreet Kaur", "Shafali": "Shafali Verma",
           "Jemimah": "Jemimah Rodrigues", "Ashwin": "Ravichandran Ashwin", "Shami": "Mohammed Shami",
           "Siraj": "Mohammed Siraj", "Jaiswal": "Yashasvi Jaiswal", "Gambhir": "Gautam Gambhir",
           "Samson": "Sanju Samson", "Kuldeep": "Kuldeep Yadav", "Arshdeep": "Arshdeep Singh",
           "Shreyas": "Shreyas Iyer", "Babar": "Babar Azam", "Smith": "Steve Smith", "Root": "Joe Root",
           "Stokes": "Ben Stokes", "Williamson": "Kane Williamson", "Cummins": "Pat Cummins",
           "Starc": "Mitchell Starc", "Warner": "David Warner", "Rabada": "Kagiso Rabada",
           "Perry": "Ellyse Perry", "Mooney": "Beth Mooney"}
