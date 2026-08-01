import asyncio
from playwright.async_api import async_playwright

async def test_ultimate():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("file:///D:/Project/otomasiFB/scratch/user_activity.html")
        
        caption = "BARANGKALI ADA YANG PUNYA TlNDER daripada ga dipake saya beli 50-350k minimal pembuatan 2025 Langsung dm/WA 087767396700 rekber on"
        tokens = ["barangkali", "punya", "tlnder", "daripada", "beli", "rekber"]
        
        result = await page.evaluate('''
            (args) => {
                const cleanStr = val => (val || '')
                    .replace(/[\\u200e\\u200f\\u200b-\\u200d\\ufeff]/g, '')
                    .toLowerCase()
                    .replace(/[^\\w\\s]/g, ' ')
                    .replace(/\\s+/g, ' ')
                    .trim();

                const cleanCap = cleanStr(args.caption || '');
                const tokens = args.tokens || [];

                const allDivs = Array.from(document.querySelectorAll('div'));
                const candidates = [];

                for (const div of allDivs) {
                    const textClean = cleanStr(div.innerText || '');
                    if (!textClean || textClean.length < 40 || textClean.length > 2500) continue;

                    const exactCaption = cleanCap.length >= 6 && textClean.includes(cleanCap.slice(0, 40));
                    const tokenMatches = tokens.filter(t => textClean.includes(t)).length;

                    const isPostCard = /suka|like|komentar|comment|menit|jam|hari|baru saja/i.test(div.innerText || '') || exactCaption || tokenMatches >= 1;

                    if (isPostCard) {
                        candidates.push({
                            element: div,
                            cleanText: textClean,
                            length: textClean.length,
                            tokenMatches: tokenMatches,
                            exactCaption: exactCaption
                        });
                    }
                }

                if (candidates.length === 0) {
                    for (const div of allDivs) {
                        const text = (div.innerText || '').trim();
                        if (text.length > 50 && text.length < 1500) {
                            candidates.push({ element: div, cleanText: cleanStr(text), length: text.length, tokenMatches: 0, exactCaption: false });
                            break;
                        }
                    }
                }

                if (candidates.length === 0) return { found: false };

                candidates.sort((a, b) => {
                    if (a.exactCaption && !b.exactCaption) return -1;
                    if (!a.exactCaption && b.exactCaption) return 1;
                    if (a.tokenMatches !== b.tokenMatches) return b.tokenMatches - a.tokenMatches;
                    return a.length - b.length;
                });

                const best = candidates[0];
                const key = `fb-user-activity-post-${Date.now()}`;
                best.element.setAttribute('data-fb-user-activity-post', key);

                return {
                    found: true,
                    target_selector: `[data-fb-user-activity-post="${key}"]`,
                    reason: best.exactCaption ? 'Caption presisi cocok di Log Aktivitas User' : (best.tokenMatches > 0 ? `${best.tokenMatches} kata kunci cocok di Log Aktivitas User` : 'Postingan teratas di Log Aktivitas User'),
                    snippet: best.cleanText.slice(0, 150)
                };
            }
        ''', {"caption": caption, "tokens": tokens})
        
        print("Ultimate Evaluator Result:", result)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ultimate())
