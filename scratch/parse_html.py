from bs4 import BeautifulSoup
import json

with open("scratch/user_activity.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("Title:", soup.title.string if soup.title else "No title")
print("Total divs:", len(soup.find_all("div")))
print("Total links:", len(soup.find_all("a")))

# Find all divs containing text "BARANGKALI"
for idx, div in enumerate(soup.find_all("div")):
    text = div.get_text()
    if "BARANGKALI" in text or "Tinder" in text or "TlNDER" in text:
        print(f"\nMatch {idx}: class={div.get('class')}, id={div.get('id')}, role={div.get('role')}")
        print("Text preview:", repr(text[:150]))
