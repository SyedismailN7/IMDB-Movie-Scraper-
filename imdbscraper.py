import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

YEAR_RE = re.compile(r"(19\d{2}|20[0-2]\d)")  # 1900–2029

def extract_year_from_li(li):
    # Try common year containers
    selectors = [
        "span.cli-title-metadata-item",
        "li.cli-title-metadata-item",
        "span.ipc-metadata-list-summary-item__li",
        "span.ipc-inline-list__item",
    ]
    for sel in selectors:
        for el in li.find_elements(By.CSS_SELECTOR, sel):
            m = YEAR_RE.search(el.text)
            if m:
                return int(m.group(1))

    # Try the title link's aria-label/title
    try:
        a = li.find_element(By.CSS_SELECTOR, "a.ipc-title-link-wrapper")
        for attr in ("aria-label", "title"):
            val = a.get_attribute(attr) or ""
            m = YEAR_RE.search(val)
            if m:
                return int(m.group(1))
    except:
        pass

    # Fallback: scan the whole block text
    m = YEAR_RE.search(li.text)
    return int(m.group(1)) if m else 0

def main():
    opts = Options()
    # opts.add_argument("--headless=new")  # keep browser visible for debugging
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    wait = WebDriverWait(driver, 30)

    try:
        url = "https://www.imdb.com/chart/top/"
        driver.get(url)

        # Wait until first batch is loaded
        wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "ul.ipc-metadata-list li.ipc-metadata-list-summary-item")
        ))

        # --- Scroll until all 250 items are loaded ---
        last_count = 0
        while True:
            driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
            time.sleep(1.5)  # give time for new items to load
            items = driver.find_elements(By.CSS_SELECTOR, "ul.ipc-metadata-list li.ipc-metadata-list-summary-item")
            if len(items) == last_count:  # no new items loaded
                break
            last_count = len(items)
            if last_count >= 250:  # safety cutoff
                break

        print(f"Found {len(items)} items after scrolling")

        rows = []
        for idx, li in enumerate(items, start=1):
            # Rank + Title
            h3 = li.find_element(By.CSS_SELECTOR, "h3").text.strip()
            if "." in h3:
                rank_str, title = h3.split(".", 1)
                rank = int(rank_str.strip())
                title = title.strip()
            else:
                rank, title = idx, h3

            year = extract_year_from_li(li)

            # Rating
            try:
                rating_text = li.find_element(By.CSS_SELECTOR, "span.ipc-rating-star--rating").text.strip()
                rating = float(rating_text)
            except:
                rating = 0.0

            rows.append([rank, title, year, rating])

        # Save to CSV
        rows.sort(key=lambda r: r[0])
        df = pd.DataFrame(rows, columns=["Rank", "Title", "Year", "Rating"])
        df.to_csv("imdb_top250.csv", index=False, encoding="utf-8")
        print(f"Scraped {len(df)} movies -> imdb_top250.csv")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
