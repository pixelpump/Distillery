import re
import httpx
import trafilatura
from trafilatura.settings import use_config
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import quote
import sys
import time
import errno
import subprocess
import json
import os


def safe_print(message: str, file=sys.stderr):
    """Print to stderr, suppressing broken pipe errors."""
    try:
        print(message, file=file, flush=True)
    except (BrokenPipeError, IOError) as e:
        if e.errno != errno.EPIPE:
            raise


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


# Common patterns to remove from jina.ai output
JINA_SKIP_PATTERNS = [
    r'^\[?skip\s+to\s+content\]?',
    r'^\[?skip\s+to\s+site\s+index\]?',
    r'^\[?skip\s+advertisement\]?',
    r'^search\s*&\s*section\s*navigation',
    r'^search\s*$',
    r'^section\s*navigation\s*$',
    r'^subscribe\s+for\s*\$?\d+',
    r'^log\s*in\s*$',
    r'^sign\s*in\s*$',
    r'^advertisement\s*$',
    r'^supported\s*by\s*$',
    r'^\[?image\s*\d+.*\]',
    r'^\*?\s*share\s+full\s+article\s*\*?',
    r'^read\s+\d+\s+comments',
    r'^\d+\s*$',
    r'^\*\s*\d+\s*\*$',
    r'^see\s+more\s+of\s+our\s+coverage',
    r'^encuentra\s+más\s+de',
    r'^add\s+.*\s+on\s+google',
    r'^agrega\s+.*\s+en\s+google',
    r'^war\s+in\s+the\s+middle\s+east',
    r'^\*\s*live\s*\*',
    r'^related\s+content',
    r'^\*\s*$',
    r'^see\s+more\s+on:',
    r'^u\.s\.\s*politics',
    r'^donald\s+trump',
    r'^(friday|monday|tuesday|wednesday|thursday|saturday|sunday),\s+\w+\s+\d+',
    r'^today.s\s+paper',
    r'^\[?\s*\]\(',  # Empty markdown links
    r'^\[\s*\]\(https?://',  # Image-only markdown links
    # CTV News / General news site patterns
    r'^sections\s*$',
    r'^news\s+service\s*$',
    r'^markdown\s+content\s*$',
    r'^url\s+source\s*:?\s*https?://',
    r'^published\s+time\s*:',
    r'^updated\s*:',
    r'^\!\[image\s*\d*\]',  # Markdown images: ![Image...]
    r'^\[\!\[image',  # Nested markdown images: [![Image...](...)](...)
    r'^\[.*logo.*\]\(https?://',  # Logo links with "logo" in text
    r'^\[local\]\(https?://',
    r'^\[watch\]\(https?://',
    r'^\[trade\s+war\]\(https?://',
    r'^\[in\s+pictures\]\(https?://',
    r'^\[ctv\s+your\s+morning\]\(https?://',
    r'^\[shopping\s+trends\]\(https?://',
    r'^\[ctv\s+news\s+now\]\(https?://',
    r'^\[the\s+baguette\s+faces',  # Related article previews
    r'^\[is\s+allergy\s+season',
    r'^\[climate\s+and\s+environment\]',
    r'^\*\s*\*\s*\*',  # Horizontal rules: * * *
    r'^-{3,}',  # Horizontal rules: ---
    r'^markdown\s+content\s*:?\s*$',  # jina.ai artifact
    r'^title\s*:\s*',  # Duplicate title prefix from jina.ai
]

# Error patterns that indicate jina.ai failed to extract content
JINA_ERROR_PATTERNS = [
    r'error\s*\d+\s*:\s*\d+',  # "error 403: Forbidden"
    r'returned\s+error\s+\d+',  # "returned error 403"
    r'\b403\s+forbidden\b',
    r'\b404\s+not\s+found\b',
    r'\b429\s+too\s+many\s+requests\b',
    r'\b500\s+internal\s+server\s+error\b',
    r'\b502\s+bad\s+gateway\b',
    r'\b503\s+service\s+unavailable\b',
    r'captcha',
    r'requiring\s+captcha',
    r'unauthorized\s+to\s+access',
    r'access\s+denied',
    r'could\s+not\s+extract',
    r'failed\s+to\s+fetch',
]


def try_extract(url: str, source_name: str = "", delay: float = 0) -> Tuple[Optional[str], Optional[object]]:
    """Try to download and extract content from a URL. Returns (text, metadata) or (None, None)."""
    source = source_name or url[:50]
    is_jina = "jina.ai" in url
    safe_print(f"[Distillery] Trying {source}...")
    
    # Add delay for rate-limited sources
    if delay > 0:
        time.sleep(delay)
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
            safe_print(f"[Distillery]   -> HTTP {resp.status_code}, {len(html)} bytes")
    except Exception as e:
        safe_print(f"[Distillery]   -> Failed: {e}")
        return None, None

    if not html:
        safe_print("[Distillery]   -> Empty response")
        return None, None

    # jina.ai returns clean extracted text directly, no need for trafilatura
    if is_jina:
        text = html.strip()
        # Check if jina.ai returned an error message
        if is_jina_error(text):
            safe_print("[Distillery]   -> jina.ai returned error content")
            return None, None
        text = clean_jina_output(text)
        word_count = len(text.split())
        safe_print(f"[Distillery]   -> jina.ai returned {word_count} words (cleaned)")
        if word_count >= 20:
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
    safe_print(f"[Distillery]   -> Extracted {word_count} words")
    
    if not result:
        return None, None

    metadata = trafilatura.extract_metadata(html)
    return result, metadata


