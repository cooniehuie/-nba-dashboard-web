"""Read-only production UI smoke check. Never authenticates or writes user data."""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL=os.getenv("DASHBOARD_URL","https://huie-dashboard.streamlit.app")
OUT=Path("ui_smoke_artifacts")
OUT.mkdir(exist_ok=True)
def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1365,"height":900})
        page.goto(URL,wait_until="domcontentloaded",timeout=120000)
        try:
            page.get_by_text("Smart Parlay",exact=False).first.wait_for(timeout=180000)
            page.screenshot(path=str(OUT/"desktop_home.png"),full_page=True)
            # Explicit public access check: app should render the navigation
            # without requiring an administrator password.
            nav=page.get_by_text("Smart Parlay",exact=False).first
            nav.wait_for(timeout=30000)
            nav.click(timeout=20000)
            page.locator("h1").filter(has_text="Smart Parlay").first.wait_for(timeout=120000)
            page.screenshot(path=str(OUT/"desktop_parlay_builder.png"),full_page=True)
            errors=page.locator('[data-testid="stException"]')
            if errors.count():raise AssertionError("A Streamlit exception appeared in production")
            print("Desktop production Smart Parlay Builder: rendered")
            mobile=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=1)
            mobile.goto(URL,wait_until="domcontentloaded",timeout=120000)
            mobile.get_by_text("Daily NBA Projections",exact=False).first.wait_for(timeout=180000)
            mobile.screenshot(path=str(OUT/"mobile_home.png"),full_page=True)
            if mobile.locator('[data-testid="stException"]').count():
                raise AssertionError("A Streamlit exception appeared in mobile view")
            print("Mobile production landing page: rendered")
        finally:
            page.screenshot(path=str(OUT/"final_desktop.png"),full_page=True)
            browser.close()
if __name__=="__main__":
    try:run()
    except Exception as exc:
        print("Production UI smoke failed:",type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(1)
