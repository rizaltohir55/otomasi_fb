"""
scratch/inspect_composer_trigger.py
Script untuk menemukan link komposer persis di m.facebook.com
"""
import asyncio
import os
import sys
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from utils.browser import setup_browser, login

async def main():
    session_file = os.path.join(BASE_DIR, "session", "fb_session_toto_redo.json")
    if not os.path.exists(session_file):
        session_file = os.path.join(BASE_DIR, "fb_session.json")

    async with async_playwright() as p:
        browser, context, page = await setup_browser(p, session_file=session_file, headless=False)
        await login(page, context, session_file=session_file)

        url = "https://m.facebook.com/groups/1481477745503794/"
        print(f"Navigasi ke {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Print all links containing composer or create post
        info = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a, div[role="button"], button, input, textarea'));
                return links.map((el, i) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        idx: i,
                        tag: el.tagName,
                        href: el.href || '',
                        aria: el.getAttribute('aria-label') || '',
                        text: (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' '),
                        top: Math.round(rect.top),
                        height: Math.round(rect.height)
                    };
                }).filter(x => x.height > 0 && x.top >= 0 && x.top < 1000);
            }
        """)

        print("\n--- ELEMEN INTERAKTIF DI HEADER & TOP FEED ---")
        for item in info:
            if any(k in (item['href'] + item['aria'] + item['text']).lower() for k in ["tulis", "write", "post", "buat", "composer", "foto", "photo", "apa yang"]):
                print(f"[{item['idx']}] {item['tag']} href={item['href']} aria='{item['aria']}' text='{item['text']}' top={item['top']}")

        # Direct navigation check to /composer/
        group_id = "1481477745503794"
        composer_url = f"https://m.facebook.com/composer/?group_id={group_id}"
        print(f"\n⚡ Menguji Navigasi Langsung ke Composer URL: {composer_url}")
        await page.goto(composer_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        print(f"URL setelah goto composer: {page.url}")

        comp_info = await page.evaluate("""
            () => {
                const forms = document.querySelectorAll('form');
                const inputs = document.querySelectorAll('input, textarea, div[role="textbox"], button, div[role="button"]');
                return {
                    formCount: forms.length,
                    formActions: Array.from(forms).map(f => f.action || ''),
                    elements: Array.from(inputs).map(el => ({
                        tag: el.tagName,
                        type: el.type || '',
                        name: el.name || '',
                        role: el.getAttribute('role') || '',
                        aria: el.getAttribute('aria-label') || '',
                        val: el.value || '',
                        text: (el.innerText || '').trim().replace(/\\s+/g, ' ')
                    }))
                };
            }
        """)

        print("\n--- DOKUMEN HALAMAN /COMPOSER/ ---")
        print(f"Form count: {comp_info['formCount']}")
        print(f"Form actions: {comp_info['formActions']}")
        print("Elemen-elemen komposer:")
        for el in comp_info['elements']:
            if el['text'] or el['aria'] or el['name'] or el['type'] or el['val']:
                print(f"  {el['tag']} type={el['type']} name={el['name']} role={el['role']} aria='{el['aria']}' val='{el['val']}' text='{el['text']}'")

        await page.screenshot(path=os.path.join(BASE_DIR, "scratch", "composer_direct_url.png"))
        print(f"\n📸 Screenshot composer direct URL: scratch/composer_direct_url.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
