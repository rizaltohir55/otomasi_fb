import asyncio
from playwright.async_api import async_playwright

async def test_js():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Load local HTML file dump
        await page.goto("file:///D:/Project/otomasiFB/scratch/user_activity.html")
        
        caption = "BARANGKALI ADA YANG PUNYA TlNDER"
        tokens = ["barangkali", "punya", "tlnder", "daripada", "beli"]
        
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
                    if (!textClean || textClean.length < 20 || textClean.length > 2500) continue;

                    const exactCaption = cleanCap.length >= 6 && textClean.includes(cleanCap);
                    const tokenMatches = tokens.filter(t => textClean.includes(t)).length;

                    if (exactCaption || tokenMatches >= 2) {
                        candidates.push({
                            element: div,
                            cleanText: textClean,
                            length: textClean.length,
                            tokenMatches: tokenMatches,
                            exactCaption: exactCaption
                        });
                    }
                }

                if (candidates.length === 0) return { found: false };

                // Pick the post container that has suitable length (e.g. 100-1500 chars) and is earliest in DOM
                const validCandidates = candidates.filter(c => c.length >= 80 && c.length <= 1500);
                const best = validCandidates[0] || candidates[0];

                const key = `fb-user-activity-post-${Date.now()}`;
                best.element.setAttribute('data-fb-user-activity-post', key);

                return {
                    found: true,
                    target_selector: `[data-fb-user-activity-post="${key}"]`,
                    snippet: best.cleanText.slice(0, 150),
                    tokenMatches: best.tokenMatches,
                    exactCaption: best.exactCaption
                };
            }
        ''', {"caption": caption, "tokens": tokens})
        
        print("JS Test Result:", result)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_js())
