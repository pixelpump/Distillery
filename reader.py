import re
import httpx
import trafilatura
from trafilatura.settings import use_config
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import quote
import sys


@dataclass
class Article:
    title: str
    author: Optional[str]
    date: Optional[str]
    text: str
    word_count: int


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def try_extract(url: str, source_name: str = "") -> Tuple[Optional[str], Optional[object]]:
    """Try to download and extract content from a URL. Returns (text, metadata) or (None, None)."""
    source = source_name or url[:50]
    is_jina = "jina.ai" in url
    print(f"[Distillery] Trying {source}...", file=sys.stderr)
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
            print(f"[Distillery]   -> HTTP {resp.status_code}, {len(html)} bytes", file=sys.stderr)
    except Exception as e:
        print(f"[Distillery]   -> Failed: {e}", file=sys.stderr)
        return None, None

    if not html:
        print(f"[Distillery]   -> Empty response", file=sys.stderr)
        return None, None

    # jina.ai returns clean extracted text directly, no need for trafilatura
    if is_jina:
        text = html.strip()
        word_count = len(text.split())
        print(f"[Distillery]   -> jina.ai returned {word_count} words", file=sys.stderr)
        if word_count >= 50:
            return text, None
        return None, None

    config = use_config()
    config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")

    result = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        output_format="txt",
        config=config,
    )

    word_count = len(result.split()) if result else 0
    print(f"[Distillery]   -> Extracted {word_count} words", file=sys.stderr)
    
    if not result:
        return None, None

    metadata = trafilatura.extract_metadata(html)
    return result, metadata


def fetch_article(url: str) -> Article:
    print(f"[Distillery] Fetching article from: {url}", file=sys.stderr)
    
    # 1. Try original URL
    result, metadata = try_extract(url, "original URL")

    # 2. If failed or very short, try 12ft.io (paywall bypass)
    if not result or len(result.split()) < 100:
        bypass_url = f"https://12ft.io/{url}"
        result, metadata = try_extract(bypass_url, "12ft.io")

    # 3. Try jina.ai text extraction service (bypasses paywalls)
    if not result or len(result.split()) < 100:
        jina_url = f"https://r.jina.ai/http://{url}"
        result, metadata = try_extract(jina_url, "jina.ai")

    # 4. Try jina.ai with https
    if not result or len(result.split()) < 100:
        jina_url2 = f"https://r.jina.ai/{url}"
        result, metadata = try_extract(jina_url2, "jina.ai (https)")

    # 5. Try archive.ph (archive.is mirror)
    if not result or len(result.split()) < 100:
        archive_ph_url = f"https://archive.ph/{url}"
        result, metadata = try_extract(archive_ph_url, "archive.ph")

    # 6. Try archive.today
    if not result or len(result.split()) < 100:
        archive_today_url = f"https://archive.today/{url}"
        result, metadata = try_extract(archive_today_url, "archive.today")

    # 7. Try Wayback Machine with different snapshot selectors
    if not result or len(result.split()) < 100:
        # Try most recent snapshot
        wayback_recent = f"https://web.archive.org/web/99999999999999/{quote(url, safe='')}"
        result, metadata = try_extract(wayback_recent, "Wayback Machine")

    # 8. If all failed, raise error
    if not result:
        print(f"[Distillery] All sources failed for: {url}", file=sys.stderr)
        raise ValueError(f"Could not download content from URL: {url}")

    result = re.sub(r'\n{3,}', '\n\n', result).strip()

    # If metadata is None (from jina.ai fallback), extract title from first line
    if metadata is None:
        lines = result.split('\n')
        title = lines[0].strip() if lines else "Untitled Article"
        author = None
        date = None
    else:
        title = (metadata.title if metadata.title else "Untitled Article")
        author = metadata.author
        date = metadata.date

    words = result.split()
    word_count = len(words)

    return Article(
        title=title,
        author=author,
        date=date,
        text=result,
        word_count=word_count,
    )