def is_jina_error(text: str) -> bool:
    """Check if jina.ai returned an error message instead of article content."""
    text_lower = text.lower()
    for pattern in JINA_ERROR_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def clean_jina_output(text: str) -> str:
    """Clean jina.ai output by removing navigation, ads, and cruft."""
    lines = text.split('\n')
    cleaned_lines = []
    skip_patterns = [re.compile(p, re.IGNORECASE) for p in JINA_SKIP_PATTERNS]
    
    # Also skip URL-only lines (navigation links)
    url_only_pattern = re.compile(r'^\[?[^\]]+\]?\(https?://[^)]+\)$', re.IGNORECASE)
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        # Skip if matches any pattern
        if any(p.match(line_stripped) for p in skip_patterns):
            continue
            
        # Skip URL-only lines (bare navigation links)
        if url_only_pattern.match(line_stripped):
            continue
            
        # Skip lines that are just "*" or numbers
        if line_stripped in ['*', '**', '***'] or line_stripped.isdigit():
            continue
            
        cleaned_lines.append(line_stripped)
    
    return '\n\n'.join(cleaned_lines)


def extract_with_dom_distiller(html_content: str) -> Optional[Tuple[str, str]]:
    """Extract content using Chrome DOM Distiller binary. Returns (title, content) or None."""
    binary_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "binaries", "dom-distiller")
    
    if not os.path.exists(binary_path):
        safe_print(f"[Distillery]   -> DOM Distiller binary not found at {binary_path}")
        return None
    
    try:
        # Pass HTML via stdin to avoid command line length limits
        proc = subprocess.run(
            [binary_path, "-html", html_content],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if proc.returncode != 0:
            safe_print(f"[Distillery]   -> DOM Distiller failed: {proc.stderr}")
            return None
        
        data = json.loads(proc.stdout)
        
        if data.get("error"):
            safe_print(f"[Distillery]   -> DOM Distiller error: {data['error']}")
            return None
        
        title = data.get("title", "")
        content = data.get("content", "")
        
        if content and len(content.split()) >= 20:
            # Format output with title if available
            if title:
                full_text = f"{title}\n\n{content}"
            else:
                full_text = content
            return (title, full_text)
        
        return None
    except subprocess.TimeoutExpired:
        safe_print("[Distillery]   -> DOM Distiller timed out")
        return None
    except json.JSONDecodeError as e:
        safe_print(f"[Distillery]   -> DOM Distiller JSON parse error: {e}")
        return None
    except Exception as e:
        safe_print(f"[Distillery]   -> DOM Distiller exception: {e}")
        return None


def fetch_article(url: str) -> Article:
    safe_print(f"[Distillery] Fetching article from: {url}")
    
    # Fetch original URL
    html_content = None
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html_content = resp.text
            safe_print(f"[Distillery]   -> HTTP {resp.status_code}, {len(html_content)} bytes")
    except Exception as e:
        safe_print(f"[Distillery]   -> Failed to fetch: {e}")
    
    result = None
    metadata = None
    
    # 1. Try trafilatura on original URL
    trafilatura_result = None
    trafilatura_metadata = None
    if html_content:
        safe_print("[Distillery] Trying trafilatura...")
        config = use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        trafilatura_result = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            output_format="txt",
            config=config,
        )
        if trafilatura_result:
            word_count = len(trafilatura_result.split())
            safe_print(f"[Distillery]   -> Trafilatura extracted {word_count} words")
            trafilatura_metadata = trafilatura.extract_metadata(html_content)
    
    # 2. Try Chrome DOM Distiller on the original HTML (fast, local, Chrome Reader Mode parity)
    # Always run DOM Distiller to compare quality with trafilatura
    dom_result = None
    dom_title = None
    if html_content:
        safe_print("[Distillery] Trying DOM Distiller (Chrome Reader Mode algorithm)...")
        dd_result = extract_with_dom_distiller(html_content)
        if dd_result:
            dom_title, dom_content = dd_result
            dom_word_count = len(dom_content.split())
            safe_print(f"[Distillery]   -> DOM Distiller extracted {dom_word_count} words")
            dom_result = dom_content
    
    # Common shopping/sidebar keywords to detect bad extractions
    shopping_keywords = ['shopping', 'advent calendar', 'amazon', 'gifts', 'best']
    
    # Choose best result: prefer DOM Distiller if it got significantly more content
    # or if trafilatura result looks like sidebar cruft (short, contains shopping keywords)
    result = trafilatura_result
    metadata = trafilatura_metadata
    
    if dom_result:
        dom_words = len(dom_result.split())
        traf_words = len(trafilatura_result.split()) if trafilatura_result else 0
        
        # Prefer DOM Distiller if:
        # 1. It got significantly more words (20%+ more) AND has minimum viable content
        # 2. Trafilatura got sidebar content (shopping keywords in short content) AND DOM has minimum content
        is_traf_sidebar = (traf_words < 300 and trafilatura_result and
                          any(kw in trafilatura_result.lower() for kw in shopping_keywords))
        
        # DOM Distiller needs at least 100 words to be considered a valid alternative
        dom_is_viable = dom_words >= 100
        
        if (dom_is_viable and dom_words > traf_words * 1.2) or (is_traf_sidebar and dom_is_viable) or (traf_words < 100 and dom_is_viable):
            safe_print(f"[Distillery] Using DOM Distiller result ({dom_words} vs {traf_words} words)")
            result = dom_result
            metadata = type('obj', (object,), {'title': dom_title, 'author': None, 'date': None})()
        else:
            safe_print(f"[Distillery] Using trafilatura result ({traf_words} vs {dom_words} words)")

    # 3. If failed, very short, or detected sidebar content, try 12ft.io (paywall bypass)
    # Also treat sidebar content as insufficient even if word count > 100
    is_sidebar = result and len(result.split()) < 300 and any(kw in result.lower() for kw in shopping_keywords)
    if not result or len(result.split()) < 100 or is_sidebar:
        bypass_url = f"https://12ft.io/{url}"
        result, metadata = try_extract(bypass_url, "12ft.io")
        # Try DOM Distiller on 12ft result too
        if result and len(result.split()) >= 100:
            try:
                with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
                    resp = client.get(bypass_url)
                    if resp.status_code == 200:
                        dd_result = extract_with_dom_distiller(resp.text)
                        if dd_result and len(dd_result[1].split()) > len(result.split()) * 0.8:
                            # DOM Distiller got comparable or better content
                            title, result = dd_result
                            metadata = type('obj', (object,), {'title': title, 'author': None, 'date': None})()
            except Exception:
                pass

    # 4. Try jina.ai text extraction service (bypasses paywalls)
    # Note: jina.ai returns clean text directly, accept even short results (>=20 words)
    jina_success = False
    if not result or len(result.split()) < 100:
        jina_url = f"https://r.jina.ai/http://{url}"
        result, metadata = try_extract(jina_url, "jina.ai")
        # If jina.ai succeeded (returned text), use it even if short
        if result:
            safe_print(f"[Distillery] Using jina.ai result: {len(result.split())} words")
            jina_success = True

    # 5. Try jina.ai with https (only if previous jina failed)
    if not result and not jina_success:
        jina_url2 = f"https://r.jina.ai/{url}"
        result, metadata = try_extract(jina_url2, "jina.ai (https)")
        if result:
            safe_print(f"[Distillery] Using jina.ai (https) result: {len(result.split())} words")
            jina_success = True

    # 6. Try textise dot iitty dot iitty - text extraction service
    if not result:
        textise_url = f"https://r.jina.ai/http://r.jina.ai/http://cc.bingj.com/cache.aspx?d&u={quote(url, safe='')}" 
        result, metadata = try_extract(textise_url, "textise dot iitty dot iitty", delay=0.5)
        if result and not is_jina_error(result):
            safe_print(f"[Distillery] Using textise dot iitty dot iitty result: {len(result.split())} words")

    # 7. Try textise dot iitty dot iitty alt URL
    if not result:
        textise2_url = f"https://r.jina.ai/http://r.jina.ai/http://r.jina.ai/http://cc.bingj.com/cache.aspx?d&u={quote(url, safe='')}"
        result, metadata = try_extract(textise2_url, "textise dot iitty dot iitty alt", delay=0.5)
        if result and not is_jina_error(result):
            safe_print(f"[Distillery] Using textise dot iitty dot iitty alt result: {len(result.split())} words")

    # 8. Try archive.ph (archive.is mirror) - add delay to avoid rate limiting
    if not result or (not jina_success and len(result.split()) < 100):
        archive_ph_url = f"https://archive.ph/{url}"
        result, metadata = try_extract(archive_ph_url, "archive.ph", delay=1.0)

    # 9. Try archive.today - add delay
    if not result or (not jina_success and len(result.split()) < 100):
        archive_today_url = f"https://archive.today/{url}"
        result, metadata = try_extract(archive_today_url, "archive.today", delay=1.0)

    # 10. Try Wayback Machine with different snapshot selectors - add delay
    if not result or (not jina_success and len(result.split()) < 100):
        # Try most recent snapshot
        wayback_recent = f"https://web.archive.org/web/99999999999999/{quote(url, safe='')}"
        result, metadata = try_extract(wayback_recent, "Wayback Machine", delay=1.0)

    # If all failed, raise error
    if not result:
        safe_print(f"[Distillery] All sources failed for: {url}")
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
