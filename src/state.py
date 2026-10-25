"""Persistent memory (data/state.json): what was already posted, so nothing repeats.

posted : article ids          titles : [{"t": headline, "d": "YYYY-MM-DD"}]
images : Wikimedia file titles already used (never reused)
"""
import json
import datetime as dt
from src.config import STATE_FILE


def load() -> dict:
    try:
        s = json.loads(STATE_FILE.read_text())
    except Exception:
        s = {}
    s.setdefault("posted", []); s.setdefault("titles", []); s.setdefault("images", [])
    return s


def remember(ids=(), titles=(), images=()):
    s = load()
    today = dt.date.today().isoformat()
    s["posted"] = (s["posted"] + list(ids))[-1000:]
    s["titles"] = (s["titles"] + [{"t": t, "d": today} for t in titles])[-600:]
    s["images"] = (s["images"] + [i for i in images if i])[-1500:]
    STATE_FILE.write_text(json.dumps(s, indent=1, ensure_ascii=False))
