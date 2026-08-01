import asyncio
import os
import json
import sys
import io

def _fix_encoding():
    for s in ("stdout", "stderr"):
        stream = getattr(sys, s)
        if stream and hasattr(stream, "encoding") and stream.encoding and stream.encoding.lower() != "utf-8":
            try:
                setattr(sys, s, io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))
            except Exception:
                pass

_fix_encoding()

from playwright.async_api import async_playwright

SESSION_FILE = r"d:\Project\otomasiFB\session\fb_session_raden_mas.json"
GROUP_URLS = [
    "https://m.facebook.com/groups/697937093629189/",
    "https://m.facebook.com/groups/2324361217720714/",
    "https://m.facebook.com/groups/1417425938580689/",
]

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE,
            viewport={"width": 412, "height": 915},
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
        )
        page = await context.new_page()
        
        results = []
        for url in GROUP_URLS:
            print(f"Navigating to {url}...")
            try:
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Error loading {url}: {e}")
                continue
                
            info = await page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"], a, input, textarea'));
                const btnDetails = btns.map(b => ({
                    tag: b.tagName,
                    text: (b.innerText || b.value || b.getAttribute('placeholder') || '').trim().replace(/\\s+/g, ' '),
                    aria: b.getAttribute('aria-label') || '',
                    role: b.getAttribute('role') || '',
                    href: b.getAttribute('href') || '',
                    id: b.id || '',
                    className: b.className || '',
                    top: Math.round(b.getBoundingClientRect().top)
                })).filter(b => b.text || b.aria || b.href);
                
                return {
                    url: window.location.href,
                    title: document.title,
                    bodySnippet: document.body.innerText.substring(0, 2000),
                    elements: btnDetails
                };
            }''')
            results.append(info)
            
        with open(r"d:\Project\otomasiFB\scratch\group_debug.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print("Done saving to scratch/group_debug.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
