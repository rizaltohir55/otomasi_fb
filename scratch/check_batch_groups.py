import asyncio
import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.async_api import async_playwright

SESSION_FILE = r"d:\Project\otomasiFB\session\fb_session_kayy_andromeda.json"
GROUPS_FILE = r"d:\Project\otomasiFB\groups.txt"

async def check_group(page, url):
    try:
        resp = await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        title = await page.title()

        # Check DOM elements for Buy/Sell vs Discussion
        detection_data = await page.evaluate('''() => {
            const body = document.body ? document.body.innerText : '';
            
            // Check for Buy/Sell buttons or tabs
            const sell_btns = Array.from(document.querySelectorAll('div[role="button"], a[role="tab"], span'))
                .filter(el => {
                    const txt = (el.innerText || '').trim().toLowerCase();
                    return txt === 'jual sesuatu' || txt === 'sell something' || txt === 'apa yang anda jual?' || txt === 'what are you selling?';
                });

            const discussion_btns = Array.from(document.querySelectorAll('div[role="button"], a[role="tab"], span'))
                .filter(el => {
                    const txt = (el.innerText || '').trim().toLowerCase();
                    return txt.includes('tulis sesuatu') || txt.includes('write something');
                });

            const has_buy_sell_tab = document.querySelector('a[href*="/buy_sell"]') !== null;
            const has_discussion_tab = document.querySelector('a[href*="/discussion"]') !== null;

            return {
                sell_btns_count: sell_btns.length,
                discussion_btns_count: discussion_btns.length,
                has_buy_sell_tab: has_buy_sell_tab,
                has_discussion_tab: has_discussion_tab,
                url: window.location.href
            };
        }''')

        # Logic to classify group type:
        # A group is "JUAL_BELI" if it has "Jual Sesuatu" button OR "Buy and Sell" tab as primary
        # A group is "DISKUSI" if its primary posting interface is discussion ("Tulis sesuatu...")
        is_jual_beli = (detection_data["sell_btns_count"] > 0) or (detection_data["has_buy_sell_tab"] and detection_data["discussion_btns_count"] == 0)

        return {
            "url": url,
            "title": title,
            "is_jual_beli": is_jual_beli,
            "details": detection_data
        }
    except Exception as e:
        return {"url": url, "error": str(e)}

async def main():
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Total groups in groups.txt: {len(urls)}")
    sample_urls = urls[:20]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        buy_sell_list = []
        discussion_list = []

        for i, url in enumerate(sample_urls, 1):
            res = await check_group(page, url)
            if "error" in res:
                print(f"[{i:02d}] ERR | {url} -> {res['error']}")
            else:
                if res["is_jual_beli"]:
                    buy_sell_list.append(url)
                    tag = "JUAL_BELI"
                else:
                    discussion_list.append(url)
                    tag = "DISKUSI"
                clean_title = res['title'].encode('ascii', 'ignore').decode('ascii')
                print(f"[{i:02d}] {tag:10s} | {clean_title[:35]:35s} | Details: {res['details']}")

        print(f"\nResults Summary:")
        print(f"Total checked: {len(sample_urls)}")
        print(f"Jual Beli groups: {len(buy_sell_list)}")
        print(f"Diskusi groups: {len(discussion_list)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
