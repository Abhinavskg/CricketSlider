"""Shared settings for the @cricketslider automation."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
STATE_FILE = ROOT / "data" / "state.json"

HANDLE = "@cricketslider"
MAX_SLIDES = 8          # hard cap for our carousels
MIN_SLIDES = 2          # Instagram requires at least 2 items in a carousel

# Wikimedia requires a descriptive User-Agent with contact info.
# Set CONTACT (email or URL) as an env var / GitHub variable.
USER_AGENT = f"cricketslider-bot/1.0 ({os.getenv('CONTACT', 'https://instagram.com/cricketslider')})"

# RSS feeds (a dead feed is skipped automatically - add/remove freely).
FEEDS = [
    "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
    "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    "https://timesofindia.indiatimes.com/rssfeeds/4719161.cms",
]

HASHTAGS = ("#cricket #cricketnews #cricketlovers #icc #bcci #t20 #testcricket "
            "#odi #ipl #cricketupdates #cricketslider")
