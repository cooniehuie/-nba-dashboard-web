"""Read-only Sam's Models collector. Never publishes to the dashboard."""
import base64
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = "https://samthemodelman.smmodel.workers.dev/nba/index.html"
HOST = urlparse(ROOT).netloc
OUT = Path("sam_models_output")
MEMBERSHIP_MARKERS = ("members only", "sign in with discord", "login with discord", "access denied", "unauthorized")
SECTIONS = {
    "bankroll": ("bankroll", "safe line"),
    "favorites": ("favorite",),
}


def validate_html(html, label):
    if len(html) < 350:
        raise ValueError(f"{label}: HTML unexpectedly short")
    soup = BeautifulSoup(html, "html.parser")
    visible = soup.get_text(" ", strip=True).lower()
    if any(marker in visible for marker in MEMBERSHIP_MARKERS):
        raise PermissionError(f"{label}: membership/login page returned")
    if len(visible) < 100:
        raise ValueError(f"{label}: no substantial visible content")
    return soup


def allowed(url):
    p = urlparse(url)
    return p.scheme == "https" and p.netloc == HOST and p.path.startswith("/nba/")


def main():
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not (8 <= now.hour <= 15):
        print("Outside 08:00–15:00 Pacific; skipping.")
        return
    secret = os.environ.get("SAM_MODELS_STORAGE_STATE_B64", "")
    if not secret:
        raise RuntimeError("Missing SAM_MODELS_STORAGE_STATE_B64 secret; no pages downloaded")
    # Session state is a credential. Keep it out of repo, artifacts and logs.
    try:
        state = json.loads(base64.b64decode(secret, validate=True))
    except Exception as exc:
        raise RuntimeError("Session secret is not valid base64-encoded Playwright storage state") from exc
    if not isinstance(state, dict) or "cookies" not in state:
        raise RuntimeError("Session state must contain Playwright cookies")
    with tempfile.TemporaryDirectory() as tmp:
        session_path = Path(tmp) / "session.json"
        session_path.write_text(json.dumps(state), encoding="utf-8")
        session_path.chmod(0o600)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(session_path))
            page = context.new_page()
            page.goto(ROOT, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)
            index_html = page.content()
            soup = validate_html(index_html, "schedule")
            links = {}
            for a in soup.select("a[href]"):
                url = urljoin(page.url, a["href"])
                if allowed(url) and url != ROOT:
                    links[url] = a.get_text(" ", strip=True)
            if not links:
                raise ValueError("No NBA section/game links discovered on schedule page")
            collected = {"schedule": (ROOT, index_html)}
            # Follow only NBA links from the schedule and discover additional NBA links
            # from those pages, with a strict cap to avoid crawling the whole site.
            queue = list(links)
            seen = {ROOT}
            while queue and len(seen) < 35:
                url = queue.pop(0)
                if url in seen or not allowed(url):
                    continue
                seen.add(url)
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(800)
                html = page.content()
                title = links.get(url, "") or urlparse(url).path
                child_soup = validate_html(html, title)
                collected[url] = (url, html)
                for a in child_soup.select("a[href]"):
                    target = urljoin(page.url, a["href"])
                    if allowed(target) and target not in seen and target not in queue:
                        if any(word in (a.get_text(" ", strip=True) + " " + target).lower() for word in ("bankroll", "favorite", "props", "game")):
                            queue.append(target)
                if len(collected) >= 25:
                    break
            browser.close()
    found = " ".join(collected.keys()).lower()
    missing = [name for name, patterns in SECTIONS.items() if not any(word in found for word in patterns)]
    if missing:
        raise ValueError("Required sections not discovered: " + ", ".join(missing))
    game_pages = [u for u in collected if u != "schedule" and any(w in u.lower() for w in ("-at-", "_at_", "vs", "props"))]
    if not game_pages:
        raise ValueError("No individual game/props pages discovered; refusing incomplete export")
    # Commit nothing: only upload an artifact after all checks pass.
    OUT.mkdir(exist_ok=True)
    manifest = {"date_pacific": now.date().isoformat(), "checked_at_pacific": now.isoformat(), "pages": []}
    for idx, (key, (url, html)) in enumerate(collected.items()):
        slug = re.sub(r"[^a-z0-9_-]+", "-", urlparse(url).path.rsplit("/", 1)[-1].lower())[:70]
        filename = f"{idx:02d}-{slug or 'schedule'}.html"
        (OUT / filename).write_text(html, encoding="utf-8")
        manifest["pages"].append({"source": url, "file": filename})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Validated {len(collected)} HTML pages; staged artifact only (no dashboard changes).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Collection failed safely: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
