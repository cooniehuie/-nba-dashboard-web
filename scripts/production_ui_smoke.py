"""Read-only public dashboard smoke; diagnose sleeping, blocked and broken apps."""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL=os.getenv("DASHBOARD_URL","https://huie-dashboard.streamlit.app")
OUT=Path("ui_smoke_artifacts")
OUT.mkdir(exist_ok=True)

def wait_for_app(page, label):
    page.goto(URL,wait_until="domcontentloaded",timeout=120000)
    # Streamlit Community Cloud suspends apps during inactivity.
    # Wake the app where its own wake button is present, then wait for a rerender.
    for attempt in range(3):
        page.wait_for_timeout(3000)
        wake=page.get_by_role("button",name="Yes, get this app back up!")
        if wake.count() and wake.first.is_visible():
            wake.first.click(timeout=15000)
        else:
            alternative=page.get_by_role("button",name="Wake up",exact=False)
            if alternative.count() and alternative.first.is_visible():
                alternative.first.click(timeout=15000)
        try:
            page.get_by_text("Smart Parlay",exact=False).first.wait_for(timeout=40000)
            break
        except PlaywrightTimeout:
            if attempt==2:
                page.screenshot(path=str(OUT/(label+"_not_ready.png")),full_page=True)
                title=page.title()
                visible=page.locator("body").inner_text(timeout=15000)[:1200]
                raise AssertionError("Public dashboard not ready; title="+repr(title)+" visible_text="+repr(visible))
            page.reload(wait_until="domcontentloaded",timeout=120000)
    if page.locator('[data-testid="stException"]').count():
        raise AssertionError("Streamlit exception on "+label)

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1365,"height":900})
        try:
            wait_for_app(page,"desktop")
            page.screenshot(path=str(OUT/"desktop_home.png"),full_page=True)
            nav=page.get_by_text("Smart Parlay",exact=False).first
            nav.click(timeout=30000)
            page.locator("h1").filter(has_text="Smart Parlay").first.wait_for(timeout=90000)
            page.screenshot(path=str(OUT/"desktop_parlay_builder.png"),full_page=True)
            if page.locator('[data-testid="stException"]').count():
                raise AssertionError("Streamlit exception in desktop parlay builder")
            print("Desktop Smart Parlay Builder: rendered")
            mobile=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=1)
            wait_for_app(mobile,"mobile")
            mobile.screenshot(path=str(OUT/"mobile_home.png"),full_page=True)
            print("Mobile public dashboard: rendered")
        finally:
            page.screenshot(path=str(OUT/"final_desktop.png"),full_page=True,timeout=15000)
            browser.close()

if __name__=="__main__":
    try:run()
    except Exception as exc:
        print("Production UI smoke failed:",type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(1)
