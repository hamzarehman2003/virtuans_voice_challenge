import os
import re
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

# ---------------- CONFIG ----------------
PROFILE_DIR = r"C:\pw_sunmarke_profile"
URLS_TXT = "allowed_urls.txt"
MAX_URLS = 70
PREVIEW_CHARS = 700
CRAWL_DELAY_SECONDS = 10   # from robots.txt Crawl-delay: 10
OUT_DIR = "out"            # saves extracted text files here
# ----------------------------------------

def is_valid_url(u: str) -> bool:
    try:
        p = urlparse(u.strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def load_urls(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    urls = [u for u in urls if is_valid_url(u)]
    # de-dupe preserve order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def slugify(url: str) -> str:
    p = urlparse(url)
    slug = (p.path.strip("/") or "home").replace("/", "_")
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", slug)
    return slug[:150]

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup
    text = main.get_text(" ", strip=True)
    return " ".join(text.split())

def is_blocked(page_url: str, html: str) -> bool:
    h = html.lower()
    return (
        "/.well-known/sgcaptcha/" in page_url
        or "403 - forbidden" in h
        or "access to this page is forbidden" in h
        or "captcha" in h
    )

def goto_stable(page, url: str, timeout_ms=60000):
    """
    Navigate in a stable way:
    - try networkidle
    - fallback to domcontentloaded
    - then small settle wait
    """
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    except PWTimeoutError:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(1500)

def safe_get_title(page, tries=8):
    for _ in range(tries):
        try:
            return page.title()
        except Exception:
            page.wait_for_timeout(400)
    return "[title unavailable due to navigation]"

def main():
    urls = load_urls(URLS_TXT)
    urls = urls[:MAX_URLS] if MAX_URLS else urls
    os.makedirs(OUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=False,
            args=["--disable-extensions", "--no-first-run", "--no-default-browser-check"],
            timeout=60000,
        )

        page = context.new_page()

        # Warm up (helps reduce bot triggers)
        print("Warming up homepage...", flush=True)
        goto_stable(page, "https://www.sunmarke.com/")
        print("Warmup URL:", page.url, flush=True)

        if "/.well-known/sgcaptcha/" in page.url:
            print("⚠️ Hit sgcaptcha on warmup. In the opened browser, refresh / browse normally, then press Enter.", flush=True)
            input()
            goto_stable(page, "https://www.sunmarke.com/")

        print("Starting scrape...\n", flush=True)

        for i, url in enumerate(urls, start=1):
            print("=" * 110)
            print(f"[{i}/{len(urls)}] {url}", flush=True)

            # Navigate with retries (because site may redirect once)
            success = False
            for attempt in range(1, 4):
                try:
                    goto_stable(page, url)
                    html = page.content()

                    if is_blocked(page.url, html):
                        print(f"⚠️ Block detected (attempt {attempt}).", flush=True)
                        print("Current URL:", page.url, flush=True)
                        print("Manually refresh / click a link in the opened browser, wait ~10s, then press Enter to retry...", flush=True)
                        input()
                        continue

                    # If not blocked, extract
                    text = extract_text(html)
                    title = safe_get_title(page)

                    print("Title:", title, flush=True)
                    if text:
                        print("Preview:\n", text[:PREVIEW_CHARS], "\n", flush=True)

                        # Save to file
                        fname = os.path.join(OUT_DIR, f"{i:03d}_{slugify(url)}.txt")
                        with open(fname, "w", encoding="utf-8") as f:
                            f.write(f"URL: {url}\n")
                            f.write(f"TITLE: {title}\n\n")
                            f.write(text)
                        print("Saved:", fname, flush=True)
                    else:
                        print("Preview: [No text extracted]", flush=True)

                    success = True
                    break

                except Exception as e:
                    print(f"Error (attempt {attempt}): {e}", flush=True)
                    page.wait_for_timeout(1200)

            if not success:
                print("❌ Skipped (could not get a clean page after retries)\n", flush=True)

            # Respect robots crawl-delay
            print(f"Sleeping {CRAWL_DELAY_SECONDS}s...\n", flush=True)
            time.sleep(CRAWL_DELAY_SECONDS)

        context.close()

if __name__ == "__main__":
    main()
