"""Step 3 - publish the story + carousel through the Instagram Graph API.

The Graph API only accepts PUBLIC image URLs, so the workflow first pushes
output/ to a `media` branch and passes MEDIA_BASE_URL (raw.githubusercontent.com).

Env: IG_USER_ID, IG_ACCESS_TOKEN, MEDIA_BASE_URL, DRY_RUN=true|false
"""
import json, os, sys, time
import requests
from src import state
from src.config import OUTPUT

GRAPH = "https://graph.facebook.com/v21.0"
IG_ID, TOKEN = os.getenv("IG_USER_ID"), os.getenv("IG_ACCESS_TOKEN")
BASE = os.getenv("MEDIA_BASE_URL", "").rstrip("/")
DRY = os.getenv("DRY_RUN", "false").lower() == "true"


def api(method, path, **params):
    params["access_token"] = TOKEN
    r = requests.request(method, f"{GRAPH}/{path}", **{("params" if method == "GET" else "data"): params}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Graph API {r.status_code}: {r.text}")
    return r.json()


def wait_url(url, tries=12):
    """raw.githubusercontent.com can lag a few seconds behind the push."""
    for _ in range(tries):
        try:
            if requests.head(url, timeout=15, allow_redirects=True).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(10)
    raise RuntimeError(f"Image URL not reachable: {url}")


def wait_ready(container_id, tries=30):
    for _ in range(tries):
        status = api("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} failed: {status}")
        time.sleep(4)
    raise RuntimeError(f"Container {container_id} timed out")


def publish_container(cid):
    wait_ready(cid)
    return api("POST", f"{IG_ID}/media_publish", creation_id=cid)["id"]


def post_story(url):
    wait_url(url)
    return publish_container(api("POST", f"{IG_ID}/media", image_url=url, media_type="STORIES")["id"])


def post_carousel(urls, caption):
    children = []
    for u in urls:                                   # 1) one child container per slide
        wait_url(u)
        cid = api("POST", f"{IG_ID}/media", image_url=u, is_carousel_item="true")["id"]
        wait_ready(cid)
        children.append(cid)
    parent = api("POST", f"{IG_ID}/media", media_type="CAROUSEL",     # 2) parent container
                 children=",".join(children), caption=caption)["id"]
    return publish_container(parent)                                  # 3) publish


def main():
    m = json.loads((OUTPUT / "manifest.json").read_text())
    story_url = f"{BASE}/{m['story']['file']}"
    slide_urls = [f"{BASE}/{f}" for f in m["carousel"]["files"]]
    caption = m["carousel"]["caption"]

    if DRY:
        print("DRY RUN - nothing published.\nStory:", story_url)
        print("Slides:", *slide_urls, sep="\n  ")
        print("\nCaption:\n" + caption)
        return
    if not (IG_ID and TOKEN and BASE):
        sys.exit("Missing IG_USER_ID / IG_ACCESS_TOKEN / MEDIA_BASE_URL")

    errors = []
    for name, fn in (("story", lambda: post_story(story_url)),
                     ("carousel", lambda: post_carousel(slide_urls, caption))):
        try:
            print(f"[{name}] published, media id {fn()}")
            part = m[name]                               # remember ids, headlines and photos -> no repeats
            state.remember(part["ids"], part["titles"], part["images"])
        except Exception as e:                        # one failure must not block the other
            print(f"[{name}] FAILED: {e}"); errors.append(name)
    if errors:
        sys.exit(f"Failed: {', '.join(errors)}")


if __name__ == "__main__":
    main()
