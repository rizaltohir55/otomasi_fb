import asyncio
import os
import sys
sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from engine.browser import create_stealth_context
from engine.joiner import check_membership_status
from engine.collector import load_groups

async def find_joined_groups(session_file: str):
    groups = load_groups()
    print(f" Memeriksa status keanggotaan {session_file} pada {len(groups)} grup...")

    async with async_playwright() as p:
        browser, context = await create_stealth_context(p, session_file=session_file, headless=True)
        page = await context.new_page()

        joined_groups = []
        pending_groups = []
        unjoined_groups = []

        try:
            for idx, g_url in enumerate(groups[:15]): # Cek 15 grup pertama
                try:
                    status = await check_membership_status(page, g_url)
                    print(f" [{idx+1}/15] {g_url} -> Status: {status}")
                    if status == "JOINED":
                        joined_groups.append(g_url)
                    elif status == "REQUESTED":
                        pending_groups.append(g_url)
                    else:
                        unjoined_groups.append(g_url)
                except Exception as e:
                    print(f" Error {g_url}: {e}")

            print("\n=== RINGKASAN HASIL ===")
            print(f" JOINED ({len(joined_groups)}):", joined_groups)
            print(f" PENDING ({len(pending_groups)}):", pending_groups)
            print(f" UNJOINED ({len(unjoined_groups)}):", unjoined_groups)

        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(find_joined_groups("fb_session.json"))
