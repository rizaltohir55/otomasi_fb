from bs4 import BeautifulSoup
import re

with open("scratch/user_activity.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

caption_text = "BARANGKALI ADA YANG PUNYA TlNDER"

for div in soup.find_all("div"):
    text = div.get_text()
    if caption_text in text and len(text) < 1500 and len(text) > 80:
        print("--- FOUND POST CARD DIV ---")
        
        buttons = div.find_all(["button", "input", "textarea"]) + div.find_all("div", attrs={"role": "button"})
        for idx, b in enumerate(buttons, 1):
            role = b.get("role", "")
            aria = b.get("aria-label", "")
            txt = b.get_text().strip()
            print(f"Elem {idx}: tag={b.name}, role={role}, aria={repr(aria)}, text={repr(txt)}")
        break
