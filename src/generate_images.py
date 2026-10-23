"""Step 2 - fetch open-license photos from Wikimedia Commons and render the cards.

Usage:  python -m src.generate_images
Reads:  output/content.json
Writes: output/carousel/slide_01.jpg ... (1080x1080, 2-8 slides)
        output/story/story.jpg          (1080x1920)
        output/manifest.json            (files + captions + item ids for publish.py)
"""
import json, re, time
from io import BytesIO
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont
from src.config import HANDLE, HASHTAGS, MAX_SLIDES, OUTPUT, ROOT, USER_AGENT
from src.fetch_content import clean

# ---------------------------------------------------------------- palette
NAVY, NAVY2 = (7, 14, 38), (16, 31, 72)
ACCENT, WHITE, MUTED = (255, 184, 28), (255, 255, 255), (172, 184, 214)
PILL_BG = (40, 58, 112)
KIND_LABEL = {"news": "CRICKET NEWS", "result": "MATCH RESULT",
              "record": "RECORD ALERT", "otd": "ON THIS DAY"}

# ---------------------------------------------------------------- fonts
BOLD = [ROOT / "fonts" / "Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
REG = [ROOT / "fonts" / "Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
       "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
       "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf"]


def font(size, bold=True):
    """Drop Bold.ttf / Regular.ttf into fonts/ to use your own typeface."""
    for p in (BOLD if bold else REG):
        if Path(p).exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------- Wikimedia Commons
API = "https://commons.wikimedia.org/w/api.php"
OK_LICENSE = re.compile(r"^(CC[ -]?BY|CC0|Public domain|PD)", re.I)
BAD_TITLE = ("logo", "map", "flag", "scorecard", "icon", "signature", ".svg", ".gif")
_used = set()


def commons_image(query):
    """Return (PIL image, credit string) for the first suitable open-license hit."""
    params = {"action": "query", "format": "json", "generator": "search",
              "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": 12,
              "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1400}
    try:
        r = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        pages = r.json().get("query", {}).get("pages", {})
    except Exception as e:
        print(f"[commons] search failed for '{query}': {e}")
        return None
    for p in sorted(pages.values(), key=lambda p: p.get("index", 999)):
        info = (p.get("imageinfo") or [{}])[0]
        meta, url = info.get("extmetadata", {}), info.get("thumburl")
        lic = meta.get("LicenseShortName", {}).get("value", "")
        if (info.get("mime") not in ("image/jpeg", "image/png") or not url or url in _used
                or info.get("width", 0) < 900 or not OK_LICENSE.match(lic)
                or any(b in p["title"].lower() for b in BAD_TITLE)):
            continue
        try:
            img = Image.open(BytesIO(requests.get(url, headers={"User-Agent": USER_AGENT},
                                                  timeout=60).content)).convert("RGB")
        except Exception:
            continue
        _used.add(url)
        artist = clean(meta.get("Artist", {}).get("value", "Unknown"))[:40]
        return img, f"{artist} ({lic}), Wikimedia Commons"
    return None


def get_photo(queries):
    for q in queries:
        res = commons_image(q)
        time.sleep(0.5)                       # be polite to the API
        if res:
            print(f"[photo] '{q}' -> ok")
            return res
    return None, None


# ---------------------------------------------------------------- drawing helpers
def gradient(size, c1, c2):
    mask = Image.linear_gradient("L").resize(size)
    return Image.composite(Image.new("RGB", size, c2), Image.new("RGB", size, c1), mask)


def fit_cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 3     # bias to top (faces)
    return im.crop((left, top, left + w, top + h))


def base_canvas(size, photo, photo_h, fade_h=320):
    """Navy gradient background with the photo on top, fading smoothly into navy."""
    W, H = size
    bg = gradient(size, NAVY, NAVY2)
    img = bg.copy()
    if photo:
        img.paste(fit_cover(photo, W, photo_h), (0, 0))
        box = (0, photo_h - fade_h, W, photo_h)
        img.paste(bg.crop(box), box[:2], Image.linear_gradient("L").resize((W, fade_h)))
    else:                                                     # decorative fallback
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse((W - 520, -200, W + 200, 520), fill=(255, 184, 28, 22))
        d.ellipse((-260, photo_h - 380, 380, photo_h + 180), fill=(80, 130, 255, 26))
    return img


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def fit_text(d, text, bold, maxw, max_h, start, minimum, spacing=1.22):
    """Shrink font until the text fits max_h; as a last resort, truncate with an ellipsis."""
    for size in range(start, minimum - 1, -2):
        f = font(size, bold)
        lines = wrap(d, text, f, maxw)
        if len(lines) * size * spacing <= max_h:
            return f, lines, size
    f, size = font(minimum, bold), minimum
    lines = wrap(d, text, f, maxw)[:max(1, int(max_h // (minimum * spacing)))]
    lines[-1] = lines[-1].rstrip(" ,.;:") + "…"
    return f, lines, size


def draw_lines(d, x, y, lines, f, size, fill, spacing=1.22):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += int(size * spacing)
    return y


def pill(d, text, x, y, fill, txt, right=False):
    f = font(26)
    w = int(d.textlength(text, font=f)) + 44
    x0 = x - w if right else x
    d.rounded_rectangle((x0, y, x0 + w, y + 52), radius=26, fill=fill)
    d.text((x0 + w / 2, y + 26), text, font=f, fill=txt, anchor="mm")


def footer(d, W, H, y, page=None, total=None):
    d.line((60, y, W - 60, y), fill=(60, 78, 130), width=2)
    d.text((60, y + 48), HANDLE, font=font(34), fill=ACCENT, anchor="lm")
    if page and total and page < total:
        d.text((W - 60, y + 48), "SWIPE  →", font=font(28), fill=MUTED, anchor="rm")


# ---------------------------------------------------------------- card renderers
def render_item(size, item, photo, photo_h, foot_y, page=None, total=None, top=50):
    W, H = size
    img = base_canvas(size, photo, photo_h)
    d = ImageDraw.Draw(img)
    pill(d, KIND_LABEL[item["kind"]], 60, top, ACCENT, NAVY)
    if page:
        pill(d, f"{page}/{total}", W - 60, top, PILL_BG, WHITE, right=True)
    y = photo_h + 10
    d.rounded_rectangle((60, y, 150, y + 8), radius=4, fill=ACCENT)
    maxw = W - 120
    # Title gets ~40% of the free space, summary the rest.
    free = foot_y - y - 60
    f, lines, size_t = fit_text(d, item["title"], True, maxw, free * 0.45, 68, 42)
    y = draw_lines(d, 60, y + 32, lines, f, size_t, WHITE) + 14
    f, lines, size_s = fit_text(d, item["summary"], False, maxw, foot_y - y - 24, 36, 26, 1.35)
    draw_lines(d, 60, y, lines, f, size_s, MUTED, 1.35)
    footer(d, W, H, foot_y, page, total)
    return img


def render_cover(content, photo, total):
    size = (1080, 1080)
    img = base_canvas(size, photo, 1080, fade_h=1)
    img = Image.blend(img, Image.new("RGB", size, NAVY), 0.62)       # darken the photo
    d = ImageDraw.Draw(img)
    pill(d, f"1/{total}", 1020, 50, PILL_BG, WHITE, right=True)
    pill(d, "CRICKET UPDATE", 60, 50, ACCENT, NAVY)
    f, lines, sz = fit_text(d, content["title"], True, 960, 340, 120, 80, 1.1)
    y = draw_lines(d, 60, 400, lines, f, sz, WHITE, 1.1)
    d.rounded_rectangle((60, y + 14, 200, y + 24), radius=5, fill=ACCENT)
    d.text((60, y + 56), content["date"], font=font(40), fill=ACCENT)
    footer(d, 1080, 1080, 980, 1, total)
    return img


def render_outro(total):
    size = (1080, 1080)
    img = base_canvas(size, None, 1080)
    d = ImageDraw.Draw(img)
    pill(d, f"{total}/{total}", 1020, 50, PILL_BG, WHITE, right=True)
    d.text((540, 380), "FOLLOW", font=font(110), fill=WHITE, anchor="mm")
    d.text((540, 510), HANDLE, font=font(84), fill=ACCENT, anchor="mm")
    d.text((540, 630), "for daily cricket updates", font=font(40, False), fill=MUTED, anchor="mm")
    d.text((540, 760), "LIKE  •  COMMENT  •  SHARE  •  SAVE", font=font(30), fill=WHITE, anchor="mm")
    footer(d, 1080, 1080, 980)
    return img


# ---------------------------------------------------------------- main
def main():
    content = json.loads((OUTPUT / "content.json").read_text())
    (OUTPUT / "carousel").mkdir(parents=True, exist_ok=True)
    (OUTPUT / "story").mkdir(parents=True, exist_ok=True)
    credits, files = [], []

    items = content["carousel"][:MAX_SLIDES - 2]        # cover + items + outro <= 8
    total = len(items) + 2

    photos = []
    for it in items:
        ph, cr = get_photo(it["image_queries"])
        photos.append(ph)
        if cr:
            credits.append(cr)

    cover_photo = next((p for p in photos if p), None) or get_photo(["cricket stadium"])[0]
    slides = [render_cover(content, cover_photo, total)]
    for n, (it, ph) in enumerate(zip(items, photos), start=2):
        slides.append(render_item((1080, 1080), it, ph, photo_h=540, foot_y=970, page=n, total=total))
    slides.append(render_outro(total))
    for n, s in enumerate(slides, start=1):
        path = OUTPUT / "carousel" / f"slide_{n:02d}.jpg"
        s.save(path, "JPEG", quality=92)
        files.append(f"carousel/{path.name}")

    # Story: 1080x1920 with Instagram's top/bottom UI safe zones respected.
    st = content["story"]
    sp, scr = get_photo(st["image_queries"])
    if scr:
        credits.append(scr)
    render_item((1080, 1920), st, sp, photo_h=980, foot_y=1600, top=250).save(
        OUTPUT / "story" / "story.jpg", "JPEG", quality=92)

    lines = [f"{content['title'].title()} · {content['date'].title()}", ""]
    lines += [f"{KIND_LABEL[i['kind']].title()}: {i['title']}" for i in items]
    caption = "\n".join(lines) + f"\n\nFollow {HANDLE} for daily cricket updates 🏏"
    if credits:
        caption += "\n\nPhotos: " + "; ".join(dict.fromkeys(credits))
    caption = caption[:2000 - len(HASHTAGS) - 2] + f"\n\n{HASHTAGS}"

    manifest = {"session": content["session"],
                "story": {"file": "story/story.jpg", "ids": [st["id"]]},
                "carousel": {"files": files, "caption": caption, "ids": [i["id"] for i in items]}}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Rendered {len(files)} carousel slides + 1 story")


if __name__ == "__main__":
    main()
