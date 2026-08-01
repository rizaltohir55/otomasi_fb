"""
scratch/inspect_left_rail.py
Inspect FB homepage DOM left rail & top nav to locate account name exact selectors.
"""
import os
import sys
import json
import asyncio
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from engine.browser import create_stealth_context

async def main():
    session_file = os.path.join(config.SESSION_DIR, "fb_session_bernando_ptr.json")
    if not os.path.exists(session_file):
        session_file = config.SESSION_FILE

    async with async_playwright() as p:
        browser, context = await create_stealth_context(p, session_file=session_file, headless=True)
        page = await context.new_page()

        print(f"Navigating to Facebook with session: {session_file}")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Dump left rail links
        links = await page.evaluate("""() => {
            const results = [];
            // 1. Left rail links
            const leftRail = document.querySelector('div[data-pagelet="LeftRail"]') || document.querySelector('div[role="navigation"]');
            if (leftRail) {
                const anchors = leftRail.querySelectorAll('a');
                anchors.forEach(a => {
                    results.push({
                        text: a.innerText.trim(),
                        aria: a.getAttribute('aria-label'),
                        href: a.getAttribute('href')
                    });
                });
            }
            // 2. Profile link in top header / top right
            const topProfile = document.querySelectorAll('a[href*="profile.php"], a[href*="/me/"]');
            topProfile.forEach(a => {
                results.push({
                    source: 'top_profile',
                    text: a.innerText.trim(),
                    aria: a.getAttribute('aria-label'),
                    href: a.getAttribute('href')
                });
            });

            // 3. User SVG / avatar image aria labels
            const avatars = document.querySelectorAll('svg[aria-label], img[alt]');
            avatars.forEach(el => {
                const label = el.getAttribute('aria-label') || el.getAttribute('alt');
                if (label) {
                    results.push({
                        source: 'avatar',
                        label: label
                    });
                }
            });

            return results;
        }""")

        print("=== DETECTED DOM ELEMENTS ===")
        print(json.dumps(links, indent=2, ensure_ascii=False))

        await page.screenshot(path="scratch/fb_homepage_nav.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
